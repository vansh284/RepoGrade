import csv
import io
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload

from app import check_service
from app.database import get_db
from app.models import (
    CheckResult,
    CloneStatus,
    EnvironmentVariable,
    Student,
    Submission,
)
from app.routes.helpers import _get_assignment, _get_course
from app.schemas import CheckProgress, CheckResultOut

router = APIRouter(tags=["checks"])


@router.post(
    "/api/courses/{course_id}/assignments/{assignment_id}/run-checks",
    response_model=CheckProgress,
)
def run_checks(
    course_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    assignment = _get_assignment(db, course_id, assignment_id)

    scripts = check_service.discover_checks(assignment.checks_directory)
    if not scripts:
        raise HTTPException(status_code=400, detail="No check scripts found")

    submissions = (
        db.query(Submission)
        .filter(
            Submission.assignment_id == assignment_id,
            Submission.clone_status == CloneStatus.cloned,
        )
        .all()
    )

    if not submissions:
        raise HTTPException(status_code=400, detail="No cloned submissions to check")

    env_vars = (
        db.query(EnvironmentVariable)
        .filter(EnvironmentVariable.assignment_id == assignment_id)
        .all()
    )
    custom_env = {ev.key: ev.value for ev in env_vars}

    students_by_id: dict[int, Student] = {}
    student_ids = [s.student_id for s in submissions]
    for student in db.query(Student).filter(Student.id.in_(student_ids)).all():
        students_by_id[student.id] = student

    total = len(submissions) * len(scripts)
    completed = 0

    for submission in submissions:
        student = students_by_id.get(submission.student_id)
        if not student or not submission.clone_path:
            continue

        env = {
            **custom_env,
            "STUDENT_USERNAME": student.github_username,
            "ASSIGNMENT_NAME": assignment.name,
        }

        for script_path in scripts:
            check_name = Path(script_path).stem

            output = check_service.run_check(script_path, submission.clone_path, env)

            existing = (
                db.query(CheckResult)
                .filter(
                    CheckResult.submission_id == submission.id,
                    CheckResult.check_name == check_name,
                )
                .first()
            )

            if existing:
                existing.passed = output.passed
                existing.message = output.message
                existing.details = output.details
                existing.stderr = output.stderr
            else:
                db.add(
                    CheckResult(
                        submission_id=submission.id,
                        check_name=check_name,
                        passed=output.passed,
                        message=output.message,
                        details=output.details,
                        stderr=output.stderr,
                    )
                )

            completed += 1

    db.commit()
    return CheckProgress(total=total, completed=completed)


@router.get(
    "/api/courses/{course_id}/assignments/{assignment_id}/check-results",
    response_model=list[CheckResultOut],
)
def list_check_results(
    course_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    _get_assignment(db, course_id, assignment_id)

    submission_ids = [
        s.id
        for s in db.query(Submission.id)
        .filter(Submission.assignment_id == assignment_id)
        .all()
    ]

    return (
        db.query(CheckResult)
        .filter(CheckResult.submission_id.in_(submission_ids))
        .all()
    )


@router.get(
    "/api/courses/{course_id}/assignments/{assignment_id}/check-results/progress",
    response_model=CheckProgress,
)
def check_progress(
    course_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    assignment = _get_assignment(db, course_id, assignment_id)

    scripts = check_service.discover_checks(assignment.checks_directory)
    cloned_count = (
        db.query(Submission)
        .filter(
            Submission.assignment_id == assignment_id,
            Submission.clone_status == CloneStatus.cloned,
        )
        .count()
    )

    total = cloned_count * len(scripts)

    submission_ids = [
        s.id
        for s in db.query(Submission.id)
        .filter(Submission.assignment_id == assignment_id)
        .all()
    ]
    completed = (
        db.query(CheckResult)
        .filter(CheckResult.submission_id.in_(submission_ids))
        .count()
        if submission_ids
        else 0
    )

    return CheckProgress(total=total, completed=completed)


@router.get(
    "/api/courses/{course_id}/assignments/{assignment_id}/check-results/export",
)
def export_check_results_csv(
    course_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    _get_assignment(db, course_id, assignment_id)

    submissions = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .options(selectinload(Submission.check_results), selectinload(Submission.student))
        .all()
    )

    check_names: set[str] = set()
    for sub in submissions:
        for cr in sub.check_results:
            check_names.add(cr.check_name)
    sorted_checks = sorted(check_names)

    fieldnames = ["student_name", "github_username"]
    for cn in sorted_checks:
        fieldnames.extend([f"{cn}_passed", f"{cn}_message"])

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()

    for sub in submissions:
        results_by_name = {cr.check_name: cr for cr in sub.check_results}
        row: dict[str, str] = {
            "student_name": sub.student.name,
            "github_username": sub.student.github_username,
        }
        for cn in sorted_checks:
            cr = results_by_name.get(cn)
            if cr:
                row[f"{cn}_passed"] = str(cr.passed)
                row[f"{cn}_message"] = cr.message
            else:
                row[f"{cn}_passed"] = ""
                row[f"{cn}_message"] = ""
        writer.writerow(row)

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=check_results.csv"},
    )
