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


def _csv_file(rows: list[dict]) -> dict:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)
    return {"file": ("grades.csv", buf.getvalue(), "text/csv")}


# ── Submit grades ─────────────────────────────────────────────


def test_submit_grades(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    gc_ids = [gc["id"] for gc in asgn["grading_components"]]
    student_id = _create_student(client, cid)
    _clone(client, cid, aid)

    resp = client.put(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/grades",
        json={"grades": [
            {"grading_component_id": gc_ids[0], "score": 45.0},
            {"grading_component_id": gc_ids[1], "score": 25.0},
        ]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    scores = {g["component_name"]: g["score"] for g in data}
    assert scores["Correctness"] == 45.0
    assert scores["Style"] == 25.0


def test_get_grades(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    gc_ids = [gc["id"] for gc in asgn["grading_components"]]
    student_id = _create_student(client, cid)
    _clone(client, cid, aid)

    client.put(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/grades",
        json={"grades": [{"grading_component_id": gc_ids[0], "score": 40.0}]},
    )

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/grades")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["score"] == 40.0
    assert data[0]["component_name"] == "Correctness"


def test_update_existing_grades(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    gc_ids = [gc["id"] for gc in asgn["grading_components"]]
    student_id = _create_student(client, cid)
    _clone(client, cid, aid)

    client.put(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/grades",
        json={"grades": [{"grading_component_id": gc_ids[0], "score": 40.0}]},
    )

    resp = client.put(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/grades",
        json={"grades": [{"grading_component_id": gc_ids[0], "score": 48.0}]},
    )
    assert resp.status_code == 200
    scores = {g["component_name"]: g["score"] for g in resp.json()}
    assert scores["Correctness"] == 48.0


def test_submit_grades_invalid_component(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    student_id = _create_student(client, cid)
    _clone(client, cid, aid)

    resp = client.put(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/grades",
        json={"grades": [{"grading_component_id": 9999, "score": 10.0}]},
    )
    assert resp.status_code == 400


def test_submit_grades_no_submission(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    student_id = _create_student(client, cid)
    # No clone = no submission

    resp = client.put(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/grades",
        json={"grades": [{"grading_component_id": 1, "score": 10.0}]},
    )
    assert resp.status_code == 404


# ── CSV import ─────────────────────────────────────────────────


def test_import_csv_valid(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    _create_student(client, cid, "Alice", "A001", "alice")
    _create_student(client, cid, "Bob", "A002", "bob")
    _clone(client, cid, aid)

    files = _csv_file([
        {"github_username": "alice", "Correctness": "45", "Style": "28"},
        {"github_username": "bob", "Correctness": "50", "Style": "30"},
    ])
    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/grades/import", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 2
    assert data["errors"] == []


def test_import_csv_invalid_component_name(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    _create_student(client, cid)
    _clone(client, cid, aid)

    files = _csv_file([
        {"github_username": "alice", "NonExistent": "10"},
    ])
    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/grades/import", files=files)
    assert resp.status_code == 400
    assert "Unknown grading component" in resp.json()["detail"]


def test_import_csv_invalid_github_username(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    _create_student(client, cid)
    _clone(client, cid, aid)

    files = _csv_file([
        {"github_username": "alice", "Correctness": "45"},
        {"github_username": "unknown_user", "Correctness": "40"},
    ])
    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/grades/import", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 1
    assert len(data["errors"]) == 1
    assert "unknown_user" in data["errors"][0]["error"]


def test_import_csv_invalid_score(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    _create_student(client, cid)
    _clone(client, cid, aid)

    files = _csv_file([
        {"github_username": "alice", "Correctness": "not_a_number"},
    ])
    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/grades/import", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 0
    assert len(data["errors"]) == 1


# ── CSV export ─────────────────────────────────────────────────


def test_export_csv(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    gc_ids = [gc["id"] for gc in asgn["grading_components"]]
    student_id = _create_student(client, cid)
    _clone(client, cid, aid)

    client.put(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/grades",
        json={"grades": [
            {"grading_component_id": gc_ids[0], "score": 45.0},
            {"grading_component_id": gc_ids[1], "score": 25.0},
        ]},
    )

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/grades/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["github_username"] == "alice"
    assert float(rows[0]["Correctness"]) == 45.0
    assert float(rows[0]["Style"]) == 25.0


def test_export_csv_empty(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/grades/export")
    assert resp.status_code == 200
    reader = csv.DictReader(io.StringIO(resp.text))
    assert list(reader) == []


# ── Dashboard includes evaluator_grade_total ────────────────────


@patch("app.routes.submissions.git_service")
def test_dashboard_includes_evaluator_grade_total(mock_git, client):
    mock_git.clone_repo.return_value = None
    mock_git.repo_exists.return_value = False

    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    gc_ids = [gc["id"] for gc in asgn["grading_components"]]
    student_id = _create_student(client, cid)

    client.post(f"/api/courses/{cid}/assignments/{aid}/clone")

    client.put(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/grades",
        json={"grades": [
            {"grading_component_id": gc_ids[0], "score": 45.0},
            {"grading_component_id": gc_ids[1], "score": 25.0},
        ]},
    )

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["evaluator_grade_total"] == 70.0


@patch("app.routes.submissions.git_service")
def test_dashboard_no_grades_returns_null(mock_git, client):
    mock_git.clone_repo.return_value = None
    mock_git.repo_exists.return_value = False

    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    _create_student(client, cid)

    client.post(f"/api/courses/{cid}/assignments/{aid}/clone")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard")
    rows = resp.json()
    assert rows[0]["evaluator_grade_total"] is None
