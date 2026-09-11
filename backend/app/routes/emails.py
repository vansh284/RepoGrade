from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.email_service import EmailSender, get_email_sender
from app.models import (
    CheckResult,
    EmailTemplate,
    Student,
    Submission,
)
from app.routes.helpers import _get_assignment, _get_course
from app.schemas import (
    BatchSendResult,
    EmailPreview,
    EmailTemplateCreate,
    EmailTemplateOut,
    EmailTemplateUpdate,
)

router = APIRouter(tags=["emails"])


def _get_template(db: Session, assignment_id: int, template_id: int) -> EmailTemplate:
    template = (
        db.query(EmailTemplate)
        .filter(
            EmailTemplate.id == template_id,
            EmailTemplate.assignment_id == assignment_id,
        )
        .first()
    )
    if not template:
        raise HTTPException(status_code=404, detail="Email template not found")
    return template


def _render_template(
    template_str: str,
    student: Student,
    assignment_name: str,
    course_name: str,
    check_name: str = "",
    check_message: str = "",
    check_details: str = "",
    repo_url: str = "",
) -> str:
    placeholders = defaultdict(
        str,
        student_name=student.name,
        student_id=student.student_id,
        student_email=student.email,
        github_username=student.github_username,
        repo_url=repo_url,
        assignment_name=assignment_name,
        course_name=course_name,
        check_name=check_name,
        check_message=check_message,
        check_details=check_details,
    )
    return template_str.format_map(placeholders)


# ── CRUD ──────────────────────────────────────────────────────


@router.post(
    "/api/courses/{course_id}/assignments/{assignment_id}/email-templates",
    response_model=EmailTemplateOut,
    status_code=201,
)
def create_email_template(
    course_id: int,
    assignment_id: int,
    data: EmailTemplateCreate,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    _get_assignment(db, course_id, assignment_id)
    template = EmailTemplate(
        assignment_id=assignment_id,
        name=data.name,
        subject_template=data.subject_template,
        body_template=data.body_template,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get(
    "/api/courses/{course_id}/assignments/{assignment_id}/email-templates",
    response_model=list[EmailTemplateOut],
)
def list_email_templates(
    course_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    _get_assignment(db, course_id, assignment_id)
    return (
        db.query(EmailTemplate)
        .filter(EmailTemplate.assignment_id == assignment_id)
        .all()
    )


@router.put(
    "/api/courses/{course_id}/assignments/{assignment_id}/email-templates/{template_id}",
    response_model=EmailTemplateOut,
)
def update_email_template(
    course_id: int,
    assignment_id: int,
    template_id: int,
    data: EmailTemplateUpdate,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    _get_assignment(db, course_id, assignment_id)
    template = _get_template(db, assignment_id, template_id)
    template.name = data.name
    template.subject_template = data.subject_template
    template.body_template = data.body_template
    db.commit()
    db.refresh(template)
    return template


@router.delete(
    "/api/courses/{course_id}/assignments/{assignment_id}/email-templates/{template_id}",
    status_code=204,
)
def delete_email_template(
    course_id: int,
    assignment_id: int,
    template_id: int,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    _get_assignment(db, course_id, assignment_id)
    template = _get_template(db, assignment_id, template_id)
    db.delete(template)
    db.commit()


# ── Preview + Send ────────────────────────────────────────────


@router.get(
    "/api/courses/{course_id}/assignments/{assignment_id}/email-templates/{template_id}/preview",
    response_model=EmailPreview,
)
def preview_email(
    course_id: int,
    assignment_id: int,
    template_id: int,
    student_id: int,
    db: Session = Depends(get_db),
):
    course = _get_course(db, course_id)
    assignment = _get_assignment(db, course_id, assignment_id)
    template = _get_template(db, assignment_id, template_id)

    student = db.query(Student).filter(Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    submission = (
        db.query(Submission)
        .filter(
            Submission.student_id == student_id,
            Submission.assignment_id == assignment_id,
        )
        .first()
    )
    repo_url = submission.repo_url if submission else ""

    subject = _render_template(
        template.subject_template,
        student,
        assignment.name,
        course.name,
        repo_url=repo_url,
    )
    body = _render_template(
        template.body_template,
        student,
        assignment.name,
        course.name,
        repo_url=repo_url,
    )
    return EmailPreview(subject=subject, body=body)


@router.post(
    "/api/courses/{course_id}/assignments/{assignment_id}/email-templates/{template_id}/send",
    response_model=BatchSendResult,
)
def batch_send(
    course_id: int,
    assignment_id: int,
    template_id: int,
    check_name: str,
    db: Session = Depends(get_db),
    sender: EmailSender = Depends(get_email_sender),
):
    course = _get_course(db, course_id)
    assignment = _get_assignment(db, course_id, assignment_id)
    template = _get_template(db, assignment_id, template_id)

    # Find all submissions for this assignment with their check results
    submissions = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .options(selectinload(Submission.check_results), selectinload(Submission.student))
        .all()
    )

    sent = 0
    failed = 0
    errors: list[str] = []

    for submission in submissions:
        # Find the specific check result that failed
        failed_check = None
        for cr in submission.check_results:
            if cr.check_name == check_name and not cr.passed:
                failed_check = cr
                break

        if failed_check is None:
            continue

        student = submission.student
        subject = _render_template(
            template.subject_template,
            student,
            assignment.name,
            course.name,
            check_name=check_name,
            check_message=failed_check.message,
            check_details=failed_check.details,
            repo_url=submission.repo_url,
        )
        body = _render_template(
            template.body_template,
            student,
            assignment.name,
            course.name,
            check_name=check_name,
            check_message=failed_check.message,
            check_details=failed_check.details,
            repo_url=submission.repo_url,
        )

        try:
            sender.send(student.email, subject, body)
            sent += 1
        except Exception as exc:
            failed += 1
            errors.append(f"{student.name}: {exc}")

    return BatchSendResult(sent=sent, failed=failed, errors=errors)
