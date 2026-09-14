import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Assignment,
    Course,
    EvaluatorGrade,
    GradingComponent,
    PeerAssignment,
    PeerEvaluation,
    Penalty,
    Student,
    Submission,
)
from app.schemas import (
    EvaluatorGradeOut,
    EvaluatorGradeSubmit,
    GradeImportResult,
    ImportRowError,
)

router = APIRouter(tags=["grades"])


def _get_course(db: Session, course_id: int) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def _get_assignment(db: Session, course_id: int, assignment_id: int) -> Assignment:
    assignment = (
        db.query(Assignment)
        .filter(Assignment.id == assignment_id, Assignment.course_id == course_id)
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


def _get_submission(db: Session, student_id: int, assignment_id: int) -> Submission:
    sub = (
        db.query(Submission)
        .filter(
            Submission.student_id == student_id,
            Submission.assignment_id == assignment_id,
        )
        .first()
    )
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")
    return sub


def _grade_to_out(grade: EvaluatorGrade) -> EvaluatorGradeOut:
    return EvaluatorGradeOut(
        id=grade.id,
        submission_id=grade.submission_id,
        grading_component_id=grade.grading_component_id,
        component_name=grade.grading_component.name,
        evaluator_id=grade.evaluator_id,
        score=grade.score,
    )


@router.put(
    "/api/courses/{course_id}/assignments/{assignment_id}/students/{student_db_id}/grades",
    response_model=list[EvaluatorGradeOut],
)
def submit_grades(
    course_id: int,
    assignment_id: int,
    student_db_id: int,
    data: EvaluatorGradeSubmit,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    assignment = _get_assignment(db, course_id, assignment_id)
    sub = _get_submission(db, student_db_id, assignment_id)

    component_ids = {gc.id for gc in assignment.grading_components}

    for g in data.grades:
        if g.grading_component_id not in component_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Grading component {g.grading_component_id} not found in this assignment",
            )

    evaluator_id = data.evaluator_id
    for g in data.grades:
        existing = (
            db.query(EvaluatorGrade)
            .filter(
                EvaluatorGrade.submission_id == sub.id,
                EvaluatorGrade.grading_component_id == g.grading_component_id,
                EvaluatorGrade.evaluator_id == evaluator_id,
            )
            .first()
        )
        if existing:
            existing.score = g.score
        else:
            db.add(
                EvaluatorGrade(
                    submission_id=sub.id,
                    grading_component_id=g.grading_component_id,
                    evaluator_id=evaluator_id,
                    score=g.score,
                )
            )

    db.commit()

    grades = (
        db.query(EvaluatorGrade)
        .filter(EvaluatorGrade.submission_id == sub.id)
        .all()
    )
    return [_grade_to_out(g) for g in grades]


@router.get(
    "/api/courses/{course_id}/assignments/{assignment_id}/students/{student_db_id}/grades",
    response_model=list[EvaluatorGradeOut],
)
def get_grades(
    course_id: int,
    assignment_id: int,
    student_db_id: int,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    _get_assignment(db, course_id, assignment_id)
    sub = _get_submission(db, student_db_id, assignment_id)

    grades = (
        db.query(EvaluatorGrade)
        .filter(EvaluatorGrade.submission_id == sub.id)
        .all()
    )
    return [_grade_to_out(g) for g in grades]


@router.post(
    "/api/courses/{course_id}/assignments/{assignment_id}/grades/import",
    response_model=GradeImportResult,
)
def import_grades_csv(
    course_id: int,
    assignment_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    assignment = _get_assignment(db, course_id, assignment_id)

    raw = file.file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8")

    reader = csv.DictReader(io.StringIO(content))
    if not reader.fieldnames or "github_username" not in reader.fieldnames:
        raise HTTPException(status_code=400, detail="Missing required column: github_username")

    components = {gc.name: gc for gc in assignment.grading_components}
    component_columns = [col for col in reader.fieldnames if col != "github_username"]

    invalid_cols = [col for col in component_columns if col not in components]
    if invalid_cols:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown grading component columns: {', '.join(invalid_cols)}",
        )

    students_by_gh = {
        s.github_username: s
        for s in db.query(Student).filter(Student.course_id == assignment.course_id).all()
    }

    imported = 0
    errors: list[ImportRowError] = []

    for i, row in enumerate(reader, start=2):
        gh = (row.get("github_username") or "").strip()
        if not gh:
            errors.append(ImportRowError(row=i, error="Missing github_username"))
            continue

        student = students_by_gh.get(gh)
        if not student:
            errors.append(ImportRowError(row=i, error=f"Unknown github_username: {gh}"))
            continue

        sub = (
            db.query(Submission)
            .filter(
                Submission.student_id == student.id,
                Submission.assignment_id == assignment_id,
            )
            .first()
        )
        if not sub:
            errors.append(ImportRowError(row=i, error=f"No submission for {gh}"))
            continue

        row_ok = True
        for col in component_columns:
            val = (row.get(col) or "").strip()
            if not val:
                continue
            try:
                score = float(val)
            except ValueError:
                errors.append(ImportRowError(row=i, error=f"Invalid score for {col}: {val}"))
                row_ok = False
                break

        if not row_ok:
            continue

        for col in component_columns:
            val = (row.get(col) or "").strip()
            if not val:
                continue
            score = float(val)
            gc = components[col]

            existing = (
                db.query(EvaluatorGrade)
                .filter(
                    EvaluatorGrade.submission_id == sub.id,
                    EvaluatorGrade.grading_component_id == gc.id,
                    EvaluatorGrade.evaluator_id == "default",
                )
                .first()
            )
            if existing:
                existing.score = score
            else:
                db.add(
                    EvaluatorGrade(
                        submission_id=sub.id,
                        grading_component_id=gc.id,
                        evaluator_id="default",
                        score=score,
                    )
                )

        imported += 1

    db.commit()
    return GradeImportResult(imported=imported, errors=errors)


@router.get("/api/courses/{course_id}/assignments/{assignment_id}/grades/export")
def export_grades_csv(
    course_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    assignment = _get_assignment(db, course_id, assignment_id)

    components = assignment.grading_components
    component_names = [gc.name for gc in components]
    component_map = {gc.id: gc.name for gc in components}

    students = db.query(Student).filter(Student.course_id == assignment.course_id).all()
    subs = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .all()
    )
    subs_by_student = {s.student_id: s for s in subs}

    sub_ids = [s.id for s in subs]
    grades = (
        db.query(EvaluatorGrade)
        .filter(EvaluatorGrade.submission_id.in_(sub_ids))
        .all()
        if sub_ids
        else []
    )
    grades_map: dict[int, dict[str, float]] = {}
    for g in grades:
        grades_map.setdefault(g.submission_id, {})[component_map[g.grading_component_id]] = g.score

    fieldnames = ["github_username"] + component_names
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()

    for student in students:
        sub = subs_by_student.get(student.id)
        row: dict[str, str] = {"github_username": student.github_username}
        if sub and sub.id in grades_map:
            for name in component_names:
                score = grades_map[sub.id].get(name)
                row[name] = str(score) if score is not None else ""
        else:
            for name in component_names:
                row[name] = ""
        writer.writerow(row)

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=grades.csv"},
    )


def _parse_name_last_first(name: str) -> tuple[str, bool]:
    """Attempt to reformat 'First Last' to 'Last, First'. Returns (formatted, success)."""
    if "," in name:
        return name, True
    parts = name.strip().split()
    if len(parts) >= 2:
        return f"{parts[-1]}, {' '.join(parts[:-1])}", True
    return name, False


def _compute_final_grades(
    db: Session, assignment: Assignment, students: list[Student],
) -> list[dict]:
    components = assignment.grading_components
    component_map = {gc.id: gc for gc in components}

    subs = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment.id)
        .all()
    )
    subs_by_student: dict[int, Submission] = {s.student_id: s for s in subs}
    sub_ids = [s.id for s in subs]

    # Collect all evaluator grades, grouped by (submission, component) -> list of scores
    eval_scores_by_sub_comp: dict[int, dict[int, list[float]]] = {}
    if sub_ids:
        for g in (
            db.query(EvaluatorGrade)
            .filter(EvaluatorGrade.submission_id.in_(sub_ids))
            .all()
        ):
            eval_scores_by_sub_comp.setdefault(g.submission_id, {}).setdefault(
                g.grading_component_id, []
            ).append(g.score)

    student_ids = [s.id for s in students]
    peer_scores_by_student_comp: dict[int, dict[int, list[float]]] = {}
    peer_evaluator_counts: dict[int, int] = {}
    if student_ids:
        pas = (
            db.query(PeerAssignment)
            .filter(
                PeerAssignment.assignment_id == assignment.id,
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
            peer_assignments_with_evals: dict[int, set[int]] = {}
            for pe in evals:
                evaluee_id = pa_evaluee_map[pe.peer_assignment_id]
                peer_scores_by_student_comp.setdefault(evaluee_id, {}).setdefault(
                    pe.grading_component_id, []
                ).append(pe.score)
                peer_assignments_with_evals.setdefault(evaluee_id, set()).add(pe.peer_assignment_id)
            for sid, pa_set in peer_assignments_with_evals.items():
                peer_evaluator_counts[sid] = len(pa_set)

    penalty_totals: dict[int, float] = {}
    if sub_ids:
        for p in (
            db.query(Penalty)
            .filter(Penalty.submission_id.in_(sub_ids))
            .all()
        ):
            penalty_totals[p.submission_id] = (
                penalty_totals.get(p.submission_id, 0.0) + p.amount
            )

    num_main_expected = assignment.num_main_evaluators
    num_peer_expected = assignment.num_peer_evaluators

    results = []
    name_warnings: list[str] = []
    for student in students:
        sub = subs_by_student.get(student.id)
        formatted_name, name_ok = _parse_name_last_first(student.name)
        if not name_ok:
            name_warnings.append(student.name)

        component_scores: dict[str, float] = {}
        final = 0.0
        has_any_grade = False
        incomplete_pools: list[str] = []

        if sub:
            sub_eval_scores = eval_scores_by_sub_comp.get(sub.id, {})
            sub_peer_scores = peer_scores_by_student_comp.get(student.id, {})

            # Determine how many distinct main evaluators graded this submission
            main_eval_count = 0
            if sub_eval_scores:
                main_eval_count = len(next(iter(sub_eval_scores.values())))
            peer_eval_count = peer_evaluator_counts.get(student.id, 0)

            # Check for incomplete pools (zero grades when expected)
            if num_main_expected is not None and num_main_expected > 0 and main_eval_count == 0:
                incomplete_pools.append("evaluator")
            if num_peer_expected is not None and num_peer_expected > 0 and peer_eval_count == 0:
                incomplete_pools.append("peer")

            # Compute effective weights with auto-weighting
            ew = assignment.evaluator_weight
            pw = assignment.peer_weight

            if num_main_expected is not None or num_peer_expected is not None:
                eval_has_grades = main_eval_count > 0
                peer_has_grades = peer_eval_count > 0

                if not eval_has_grades and not peer_has_grades:
                    ew, pw = 0.0, 0.0
                elif not eval_has_grades and peer_has_grades:
                    # Evaluator pool empty -> all weight to peer
                    pw = ew + pw
                    ew = 0.0
                elif eval_has_grades and not peer_has_grades:
                    # Peer pool empty -> all weight to evaluator
                    ew = ew + pw
                    pw = 0.0

            for gc in components:
                eval_scores_list = sub_eval_scores.get(gc.id, [])
                peer_scores_list = sub_peer_scores.get(gc.id, [])

                eval_score = sum(eval_scores_list) / len(eval_scores_list) if eval_scores_list else None
                peer_score = sum(peer_scores_list) / len(peer_scores_list) if peer_scores_list else None

                if eval_score is not None or peer_score is not None:
                    has_any_grade = True
                    consolidated = (
                        ew * (eval_score or 0.0)
                        + pw * (peer_score or 0.0)
                    )
                    component_scores[gc.name] = round(consolidated, 4)
                    final += gc.weight * consolidated

            penalty = penalty_totals.get(sub.id, 0.0)
            final -= penalty

        results.append({
            "student_name": formatted_name,
            "student_id": student.student_id,
            "email": student.email,
            "component_scores": component_scores,
            "final_grade": round(final, 4) if has_any_grade else None,
            "name_warning": not name_ok,
            "incomplete_pools": incomplete_pools,
        })

    return results


@router.get("/api/courses/{course_id}/assignments/{assignment_id}/canvas-export")
def canvas_export_csv(
    course_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    assignment = _get_assignment(db, course_id, assignment_id)
    students = db.query(Student).filter(Student.course_id == assignment.course_id).all()

    grade_data = _compute_final_grades(db, assignment, students)

    component_names = [gc.name for gc in assignment.grading_components]
    fieldnames = ["Student", "ID", "SIS Login ID"] + component_names + ["Final Grade"]

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()

    for entry in grade_data:
        row: dict[str, str] = {
            "Student": entry["student_name"],
            "ID": entry["student_id"],
            "SIS Login ID": entry["email"],
        }
        for cn in component_names:
            score = entry["component_scores"].get(cn)
            row[cn] = str(score) if score is not None else ""
        row["Final Grade"] = str(entry["final_grade"]) if entry["final_grade"] is not None else ""
        writer.writerow(row)

    buf.seek(0)
    warnings = [e["student_name"] for e in grade_data if e["name_warning"]]
    headers = {"Content-Disposition": "attachment; filename=canvas_grades.csv"}
    if warnings:
        headers["X-Name-Warnings"] = ",".join(warnings)

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers=headers,
    )
