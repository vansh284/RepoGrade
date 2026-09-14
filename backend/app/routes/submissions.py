import os
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import git_service
from app.database import get_db
from app.models import CheckResult, CloneStatus, EvaluatorGrade, GradingComponent, PeerAssignment, PeerEvaluation, Penalty, Student, Submission
from app.routes.helpers import _get_assignment, _get_course
from app.schemas import CloneProgress, DashboardCheckResult, DashboardRowWithChecks, SubmissionOut

router = APIRouter(tags=["submissions"])

REPO_BASE_PATH = os.environ.get("REPO_BASE_PATH", "./repos")


def _safe_path_segment(value: str) -> str:
    sanitized = value.replace("/", "_").replace("\\", "_").replace("..", "_").replace("\0", "_")
    if not sanitized or sanitized in (".", ".."):
        sanitized = "_"
    return sanitized


def _build_clone_path(course_name: str, assignment_name: str, github_username: str) -> str:
    base = Path(REPO_BASE_PATH).resolve()
    clone_path = (
        base
        / _safe_path_segment(course_name)
        / _safe_path_segment(assignment_name)
        / _safe_path_segment(github_username)
    ).resolve()
    if not str(clone_path).startswith(str(base)):
        raise ValueError("Clone path escapes base directory")
    return str(clone_path)


@router.post(
    "/api/courses/{course_id}/assignments/{assignment_id}/clone",
    response_model=CloneProgress,
)
def clone_repos(
    course_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
):
    course = _get_course(db, course_id)
    assignment = _get_assignment(db, course_id, assignment_id)
    students = db.query(Student).filter(Student.course_id == course_id).all()

    if not students:
        raise HTTPException(status_code=400, detail="No students in this course")

    student_ids = [s.id for s in students]
    existing_subs = (
        db.query(Submission)
        .filter(
            Submission.assignment_id == assignment_id,
            Submission.student_id.in_(student_ids),
        )
        .all()
    )
    subs_by_student: dict[int, Submission] = {s.student_id: s for s in existing_subs}

    completed = 0
    failed = 0

    for student in students:
        existing = subs_by_student.get(student.id)

        repo_url = f"https://github.com/{student.github_username}/{assignment.github_repo_name}"
        clone_path = _build_clone_path(course.name, assignment.name, student.github_username)

        if existing and existing.clone_status == CloneStatus.cloned:
            if git_service.repo_exists(existing.clone_path or ""):
                completed += 1
                continue

        if not existing:
            existing = Submission(
                student_id=student.id,
                assignment_id=assignment_id,
                repo_url=repo_url,
                clone_status=CloneStatus.pending,
                clone_path=clone_path,
            )
            db.add(existing)
            db.flush()
            subs_by_student[student.id] = existing

        existing.repo_url = repo_url
        existing.clone_path = clone_path

        dest = Path(clone_path)
        if dest.exists() and not git_service.repo_exists(clone_path):
            shutil.rmtree(clone_path)

        try:
            git_service.clone_repo(repo_url, clone_path)
            existing.clone_status = CloneStatus.cloned
            completed += 1
        except subprocess.CalledProcessError:
            existing.clone_status = CloneStatus.missing
            failed += 1

    db.commit()
    return CloneProgress(total=len(students), completed=completed, failed=failed)


@router.get(
    "/api/courses/{course_id}/assignments/{assignment_id}/dashboard",
    response_model=list[DashboardRowWithChecks],
)
def assignment_dashboard(
    course_id: int,
    assignment_id: int,
    status: str | None = None,
    search: str | None = None,
    sort: str = "student_name",
    order: str = "asc",
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    assignment = _get_assignment(db, course_id, assignment_id)

    students = db.query(Student).filter(Student.course_id == course_id).all()
    submissions_map: dict[int, Submission] = {}
    for sub in (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .all()
    ):
        submissions_map[sub.student_id] = sub

    submission_ids = [s.id for s in submissions_map.values()]
    check_results_map: dict[int, list[CheckResult]] = {}
    if submission_ids:
        for cr in (
            db.query(CheckResult)
            .filter(CheckResult.submission_id.in_(submission_ids))
            .all()
        ):
            check_results_map.setdefault(cr.submission_id, []).append(cr)

    grade_totals: dict[int, float] = {}
    if submission_ids:
        for grade in (
            db.query(EvaluatorGrade)
            .filter(EvaluatorGrade.submission_id.in_(submission_ids))
            .all()
        ):
            grade_totals[grade.submission_id] = (
                grade_totals.get(grade.submission_id, 0.0) + grade.score
            )

    peer_averages: dict[int, float] = {}
    peer_scores_by_student_comp: dict[int, dict[int, list[float]]] = {}
    peer_evaluator_counts: dict[int, int] = {}
    student_ids = [s.id for s in students]
    if student_ids:
        pas = (
            db.query(PeerAssignment)
            .filter(
                PeerAssignment.assignment_id == assignment_id,
                PeerAssignment.evaluee_id.in_(student_ids),
            )
            .all()
        )
        pa_ids = [pa.id for pa in pas]
        pa_evaluee_map = {pa.id: pa.evaluee_id for pa in pas}
        if pa_ids:
            evals = (
                db.query(PeerEvaluation)
                .filter(PeerEvaluation.peer_assignment_id.in_(pa_ids))
                .all()
            )
            totals_by_pa: dict[int, float] = {}
            peer_assignments_with_evals: dict[int, set[int]] = {}
            for pe in evals:
                totals_by_pa[pe.peer_assignment_id] = (
                    totals_by_pa.get(pe.peer_assignment_id, 0.0) + pe.score
                )
                evaluee_id = pa_evaluee_map[pe.peer_assignment_id]
                peer_scores_by_student_comp.setdefault(evaluee_id, {}).setdefault(
                    pe.grading_component_id, []
                ).append(pe.score)
                peer_assignments_with_evals.setdefault(evaluee_id, set()).add(pe.peer_assignment_id)
            totals_by_student: dict[int, list[float]] = {}
            for pa_id, total in totals_by_pa.items():
                evaluee_id = pa_evaluee_map[pa_id]
                totals_by_student.setdefault(evaluee_id, []).append(total)
            for sid, totals in totals_by_student.items():
                peer_averages[sid] = sum(totals) / len(totals)
            for sid, pa_set in peer_assignments_with_evals.items():
                peer_evaluator_counts[sid] = len(pa_set)

    penalty_map: dict[int, tuple[int, float]] = {}
    if submission_ids:
        for p in (
            db.query(Penalty)
            .filter(Penalty.submission_id.in_(submission_ids))
            .all()
        ):
            count, total = penalty_map.get(p.submission_id, (0, 0.0))
            penalty_map[p.submission_id] = (count + 1, total + p.amount)

    eval_scores_by_sub_comp: dict[int, dict[int, list[float]]] = {}
    if submission_ids:
        for g in (
            db.query(EvaluatorGrade)
            .filter(EvaluatorGrade.submission_id.in_(submission_ids))
            .all()
        ):
            eval_scores_by_sub_comp.setdefault(g.submission_id, {}).setdefault(
                g.grading_component_id, []
            ).append(g.score)

    components = assignment.grading_components
    num_main_expected = assignment.num_main_evaluators
    num_peer_expected = assignment.num_peer_evaluators

    rows: list[DashboardRowWithChecks] = []
    for student in students:
        sub = submissions_map.get(student.id)
        repo_url = f"https://github.com/{student.github_username}/{assignment.github_repo_name}"
        checks: list[DashboardCheckResult] = []
        if sub:
            for cr in check_results_map.get(sub.id, []):
                checks.append(
                    DashboardCheckResult(
                        check_name=cr.check_name,
                        passed=cr.passed,
                        message=cr.message,
                        details=cr.details,
                        stderr=cr.stderr,
                    )
                )

        final_grade = None
        pen_count = 0
        pen_total = 0.0
        incomplete_pools: list[str] = []
        if sub:
            pen_count, pen_total = penalty_map.get(sub.id, (0, 0.0))
            sub_eval_scores = eval_scores_by_sub_comp.get(sub.id, {})
            sub_peer_scores = peer_scores_by_student_comp.get(student.id, {})

            main_eval_count = 0
            if sub_eval_scores:
                main_eval_count = len(next(iter(sub_eval_scores.values())))
            peer_eval_count = peer_evaluator_counts.get(student.id, 0)

            if num_main_expected is not None and num_main_expected > 0 and main_eval_count == 0:
                incomplete_pools.append("evaluator")
            if num_peer_expected is not None and num_peer_expected > 0 and peer_eval_count == 0:
                incomplete_pools.append("peer")

            ew = assignment.evaluator_weight
            pw = assignment.peer_weight

            if num_main_expected is not None or num_peer_expected is not None:
                eval_has_grades = main_eval_count > 0
                peer_has_grades = peer_eval_count > 0
                if not eval_has_grades and not peer_has_grades:
                    ew, pw = 0.0, 0.0
                elif not eval_has_grades and peer_has_grades:
                    pw = ew + pw
                    ew = 0.0
                elif eval_has_grades and not peer_has_grades:
                    ew = ew + pw
                    pw = 0.0

            has_any = False
            fg = 0.0
            for gc in components:
                eval_list = sub_eval_scores.get(gc.id, [])
                peer_list = sub_peer_scores.get(gc.id, [])
                es = sum(eval_list) / len(eval_list) if eval_list else None
                ps = sum(peer_list) / len(peer_list) if peer_list else None
                if es is not None or ps is not None:
                    has_any = True
                    consolidated = ew * (es or 0.0) + pw * (ps or 0.0)
                    fg += gc.weight * consolidated
            if has_any:
                final_grade = round(fg - pen_total, 4)

        rows.append(
            DashboardRowWithChecks(
                student_name=student.name,
                github_username=student.github_username,
                student_db_id=student.id,
                clone_status=sub.clone_status.value if sub else "pending",
                repo_url=sub.repo_url if sub else repo_url,
                check_results=checks,
                evaluator_grade_total=grade_totals.get(sub.id) if sub else None,
                peer_grade_average=peer_averages.get(student.id),
                final_grade=final_grade,
                penalty_count=pen_count,
                penalty_total=pen_total,
                incomplete_pools=incomplete_pools,
            )
        )

    if status:
        rows = [r for r in rows if r.clone_status == status]

    if search:
        q = search.lower()
        rows = [
            r
            for r in rows
            if q in r.student_name.lower() or q in r.github_username.lower()
        ]

    reverse = order.lower() == "desc"
    sort_keys = {"student_name", "github_username", "clone_status"}
    if sort in sort_keys:
        rows.sort(key=lambda r: getattr(r, sort), reverse=reverse)

    return rows


@router.get(
    "/api/courses/{course_id}/assignments/{assignment_id}/clone/progress",
    response_model=CloneProgress,
)
def clone_progress(
    course_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    _get_assignment(db, course_id, assignment_id)

    student_count = db.query(Student).filter(Student.course_id == course_id).count()
    status_counts = dict(
        db.query(Submission.clone_status, func.count())
        .filter(Submission.assignment_id == assignment_id)
        .group_by(Submission.clone_status)
        .all()
    )

    completed = status_counts.get(CloneStatus.cloned, 0)
    failed = status_counts.get(CloneStatus.missing, 0) + status_counts.get(CloneStatus.error, 0)

    return CloneProgress(total=student_count, completed=completed, failed=failed)
