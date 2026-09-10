import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Course, Student
from app.schemas import ImportResult, ImportRowError, StudentCreate, StudentOut, StudentUpdate

router = APIRouter(prefix="/api/courses/{course_id}/students", tags=["students"])

REQUIRED_COLUMNS = {"name", "student_id", "email", "github_username"}


def _get_course(course_id: int, db: Session) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course


def _get_student(course_id: int, student_id: int, db: Session) -> Student:
    student = (
        db.query(Student)
        .filter(Student.course_id == course_id, Student.id == student_id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@router.post("", response_model=StudentOut, status_code=201)
def create_student(course_id: int, data: StudentCreate, db: Session = Depends(get_db)):
    _get_course(course_id, db)
    student = Student(course_id=course_id, **data.model_dump())
    db.add(student)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate student_id in this course")
    db.refresh(student)
    return student


@router.get("", response_model=list[StudentOut])
def list_students(course_id: int, db: Session = Depends(get_db)):
    _get_course(course_id, db)
    return db.query(Student).filter(Student.course_id == course_id).all()


@router.get("/export")
def export_students_csv(course_id: int, db: Session = Depends(get_db)):
    _get_course(course_id, db)
    students = db.query(Student).filter(Student.course_id == course_id).all()
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["name", "student_id", "email", "github_username"])
    writer.writeheader()
    for s in students:
        writer.writerow({
            "name": s.name,
            "student_id": s.student_id,
            "email": s.email,
            "github_username": s.github_username,
        })
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=roster.csv"},
    )


@router.get("/{student_id}", response_model=StudentOut)
def get_student(course_id: int, student_id: int, db: Session = Depends(get_db)):
    return _get_student(course_id, student_id, db)


@router.put("/{student_id}", response_model=StudentOut)
def update_student(course_id: int, student_id: int, data: StudentUpdate, db: Session = Depends(get_db)):
    student = _get_student(course_id, student_id, db)
    for key, value in data.model_dump().items():
        setattr(student, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Duplicate student_id in this course")
    db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=204)
def delete_student(course_id: int, student_id: int, db: Session = Depends(get_db)):
    student = _get_student(course_id, student_id, db)
    db.delete(student)
    db.commit()


@router.post("/import", response_model=ImportResult)
def import_students_csv(course_id: int, file: UploadFile, db: Session = Depends(get_db)):
    _get_course(course_id, db)
    raw = file.file.read()
    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File is not valid UTF-8")
    reader = csv.DictReader(io.StringIO(content))

    if not reader.fieldnames or not REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
        missing = REQUIRED_COLUMNS - set(reader.fieldnames or [])
        raise HTTPException(status_code=400, detail=f"Missing columns: {', '.join(sorted(missing))}")

    imported = 0
    errors: list[ImportRowError] = []

    for i, row in enumerate(reader, start=2):
        try:
            values = {col: (row[col] or "").strip() for col in REQUIRED_COLUMNS}
        except (KeyError, TypeError):
            errors.append(ImportRowError(row=i, error="Malformed row"))
            continue
        if not all(values.values()):
            errors.append(ImportRowError(row=i, error="Missing required field(s)"))
            continue
        sp = db.begin_nested()
        student = Student(course_id=course_id, **values)
        db.add(student)
        try:
            sp.commit()
            imported += 1
        except IntegrityError:
            sp.rollback()
            errors.append(ImportRowError(row=i, error=f"Duplicate student_id: {values['student_id']}"))

    db.commit()
    return ImportResult(imported=imported, errors=errors)
