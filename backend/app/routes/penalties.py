from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Penalty, Submission
from app.routes.helpers import _get_assignment, _get_course
from app.schemas import PenaltyCreate, PenaltyOut, PenaltyUpdate

router = APIRouter(tags=["penalties"])


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


@router.get(
    "/api/courses/{course_id}/assignments/{assignment_id}/students/{student_db_id}/penalties",
    response_model=list[PenaltyOut],
)
def list_penalties(
    course_id: int,
    assignment_id: int,
    student_db_id: int,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    _get_assignment(db, course_id, assignment_id)
    sub = _get_submission(db, student_db_id, assignment_id)

    return (
        db.query(Penalty)
        .filter(Penalty.submission_id == sub.id)
        .all()
    )


@router.post(
    "/api/courses/{course_id}/assignments/{assignment_id}/students/{student_db_id}/penalties",
    response_model=PenaltyOut,
    status_code=201,
)
def add_penalty(
    course_id: int,
    assignment_id: int,
    student_db_id: int,
    data: PenaltyCreate,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    _get_assignment(db, course_id, assignment_id)
    sub = _get_submission(db, student_db_id, assignment_id)

    penalty = Penalty(
        submission_id=sub.id,
        reason=data.reason,
        amount=data.amount,
    )
    db.add(penalty)
    db.commit()
    db.refresh(penalty)
    return penalty


@router.put(
    "/api/courses/{course_id}/assignments/{assignment_id}/students/{student_db_id}/penalties/{penalty_id}",
    response_model=PenaltyOut,
)
def update_penalty(
    course_id: int,
    assignment_id: int,
    student_db_id: int,
    penalty_id: int,
    data: PenaltyUpdate,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    _get_assignment(db, course_id, assignment_id)
    sub = _get_submission(db, student_db_id, assignment_id)

    penalty = (
        db.query(Penalty)
        .filter(Penalty.id == penalty_id, Penalty.submission_id == sub.id)
        .first()
    )
    if not penalty:
        raise HTTPException(status_code=404, detail="Penalty not found")

    penalty.reason = data.reason
    penalty.amount = data.amount
    db.commit()
    db.refresh(penalty)
    return penalty


@router.delete(
    "/api/courses/{course_id}/assignments/{assignment_id}/students/{student_db_id}/penalties/{penalty_id}",
    status_code=204,
)
def delete_penalty(
    course_id: int,
    assignment_id: int,
    student_db_id: int,
    penalty_id: int,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    _get_assignment(db, course_id, assignment_id)
    sub = _get_submission(db, student_db_id, assignment_id)

    penalty = (
        db.query(Penalty)
        .filter(Penalty.id == penalty_id, Penalty.submission_id == sub.id)
        .first()
    )
    if not penalty:
        raise HTTPException(status_code=404, detail="Penalty not found")

    db.delete(penalty)
    db.commit()
