import csv
import io
from unittest.mock import patch


def _create_course(client):
    return client.post("/api/courses", json={"name": "CS201"}).json()["id"]


def _create_assignment(client, course_id):
    return client.post(
        f"/api/courses/{course_id}/assignments",
        json={
            "name": "HW1",
            "github_repo_name": "cs201-hw1",
            "checks_directory": "/checks/hw1",
            "evaluator_weight": 0.7,
            "peer_weight": 0.3,
            "grading_components": [
                {"name": "Correctness", "max_points": 100, "weight": 0.6},
                {"name": "Style", "max_points": 50, "weight": 0.4},
            ],
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


# ── Penalty CRUD ─────────────────────────────────────────────


def test_add_penalty(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    student_id = _create_student(client, cid)
    _clone(client, cid, aid)

    resp = client.post(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/penalties",
        json={"reason": "Late submission", "amount": 5.0},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["reason"] == "Late submission"
    assert data["amount"] == 5.0
    assert "id" in data


def test_list_penalties(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    student_id = _create_student(client, cid)
    _clone(client, cid, aid)

    client.post(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/penalties",
        json={"reason": "Late", "amount": 5.0},
    )
    client.post(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/penalties",
        json={"reason": "Plagiarism", "amount": 10.0},
    )

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/penalties")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert sum(p["amount"] for p in data) == 15.0


def test_update_penalty(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    student_id = _create_student(client, cid)
    _clone(client, cid, aid)

    created = client.post(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/penalties",
        json={"reason": "Late", "amount": 5.0},
    ).json()

    resp = client.put(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/penalties/{created['id']}",
        json={"reason": "Late (revised)", "amount": 3.0},
    )
    assert resp.status_code == 200
    assert resp.json()["amount"] == 3.0
    assert resp.json()["reason"] == "Late (revised)"


def test_delete_penalty(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    student_id = _create_student(client, cid)
    _clone(client, cid, aid)

    created = client.post(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/penalties",
        json={"reason": "Late", "amount": 5.0},
    ).json()

    resp = client.delete(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/penalties/{created['id']}",
    )
    assert resp.status_code == 204

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/penalties")
    assert resp.json() == []


def test_penalty_not_found(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    student_id = _create_student(client, cid)
    _clone(client, cid, aid)

    resp = client.put(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/penalties/9999",
        json={"reason": "x", "amount": 1.0},
    )
    assert resp.status_code == 404

    resp = client.delete(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/penalties/9999",
    )
    assert resp.status_code == 404


# ── Grade consolidation formula ──────────────────────────────


@patch("app.routes.submissions.git_service")
def test_final_grade_consolidation(mock_git, client):
    """
    evaluator_weight=0.7, peer_weight=0.3
    Components: Correctness(weight=0.6), Style(weight=0.4)

    Student Alice:
      Evaluator: Correctness=80, Style=40
      Peer avg:  Correctness=90, Style=45
      Penalty: 5

    Consolidated Correctness = 0.7*80 + 0.3*90 = 56 + 27 = 83
    Consolidated Style       = 0.7*40 + 0.3*45 = 28 + 13.5 = 41.5
    Final = 0.6*83 + 0.4*41.5 - 5 = 49.8 + 16.6 - 5 = 61.4
    """
    mock_git.clone_repo.return_value = None
    mock_git.repo_exists.return_value = False

    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    gc_ids = [gc["id"] for gc in asgn["grading_components"]]
    alice_id = _create_student(client, cid, "Alice Smith", "A001", "alice")
    bob_id = _create_student(client, cid, "Bob Jones", "A002", "bob")

    client.post(f"/api/courses/{cid}/assignments/{aid}/clone")

    client.put(
        f"/api/courses/{cid}/assignments/{aid}/students/{alice_id}/grades",
        json={"grades": [
            {"grading_component_id": gc_ids[0], "score": 80.0},
            {"grading_component_id": gc_ids[1], "score": 40.0},
        ]},
    )

    client.post(
        f"/api/courses/{cid}/assignments/{aid}/peer-assignments/generate?count=1",
    )

    pas = client.get(f"/api/courses/{cid}/assignments/{aid}/peer-assignments").json()
    alice_evaluee_pas = [pa for pa in pas if pa["evaluee_id"] == alice_id]

    if alice_evaluee_pas:
        pa = alice_evaluee_pas[0]
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["evaluator_name", "evaluee_github", "Correctness", "Style"])
        writer.writeheader()
        writer.writerow({
            "evaluator_name": pa["evaluator_name"],
            "evaluee_github": "alice",
            "Correctness": "90",
            "Style": "45",
        })
        buf.seek(0)
        client.post(
            f"/api/courses/{cid}/assignments/{aid}/peer-evaluations/import",
            files={"file": ("evals.csv", buf.getvalue(), "text/csv")},
        )

    client.post(
        f"/api/courses/{cid}/assignments/{aid}/students/{alice_id}/penalties",
        json={"reason": "Late", "amount": 5.0},
    )

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard")
    assert resp.status_code == 200
    rows = resp.json()
    alice_row = next(r for r in rows if r["student_db_id"] == alice_id)

    assert alice_row["penalty_count"] == 1
    assert alice_row["penalty_total"] == 5.0
    assert alice_row["final_grade"] is not None
    assert abs(alice_row["final_grade"] - 61.4) < 0.01


# ── Canvas CSV export ────────────────────────────────────────


@patch("app.routes.submissions.git_service")
def test_canvas_export_format(mock_git, client):
    mock_git.clone_repo.return_value = None
    mock_git.repo_exists.return_value = False

    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    gc_ids = [gc["id"] for gc in asgn["grading_components"]]
    _create_student(client, cid, "Alice Smith", "A001", "alice")

    client.post(f"/api/courses/{cid}/assignments/{aid}/clone")

    client.put(
        f"/api/courses/{cid}/assignments/{aid}/students/1/grades",
        json={"grades": [
            {"grading_component_id": gc_ids[0], "score": 80.0},
            {"grading_component_id": gc_ids[1], "score": 40.0},
        ]},
    )

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/canvas-export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]

    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 1

    row = rows[0]
    assert row["Student"] == "Smith, Alice"
    assert row["ID"] == "A001"
    assert row["SIS Login ID"] == "alice@example.com"
    assert "Correctness" in row
    assert "Style" in row
    assert "Final Grade" in row
    assert row["Final Grade"] != ""


@patch("app.routes.submissions.git_service")
def test_canvas_export_no_grades(mock_git, client):
    mock_git.clone_repo.return_value = None
    mock_git.repo_exists.return_value = False

    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    _create_student(client, cid, "Alice Smith", "A001", "alice")

    client.post(f"/api/courses/{cid}/assignments/{aid}/clone")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/canvas-export")
    assert resp.status_code == 200
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["Final Grade"] == ""


def test_canvas_export_name_parsing(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    _create_student(client, cid, "Madonna", "A001", "madonna")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/canvas-export")
    assert resp.status_code == 200
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert rows[0]["Student"] == "Madonna"
    assert "X-Name-Warnings" in resp.headers


# ── Dashboard with penalties ──────────────────────────────────


@patch("app.routes.submissions.git_service")
def test_dashboard_includes_penalty_info(mock_git, client):
    mock_git.clone_repo.return_value = None
    mock_git.repo_exists.return_value = False

    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    student_id = _create_student(client, cid)

    client.post(f"/api/courses/{cid}/assignments/{aid}/clone")

    client.post(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/penalties",
        json={"reason": "Late", "amount": 5.0},
    )
    client.post(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/penalties",
        json={"reason": "Formatting", "amount": 2.0},
    )

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["penalty_count"] == 2
    assert rows[0]["penalty_total"] == 7.0
