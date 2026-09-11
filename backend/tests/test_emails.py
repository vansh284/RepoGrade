from unittest.mock import MagicMock

from app.email_service import get_email_sender


class FakeEmailSender:
    def __init__(self):
        self.sent: list[dict] = []

    def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append({"to": to, "subject": subject, "body": body})


def _setup_course_and_assignment(client):
    """Create a course and assignment, return (course_id, assignment_id)."""
    c = client.post("/api/courses", json={"name": "CS101"}).json()
    a = client.post(
        f"/api/courses/{c['id']}/assignments",
        json={
            "name": "HW1",
            "github_repo_name": "hw1",
            "checks_directory": "/checks",
            "evaluator_weight": 0.6,
            "peer_weight": 0.4,
            "grading_components": [],
            "environment_variables": [],
        },
    ).json()
    return c["id"], a["id"]


def _create_student(client, course_id, name="Alice", student_id="s1", email="alice@test.com", github="alice"):
    return client.post(
        f"/api/courses/{course_id}/students",
        json={"name": name, "student_id": student_id, "email": email, "github_username": github},
    ).json()


# ── Template CRUD ─────────────────────────────────────────────


def test_create_email_template(client):
    cid, aid = _setup_course_and_assignment(client)
    resp = client.post(
        f"/api/courses/{cid}/assignments/{aid}/email-templates",
        json={
            "name": "Late submission",
            "subject_template": "Re: {assignment_name}",
            "body_template": "Hi {student_name}, your submission was late.",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Late submission"
    assert data["assignment_id"] == aid


def test_list_email_templates(client):
    cid, aid = _setup_course_and_assignment(client)
    client.post(
        f"/api/courses/{cid}/assignments/{aid}/email-templates",
        json={"name": "T1", "subject_template": "S1", "body_template": "B1"},
    )
    client.post(
        f"/api/courses/{cid}/assignments/{aid}/email-templates",
        json={"name": "T2", "subject_template": "S2", "body_template": "B2"},
    )
    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/email-templates")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_email_template(client):
    cid, aid = _setup_course_and_assignment(client)
    created = client.post(
        f"/api/courses/{cid}/assignments/{aid}/email-templates",
        json={"name": "Old", "subject_template": "S", "body_template": "B"},
    ).json()
    resp = client.put(
        f"/api/courses/{cid}/assignments/{aid}/email-templates/{created['id']}",
        json={"name": "New", "subject_template": "S2", "body_template": "B2"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "New"
    assert resp.json()["subject_template"] == "S2"


def test_delete_email_template(client):
    cid, aid = _setup_course_and_assignment(client)
    created = client.post(
        f"/api/courses/{cid}/assignments/{aid}/email-templates",
        json={"name": "Del", "subject_template": "S", "body_template": "B"},
    ).json()
    resp = client.delete(
        f"/api/courses/{cid}/assignments/{aid}/email-templates/{created['id']}"
    )
    assert resp.status_code == 204
    listing = client.get(f"/api/courses/{cid}/assignments/{aid}/email-templates")
    assert len(listing.json()) == 0


def test_template_not_found(client):
    cid, aid = _setup_course_and_assignment(client)
    resp = client.get(
        f"/api/courses/{cid}/assignments/{aid}/email-templates/9999/preview?student_id=1"
    )
    assert resp.status_code == 404


# ── Preview ───────────────────────────────────────────────────


def test_preview_email(client):
    cid, aid = _setup_course_and_assignment(client)
    student = _create_student(client, cid)
    template = client.post(
        f"/api/courses/{cid}/assignments/{aid}/email-templates",
        json={
            "name": "Feedback",
            "subject_template": "{assignment_name} feedback for {student_name}",
            "body_template": "Hi {student_name} ({student_id}), check {course_name}.",
        },
    ).json()
    resp = client.get(
        f"/api/courses/{cid}/assignments/{aid}/email-templates/{template['id']}/preview",
        params={"student_id": student["id"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["subject"] == "HW1 feedback for Alice"
    assert "Alice" in data["body"]
    assert "s1" in data["body"]
    assert "CS101" in data["body"]


def test_preview_missing_student(client):
    cid, aid = _setup_course_and_assignment(client)
    template = client.post(
        f"/api/courses/{cid}/assignments/{aid}/email-templates",
        json={"name": "T", "subject_template": "S", "body_template": "B"},
    ).json()
    resp = client.get(
        f"/api/courses/{cid}/assignments/{aid}/email-templates/{template['id']}/preview",
        params={"student_id": 9999},
    )
    assert resp.status_code == 404


def test_preview_unknown_placeholder_graceful(client):
    """Unknown placeholders should render as empty strings, not crash."""
    cid, aid = _setup_course_and_assignment(client)
    student = _create_student(client, cid)
    template = client.post(
        f"/api/courses/{cid}/assignments/{aid}/email-templates",
        json={
            "name": "T",
            "subject_template": "{unknown_thing} subject",
            "body_template": "Body {another_unknown}",
        },
    ).json()
    resp = client.get(
        f"/api/courses/{cid}/assignments/{aid}/email-templates/{template['id']}/preview",
        params={"student_id": student["id"]},
    )
    assert resp.status_code == 200
    assert resp.json()["subject"] == " subject"
    assert resp.json()["body"] == "Body "


# ── Batch Send ────────────────────────────────────────────────


def _setup_submission_with_check(client, db_override, cid, aid, student_id, passed):
    """Create a submission and check result directly in the DB."""
    from app.models import CheckResult, CloneStatus, Submission

    db = next(db_override())
    sub = Submission(
        student_id=student_id,
        assignment_id=aid,
        repo_url=f"https://github.com/user/hw1",
        clone_status=CloneStatus.cloned,
        clone_path="/tmp/repo",
    )
    db.add(sub)
    db.flush()
    sub_id = sub.id
    cr = CheckResult(
        submission_id=sub_id,
        check_name="lint",
        passed=passed,
        message="Lint failed" if not passed else "OK",
        details="details here" if not passed else "",
    )
    db.add(cr)
    db.commit()
    db.close()
    return sub_id


def test_batch_send_emails_to_failed_students(client):
    from app.database import get_db
    from app.main import app

    fake = FakeEmailSender()
    app.dependency_overrides[get_email_sender] = lambda: fake

    cid, aid = _setup_course_and_assignment(client)
    alice = _create_student(client, cid, name="Alice", student_id="s1", email="alice@test.com", github="alice")
    bob = _create_student(client, cid, name="Bob", student_id="s2", email="bob@test.com", github="bob")

    db_override = app.dependency_overrides[get_db]
    _setup_submission_with_check(client, db_override, cid, aid, alice["id"], passed=False)
    _setup_submission_with_check(client, db_override, cid, aid, bob["id"], passed=True)

    template = client.post(
        f"/api/courses/{cid}/assignments/{aid}/email-templates",
        json={
            "name": "Lint fail",
            "subject_template": "{check_name} failed for {student_name}",
            "body_template": "Hi {student_name}, {check_message}. Details: {check_details}",
        },
    ).json()

    resp = client.post(
        f"/api/courses/{cid}/assignments/{aid}/email-templates/{template['id']}/send",
        params={"check_name": "lint"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sent"] == 1
    assert data["failed"] == 0

    # Verify the fake sender received exactly one email, to Alice
    assert len(fake.sent) == 1
    assert fake.sent[0]["to"] == "alice@test.com"
    assert "lint" in fake.sent[0]["subject"]
    assert "Alice" in fake.sent[0]["subject"]
    assert "Lint failed" in fake.sent[0]["body"]
    assert "details here" in fake.sent[0]["body"]


def test_batch_send_no_failed_students(client):
    from app.database import get_db
    from app.main import app

    fake = FakeEmailSender()
    app.dependency_overrides[get_email_sender] = lambda: fake

    cid, aid = _setup_course_and_assignment(client)
    alice = _create_student(client, cid)

    db_override = app.dependency_overrides[get_db]
    _setup_submission_with_check(client, db_override, cid, aid, alice["id"], passed=True)

    template = client.post(
        f"/api/courses/{cid}/assignments/{aid}/email-templates",
        json={"name": "T", "subject_template": "S", "body_template": "B"},
    ).json()

    resp = client.post(
        f"/api/courses/{cid}/assignments/{aid}/email-templates/{template['id']}/send",
        params={"check_name": "lint"},
    )
    assert resp.status_code == 200
    assert resp.json()["sent"] == 0
    assert len(fake.sent) == 0


def test_batch_send_student_no_check_results(client):
    """Students with no check results should not receive emails."""
    from app.main import app

    fake = FakeEmailSender()
    app.dependency_overrides[get_email_sender] = lambda: fake

    cid, aid = _setup_course_and_assignment(client)
    _create_student(client, cid)

    template = client.post(
        f"/api/courses/{cid}/assignments/{aid}/email-templates",
        json={"name": "T", "subject_template": "S", "body_template": "B"},
    ).json()

    resp = client.post(
        f"/api/courses/{cid}/assignments/{aid}/email-templates/{template['id']}/send",
        params={"check_name": "lint"},
    )
    assert resp.status_code == 200
    assert resp.json()["sent"] == 0
    assert len(fake.sent) == 0


def test_batch_send_sender_error_captured(client):
    """If the sender raises, it should count as failed, not crash."""
    from app.database import get_db
    from app.main import app

    class FailingSender:
        def send(self, to, subject, body):
            raise RuntimeError("SMTP connection refused")

    app.dependency_overrides[get_email_sender] = lambda: FailingSender()

    cid, aid = _setup_course_and_assignment(client)
    alice = _create_student(client, cid)

    db_override = app.dependency_overrides[get_db]
    _setup_submission_with_check(client, db_override, cid, aid, alice["id"], passed=False)

    template = client.post(
        f"/api/courses/{cid}/assignments/{aid}/email-templates",
        json={"name": "T", "subject_template": "S", "body_template": "B"},
    ).json()

    resp = client.post(
        f"/api/courses/{cid}/assignments/{aid}/email-templates/{template['id']}/send",
        params={"check_name": "lint"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["sent"] == 0
    assert data["failed"] == 1
    assert "SMTP connection refused" in data["errors"][0]
