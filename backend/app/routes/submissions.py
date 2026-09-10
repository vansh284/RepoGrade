import os
import shutil
import subprocess
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import git_service
from app.database import get_db
from app.models import Assignment, CloneStatus, Course, Student, Submission
from app.schemas import CloneProgress, DashboardRow, SubmissionOut

router = APIRouter(tags=["submissions"])

REPO_BASE_PATH = os.environ.get("REPO_BASE_PATH", "./repos")


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
    response_model=list[DashboardRow],
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

    rows: list[DashboardRow] = []
    for student in students:
        sub = submissions_map.get(student.id)
        repo_url = f"https://github.com/{student.github_username}/{assignment.github_repo_name}"
        rows.append(
            DashboardRow(
                student_name=student.name,
                github_username=student.github_username,
                student_db_id=student.id,
                clone_status=sub.clone_status.value if sub else "pending",
                repo_url=sub.repo_url if sub else repo_url,
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
