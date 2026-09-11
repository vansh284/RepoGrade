import csv
import io
import random
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.email_service import EmailSender, get_email_sender
from app.models import (
    GradingComponent,
    PeerAssignment,
    PeerEvaluation,
    Student,
    Submission,
)
from app.routes.helpers import _get_assignment, _get_course
from app.schemas import (
    BatchSendResult,
    ImportRowError,
    PeerAssignmentOut,
    PeerEmailSendRequest,
    PeerEvalImportResult,
    PeerEvaluationOut,
)

router = APIRouter(tags=["peers"])


def _peer_assignment_to_out(pa: PeerAssignment) -> PeerAssignmentOut:
    return PeerAssignmentOut(
        id=pa.id,
        assignment_id=pa.assignment_id,
        evaluator_id=pa.evaluator_id,
        evaluator_name=pa.evaluator.name,
        evaluee_id=pa.evaluee_id,
        evaluee_name=pa.evaluee.name,
        repo_url=pa.repo_url,
    )


# ── Generate ─────────────────────────────────────────────────


@router.post(
    "/api/courses/{course_id}/assignments/{assignment_id}/peer-assignments/generate",
    response_model=list[PeerAssignmentOut],
)
def generate_peer_assignments(
    course_id: int,
    assignment_id: int,
    count: int = 2,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    assignment = _get_assignment(db, course_id, assignment_id)

    students = db.query(Student).filter(Student.course_id == course_id).all()
    if len(students) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 students for peer assignments")

    if count >= len(students):
        raise HTTPException(status_code=400, detail="Count must be less than the number of students")

    db.query(PeerAssignment).filter(PeerAssignment.assignment_id == assignment_id).delete()

    subs_by_student: dict[int, Submission] = {}
    for sub in db.query(Submission).filter(Submission.assignment_id == assignment_id).all():
        subs_by_student[sub.student_id] = sub

    shuffled = list(students)
    random.shuffle(shuffled)
    n = len(shuffled)

    assignments_out: list[PeerAssignment] = []
    for i, evaluator in enumerate(shuffled):
        for offset in range(1, count + 1):
            evaluee = shuffled[(i + offset) % n]
            sub = subs_by_student.get(evaluee.id)
            repo_url = sub.repo_url if sub else f"https://github.com/{evaluee.github_username}/{assignment.github_repo_name}"
            pa = PeerAssignment(
                assignment_id=assignment_id,
                evaluator_id=evaluator.id,
                evaluee_id=evaluee.id,
                repo_url=repo_url,
            )
            db.add(pa)
            assignments_out.append(pa)

    db.commit()

    created = (
        db.query(PeerAssignment)
        .filter(PeerAssignment.assignment_id == assignment_id)
        .options(selectinload(PeerAssignment.evaluator), selectinload(PeerAssignment.evaluee))
        .all()
    )
    return [_peer_assignment_to_out(pa) for pa in created]


# ── List ─────────────────────────────────────────────────────


@router.get(
    "/api/courses/{course_id}/assignments/{assignment_id}/peer-assignments",
    response_model=list[PeerAssignmentOut],
)
def list_peer_assignments(
    course_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    _get_assignment(db, course_id, assignment_id)

    pas = (
        db.query(PeerAssignment)
        .filter(PeerAssignment.assignment_id == assignment_id)
        .options(selectinload(PeerAssignment.evaluator), selectinload(PeerAssignment.evaluee))
        .all()
    )
    return [_peer_assignment_to_out(pa) for pa in pas]


# ── Export peer assignments CSV ──────────────────────────────


@router.get(
    "/api/courses/{course_id}/assignments/{assignment_id}/peer-assignments/export",
)
def export_peer_assignments_csv(
    course_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    _get_assignment(db, course_id, assignment_id)

    pas = (
        db.query(PeerAssignment)
        .filter(PeerAssignment.assignment_id == assignment_id)
        .options(selectinload(PeerAssignment.evaluator), selectinload(PeerAssignment.evaluee))
        .all()
    )

    fieldnames = ["evaluator_name", "evaluator_github", "evaluee_name", "evaluee_github", "repo_url"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()

    for pa in pas:
        writer.writerow({
            "evaluator_name": pa.evaluator.name,
            "evaluator_github": pa.evaluator.github_username,
            "evaluee_name": pa.evaluee.name,
            "evaluee_github": pa.evaluee.github_username,
            "repo_url": pa.repo_url,
        })

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=peer_assignments.csv"},
    )


# ── Send peer notification emails ────────────────────────────


@router.post(
    "/api/courses/{course_id}/assignments/{assignment_id}/peer-assignments/send-emails",
    response_model=BatchSendResult,
)
def send_peer_emails(
    course_id: int,
    assignment_id: int,
    data: PeerEmailSendRequest,
    db: Session = Depends(get_db),
    sender: EmailSender = Depends(get_email_sender),
):
    _get_course(db, course_id)
    _get_assignment(db, course_id, assignment_id)

    pas = (
        db.query(PeerAssignment)
        .filter(PeerAssignment.assignment_id == assignment_id)
        .options(selectinload(PeerAssignment.evaluator), selectinload(PeerAssignment.evaluee))
        .all()
    )

    by_evaluator: dict[int, list[PeerAssignment]] = {}
    for pa in pas:
        by_evaluator.setdefault(pa.evaluator_id, []).append(pa)

    sent = 0
    failed = 0
    errors: list[str] = []

    for evaluator_id, evals in by_evaluator.items():
        evaluator = evals[0].evaluator
        placeholders = defaultdict(
            str,
            student_name=evaluator.name,
            student_email=evaluator.email,
            github_username=evaluator.github_username,
        )
        for idx, pa in enumerate(evals, start=1):
            placeholders[f"repo_url_{idx}"] = pa.repo_url

        try:
            subject = data.subject.format_map(placeholders)
            body = data.body.format_map(placeholders)
        except (KeyError, ValueError) as exc:
            failed += 1
            errors.append(f"{evaluator.name}: template error: {exc}")
            continue

        try:
            sender.send(evaluator.email, subject, body)
            sent += 1
        except Exception as exc:
            failed += 1
            errors.append(f"{evaluator.name}: {exc}")

    return BatchSendResult(sent=sent, failed=failed, errors=errors)


# ── Import peer evaluations CSV ──────────────────────────────


@router.post(
    "/api/courses/{course_id}/assignments/{assignment_id}/peer-evaluations/import",
    response_model=PeerEvalImportResult,
)
def import_peer_evaluations_csv(
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
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="Empty CSV")

    required = {"evaluator_name", "evaluee_github"}
    missing = required - set(reader.fieldnames)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(sorted(missing))}")

    components = {gc.name: gc for gc in assignment.grading_components}
    reserved = {"evaluator_name", "evaluee_github", "feedback"}
    component_columns = [col for col in reader.fieldnames if col not in reserved]

    invalid_cols = [col for col in component_columns if col not in components]
    if invalid_cols:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown grading component columns: {', '.join(invalid_cols)}",
        )

    students = db.query(Student).filter(Student.course_id == course_id).all()
    students_by_name_lower = {}
    for s in students:
        students_by_name_lower.setdefault(s.name.lower(), []).append(s)
    students_by_gh = {s.github_username: s for s in students}

    pas = (
        db.query(PeerAssignment)
        .filter(PeerAssignment.assignment_id == assignment_id)
        .all()
    )
    pa_lookup: dict[tuple[int, int], PeerAssignment] = {}
    for pa in pas:
        pa_lookup[(pa.evaluator_id, pa.evaluee_id)] = pa

    imported = 0
    errors: list[ImportRowError] = []

    for i, row in enumerate(reader, start=2):
        evaluator_name = (row.get("evaluator_name") or "").strip()
        evaluee_gh = (row.get("evaluee_github") or "").strip()
        feedback = (row.get("feedback") or "").strip()

        if not evaluator_name:
            errors.append(ImportRowError(row=i, error="Missing evaluator_name"))
            continue
        if not evaluee_gh:
            errors.append(ImportRowError(row=i, error="Missing evaluee_github"))
            continue

        matches = students_by_name_lower.get(evaluator_name.lower(), [])
        if len(matches) == 1:
            evaluator = matches[0]
        elif len(matches) > 1:
            errors.append(ImportRowError(row=i, error=f"Ambiguous evaluator (multiple matches): {evaluator_name}"))
            continue
        else:
            errors.append(ImportRowError(row=i, error=f"Unrecognized evaluator: {evaluator_name}"))
            continue

        evaluee = students_by_gh.get(evaluee_gh)
        if not evaluee:
            errors.append(ImportRowError(row=i, error=f"Unknown evaluee github: {evaluee_gh}"))
            continue

        pa = pa_lookup.get((evaluator.id, evaluee.id))
        if not pa:
            errors.append(ImportRowError(row=i, error=f"No peer assignment for {evaluator_name} -> {evaluee_gh}"))
            continue

        row_ok = True
        for col in component_columns:
            val = (row.get(col) or "").strip()
            if not val:
                continue
            try:
                float(val)
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
                db.query(PeerEvaluation)
                .filter(
                    PeerEvaluation.peer_assignment_id == pa.id,
                    PeerEvaluation.grading_component_id == gc.id,
                )
                .first()
            )
            if existing:
                existing.score = score
                existing.feedback = feedback
            else:
                db.add(
                    PeerEvaluation(
                        peer_assignment_id=pa.id,
                        grading_component_id=gc.id,
                        score=score,
                        feedback=feedback,
                    )
                )

        imported += 1

    db.commit()
    return PeerEvalImportResult(imported=imported, errors=errors)


# ── Export peer evaluations CSV ──────────────────────────────


@router.get(
    "/api/courses/{course_id}/assignments/{assignment_id}/peer-evaluations/export",
)
def export_peer_evaluations_csv(
    course_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
):
    _get_course(db, course_id)
    assignment = _get_assignment(db, course_id, assignment_id)

    component_names = [gc.name for gc in assignment.grading_components]
    component_map = {gc.id: gc.name for gc in assignment.grading_components}

    pas = (
        db.query(PeerAssignment)
        .filter(PeerAssignment.assignment_id == assignment_id)
        .options(
            selectinload(PeerAssignment.evaluator),
            selectinload(PeerAssignment.evaluee),
            selectinload(PeerAssignment.peer_evaluations),
        )
        .all()
    )

    fieldnames = ["evaluator_name", "evaluee_github"] + component_names + ["feedback"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()

    for pa in pas:
        evals_by_component: dict[str, PeerEvaluation] = {}
        for pe in pa.peer_evaluations:
            cname = component_map.get(pe.grading_component_id, "")
            evals_by_component[cname] = pe

        row: dict[str, str] = {
            "evaluator_name": pa.evaluator.name,
            "evaluee_github": pa.evaluee.github_username,
        }
        feedback_parts = []
        for name in component_names:
            pe = evals_by_component.get(name)
            row[name] = str(pe.score) if pe else ""
            if pe and pe.feedback:
                feedback_parts.append(pe.feedback)

        row["feedback"] = feedback_parts[0] if feedback_parts else ""
        writer.writerow(row)

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=peer_evaluations.csv"},
    )
