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

    for g in data.grades:
        existing = (
            db.query(EvaluatorGrade)
            .filter(
                EvaluatorGrade.submission_id == sub.id,
                EvaluatorGrade.grading_component_id == g.grading_component_id,
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
