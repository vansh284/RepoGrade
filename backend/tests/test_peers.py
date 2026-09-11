import csv
import io
from unittest.mock import patch


def _create_course(client):
    return client.post("/api/courses", json={"name": "CS201"}).json()["id"]


def _create_assignment(client, course_id, components=None):
    if components is None:
        components = [
            {"name": "Correctness", "max_points": 50, "weight": 0.6},
            {"name": "Style", "max_points": 30, "weight": 0.4},
        ]
    return client.post(
        f"/api/courses/{course_id}/assignments",
        json={
            "name": "HW1",
            "github_repo_name": "cs201-hw1",
            "checks_directory": "/checks/hw1",
            "evaluator_weight": 0.7,
            "peer_weight": 0.3,
            "grading_components": components,
            "environment_variables": [],
        },
    ).json()


def _create_student(client, course_id, name="Alice", sid="A001", gh="alice"):
    return client.post(
        f"/api/courses/{course_id}/students",
        json={
            "name": name,
            "student_id": sid,
            "email": f"{gh}@example.com",
            "github_username": gh,
        },
    ).json()["id"]


def _clone(client, cid, aid):
    with patch("app.routes.submissions.git_service") as mock_git:
        mock_git.clone_repo.return_value = None
        mock_git.repo_exists.return_value = False
        client.post(f"/api/courses/{cid}/assignments/{aid}/clone")


def _csv_file(rows: list[dict], filename="evals.csv") -> dict:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)
    return {"file": (filename, buf.getvalue(), "text/csv")}


def _setup_4_students(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    s1 = _create_student(client, cid, "Alice", "A001", "alice")
    s2 = _create_student(client, cid, "Bob", "A002", "bob")
    s3 = _create_student(client, cid, "Charlie", "A003", "charlie")
    s4 = _create_student(client, cid, "Diana", "A004", "diana")
    _clone(client, cid, aid)
    return cid, aid, asgn, [s1, s2, s3, s4]


# ── Generate ─────────────────────────────────────────────────


def test_generate_peer_assignments(client):
    cid, aid, _, student_ids = _setup_4_students(client)

    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/peer-assignments/generate?count=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 8  # 4 students * 2 each

    evaluator_counts = {}
    evaluee_counts = {}
    for pa in data:
        evaluator_counts[pa["evaluator_id"]] = evaluator_counts.get(pa["evaluator_id"], 0) + 1
        evaluee_counts[pa["evaluee_id"]] = evaluee_counts.get(pa["evaluee_id"], 0) + 1

    for sid in student_ids:
        assert evaluator_counts[sid] == 2
        assert evaluee_counts[sid] == 2


def test_generate_even_distribution(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    for i in range(6):
        _create_student(client, cid, f"Student{i}", f"S{i:03d}", f"student{i}")
    _clone(client, cid, aid)

    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/peer-assignments/generate?count=2")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 12

    evaluee_counts = {}
    for pa in data:
        evaluee_counts[pa["evaluee_id"]] = evaluee_counts.get(pa["evaluee_id"], 0) + 1

    counts = list(evaluee_counts.values())
    assert max(counts) - min(counts) == 0  # perfectly even


def test_regenerate_replaces(client):
    cid, aid, _, _ = _setup_4_students(client)

    resp1 = client.post(f"/api/courses/{cid}/assignments/{aid}/peer-assignments/generate?count=2")
    assert resp1.status_code == 200
    assert len(resp1.json()) == 8

    resp2 = client.post(f"/api/courses/{cid}/assignments/{aid}/peer-assignments/generate?count=2")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 8

    listing = client.get(f"/api/courses/{cid}/assignments/{aid}/peer-assignments")
    assert len(listing.json()) == 8


def test_generate_too_few_students(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    _create_student(client, cid)

    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/peer-assignments/generate?count=2")
    assert resp.status_code == 400


def test_generate_count_too_high(client):
    cid, aid, _, _ = _setup_4_students(client)

    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/peer-assignments/generate?count=4")
    assert resp.status_code == 400


# ── List ─────────────────────────────────────────────────────


def test_list_peer_assignments(client):
    cid, aid, _, _ = _setup_4_students(client)
    client.post(f"/api/courses/{cid}/assignments/{aid}/peer-assignments/generate?count=2")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/peer-assignments")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 8
    for pa in data:
        assert "evaluator_name" in pa
        assert "evaluee_name" in pa
        assert "repo_url" in pa


# ── Export CSV ───────────────────────────────────────────────


def test_export_peer_assignments_csv(client):
    cid, aid, _, _ = _setup_4_students(client)
    client.post(f"/api/courses/{cid}/assignments/{aid}/peer-assignments/generate?count=2")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/peer-assignments/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]

    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 8
    assert set(reader.fieldnames) == {"evaluator_name", "evaluator_github", "evaluee_name", "evaluee_github", "repo_url"}


# ── Import peer evaluations ─────────────────────────────────


def test_import_peer_evaluations(client):
    cid, aid, _, _ = _setup_4_students(client)
    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/peer-assignments/generate?count=2")
    pas = resp.json()

    pa = pas[0]
    evaluator_name = pa["evaluator_name"]
    evaluee_resp = client.get(f"/api/courses/{cid}/students")
    students = {s["id"]: s for s in evaluee_resp.json()}
    evaluee_gh = students[pa["evaluee_id"]]["github_username"]

    files = _csv_file([{
        "evaluator_name": evaluator_name,
        "evaluee_github": evaluee_gh,
        "Correctness": "45",
        "Style": "28",
        "feedback": "Good work",
    }])
    resp = client.post(
        f"/api/courses/{cid}/assignments/{aid}/peer-evaluations/import",
        files=files,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 1
    assert data["errors"] == []


def test_import_unrecognized_evaluator(client):
    cid, aid, _, _ = _setup_4_students(client)
    client.post(f"/api/courses/{cid}/assignments/{aid}/peer-assignments/generate?count=2")

    pas = client.get(f"/api/courses/{cid}/assignments/{aid}/peer-assignments").json()
    pa = pas[0]
    students = {s["id"]: s for s in client.get(f"/api/courses/{cid}/students").json()}
    evaluee_gh = students[pa["evaluee_id"]]["github_username"]

    files = _csv_file([{
        "evaluator_name": "NonExistentPerson",
        "evaluee_github": evaluee_gh,
        "Correctness": "40",
        "Style": "25",
        "feedback": "",
    }])
    resp = client.post(
        f"/api/courses/{cid}/assignments/{aid}/peer-evaluations/import",
        files=files,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 0
    assert len(data["errors"]) == 1
    assert "Unrecognized" in data["errors"][0]["error"]


def test_import_case_insensitive_match(client):
    cid, aid, _, _ = _setup_4_students(client)
    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/peer-assignments/generate?count=2")
    pas = resp.json()

    pa = pas[0]
    evaluator_name = pa["evaluator_name"]
    students = {s["id"]: s for s in client.get(f"/api/courses/{cid}/students").json()}
    evaluee_gh = students[pa["evaluee_id"]]["github_username"]

    files = _csv_file([{
        "evaluator_name": evaluator_name.lower(),
        "evaluee_github": evaluee_gh,
        "Correctness": "42",
        "Style": "27",
        "feedback": "Decent",
    }])
    resp = client.post(
        f"/api/courses/{cid}/assignments/{aid}/peer-evaluations/import",
        files=files,
    )
    assert resp.status_code == 200
    assert resp.json()["imported"] == 1


# ── Export peer evaluations CSV ──────────────────────────────


def test_export_peer_evaluations_csv(client):
    cid, aid, _, _ = _setup_4_students(client)
    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/peer-assignments/generate?count=2")
    pas = resp.json()
    pa = pas[0]
    students = {s["id"]: s for s in client.get(f"/api/courses/{cid}/students").json()}
    evaluee_gh = students[pa["evaluee_id"]]["github_username"]

    files = _csv_file([{
        "evaluator_name": pa["evaluator_name"],
        "evaluee_github": evaluee_gh,
        "Correctness": "45",
        "Style": "28",
        "feedback": "Nice",
    }])
    client.post(f"/api/courses/{cid}/assignments/{aid}/peer-evaluations/import", files=files)

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/peer-evaluations/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]

    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 8
    scored_rows = [r for r in rows if r["Correctness"]]
    assert len(scored_rows) == 1
    assert float(scored_rows[0]["Correctness"]) == 45.0


# ── Send emails ──────────────────────────────────────────────


def test_send_peer_emails(client):
    from app.email_service import get_email_sender
    from app.main import app

    class FakeEmailSender:
        def __init__(self):
            self.sent: list[dict] = []

        def send(self, to, subject, body):
            self.sent.append({"to": to, "subject": subject, "body": body})

    fake = FakeEmailSender()
    app.dependency_overrides[get_email_sender] = lambda: fake

    try:
        cid, aid, _, _ = _setup_4_students(client)
        client.post(f"/api/courses/{cid}/assignments/{aid}/peer-assignments/generate?count=2")

        resp = client.post(
            f"/api/courses/{cid}/assignments/{aid}/peer-assignments/send-emails",
            json={
                "subject": "Peer Review for {student_name}",
                "body": "Hi {student_name}, please review: {repo_url_1} and {repo_url_2}",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["sent"] == 4
        assert data["failed"] == 0

        for email in fake.sent:
            assert "please review:" in email["body"]
            assert "https://github.com/" in email["body"]
    finally:
        app.dependency_overrides.pop(get_email_sender, None)


# ── Dashboard peer grade average ─────────────────────────────


@patch("app.routes.submissions.git_service")
def test_dashboard_peer_grade_average(mock_git, client):
    mock_git.clone_repo.return_value = None
    mock_git.repo_exists.return_value = False

    cid, aid, _, _ = _setup_4_students(client)

    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/peer-assignments/generate?count=2")
    pas = resp.json()

    students = {s["id"]: s for s in client.get(f"/api/courses/{cid}/students").json()}
    target_student_id = pas[0]["evaluee_id"]
    target_gh = students[target_student_id]["github_username"]

    evals_for_target = [pa for pa in pas if pa["evaluee_id"] == target_student_id]
    for pa in evals_for_target:
        evaluator_name = pa["evaluator_name"]
        files = _csv_file([{
            "evaluator_name": evaluator_name,
            "evaluee_github": target_gh,
            "Correctness": "40",
            "Style": "30",
            "feedback": "",
        }])
        client.post(f"/api/courses/{cid}/assignments/{aid}/peer-evaluations/import", files=files)

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard")
    assert resp.status_code == 200
    rows = resp.json()
    target_row = [r for r in rows if r["student_db_id"] == target_student_id][0]
    assert target_row["peer_grade_average"] == 70.0  # each evaluator scores 40+30=70, avg(70, 70) = 70

    no_eval_rows = [r for r in rows if r["peer_grade_average"] is None]
    assert len(no_eval_rows) == 3
