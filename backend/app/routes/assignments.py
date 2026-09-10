from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Assignment, Course, EnvironmentVariable, GradingComponent
from app.schemas import (
    AssignmentCreate,
    AssignmentOut,
    AssignmentUpdate,
    EnvVarCreate,
    EnvVarOut,
    EnvVarUpdate,
    GradingComponentCreate,
    GradingComponentOut,
    GradingComponentUpdate,
)

router = APIRouter(tags=["assignments"])


def _get_course(db: Session, course_id: int) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def _get_assignment(db: Session, assignment_id: int) -> Assignment:
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


# ── Assignment CRUD ──────────────────────────────────────────────


@router.post("/api/courses/{course_id}/assignments", response_model=AssignmentOut, status_code=201)
def create_assignment(course_id: int, data: AssignmentCreate, db: Session = Depends(get_db)):
    _get_course(db, course_id)
    assignment = Assignment(
        course_id=course_id,
        name=data.name,
        github_repo_name=data.github_repo_name,
        checks_directory=data.checks_directory,
        evaluator_weight=data.evaluator_weight,
        peer_weight=data.peer_weight,
    )
    for gc in data.grading_components:
        assignment.grading_components.append(
            GradingComponent(name=gc.name, max_points=gc.max_points, weight=gc.weight)
        )
    for ev in data.environment_variables:
        assignment.environment_variables.append(
            EnvironmentVariable(key=ev.key, value=ev.value)
        )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/api/courses/{course_id}/assignments", response_model=list[AssignmentOut])
def list_assignments(course_id: int, db: Session = Depends(get_db)):
    _get_course(db, course_id)
    return (
        db.query(Assignment)
        .filter(Assignment.course_id == course_id)
        .options(selectinload(Assignment.grading_components), selectinload(Assignment.environment_variables))
        .all()
    )


@router.get("/api/courses/{course_id}/assignments/{assignment_id}", response_model=AssignmentOut)
def get_assignment(course_id: int, assignment_id: int, db: Session = Depends(get_db)):
    _get_course(db, course_id)
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id, Assignment.course_id == course_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


@router.put("/api/courses/{course_id}/assignments/{assignment_id}", response_model=AssignmentOut)
def update_assignment(course_id: int, assignment_id: int, data: AssignmentUpdate, db: Session = Depends(get_db)):
    _get_course(db, course_id)
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id, Assignment.course_id == course_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    assignment.name = data.name
    assignment.github_repo_name = data.github_repo_name
    assignment.checks_directory = data.checks_directory
    assignment.evaluator_weight = data.evaluator_weight
    assignment.peer_weight = data.peer_weight
    assignment.grading_components.clear()
    for gc in data.grading_components:
        assignment.grading_components.append(
            GradingComponent(name=gc.name, max_points=gc.max_points, weight=gc.weight)
        )
    assignment.environment_variables.clear()
    for ev in data.environment_variables:
        assignment.environment_variables.append(
            EnvironmentVariable(key=ev.key, value=ev.value)
        )
    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/api/courses/{course_id}/assignments/{assignment_id}", status_code=204)
def delete_assignment(course_id: int, assignment_id: int, db: Session = Depends(get_db)):
    _get_course(db, course_id)
    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id, Assignment.course_id == course_id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.delete(assignment)
    db.commit()


# ── Grading Component CRUD ───────────────────────────────────────


@router.post("/api/assignments/{assignment_id}/grading-components", response_model=GradingComponentOut, status_code=201)
def create_grading_component(assignment_id: int, data: GradingComponentCreate, db: Session = Depends(get_db)):
    _get_assignment(db, assignment_id)
    gc = GradingComponent(
        assignment_id=assignment_id,
        name=data.name,
        max_points=data.max_points,
        weight=data.weight,
    )
    db.add(gc)
    db.commit()
    db.refresh(gc)
    return gc


@router.get("/api/assignments/{assignment_id}/grading-components", response_model=list[GradingComponentOut])
def list_grading_components(assignment_id: int, db: Session = Depends(get_db)):
    _get_assignment(db, assignment_id)
    return db.query(GradingComponent).filter(GradingComponent.assignment_id == assignment_id).all()


@router.put("/api/assignments/{assignment_id}/grading-components/{gc_id}", response_model=GradingComponentOut)
def update_grading_component(assignment_id: int, gc_id: int, data: GradingComponentUpdate, db: Session = Depends(get_db)):
    _get_assignment(db, assignment_id)
    gc = db.query(GradingComponent).filter(
        GradingComponent.id == gc_id, GradingComponent.assignment_id == assignment_id
    ).first()
    if not gc:
        raise HTTPException(status_code=404, detail="Grading component not found")
    gc.name = data.name
    gc.max_points = data.max_points
    gc.weight = data.weight
    db.commit()
    db.refresh(gc)
    return gc


@router.delete("/api/assignments/{assignment_id}/grading-components/{gc_id}", status_code=204)
def delete_grading_component(assignment_id: int, gc_id: int, db: Session = Depends(get_db)):
    _get_assignment(db, assignment_id)
    gc = db.query(GradingComponent).filter(
        GradingComponent.id == gc_id, GradingComponent.assignment_id == assignment_id
    ).first()
    if not gc:
        raise HTTPException(status_code=404, detail="Grading component not found")
    db.delete(gc)
    db.commit()


# ── Environment Variable CRUD ────────────────────────────────────


@router.post("/api/assignments/{assignment_id}/env-vars", response_model=EnvVarOut, status_code=201)
def create_env_var(assignment_id: int, data: EnvVarCreate, db: Session = Depends(get_db)):
    _get_assignment(db, assignment_id)
    ev = EnvironmentVariable(
        assignment_id=assignment_id,
        key=data.key,
        value=data.value,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


@router.get("/api/assignments/{assignment_id}/env-vars", response_model=list[EnvVarOut])
def list_env_vars(assignment_id: int, db: Session = Depends(get_db)):
    _get_assignment(db, assignment_id)
    return db.query(EnvironmentVariable).filter(EnvironmentVariable.assignment_id == assignment_id).all()


@router.put("/api/assignments/{assignment_id}/env-vars/{ev_id}", response_model=EnvVarOut)
def update_env_var(assignment_id: int, ev_id: int, data: EnvVarUpdate, db: Session = Depends(get_db)):
    _get_assignment(db, assignment_id)
    ev = db.query(EnvironmentVariable).filter(
        EnvironmentVariable.id == ev_id, EnvironmentVariable.assignment_id == assignment_id
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Environment variable not found")
    ev.key = data.key
    ev.value = data.value
    db.commit()
    db.refresh(ev)
    return ev


@router.delete("/api/assignments/{assignment_id}/env-vars/{ev_id}", status_code=204)
def delete_env_var(assignment_id: int, ev_id: int, db: Session = Depends(get_db)):
    _get_assignment(db, assignment_id)
    ev = db.query(EnvironmentVariable).filter(
        EnvironmentVariable.id == ev_id, EnvironmentVariable.assignment_id == assignment_id
    ).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Environment variable not found")
    db.delete(ev)
    db.commit()
