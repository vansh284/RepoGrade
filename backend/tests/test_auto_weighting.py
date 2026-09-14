import csv
import io
from unittest.mock import patch


def _create_course(client):
    return client.post("/api/courses", json={"name": "CS201"}).json()["id"]


def _create_assignment(client, course_id, num_main=None, num_peer=None):
    return client.post(
        f"/api/courses/{course_id}/assignments",
        json={
            "name": "HW1",
            "github_repo_name": "cs201-hw1",
            "checks_directory": "/checks/hw1",
            "evaluator_weight": 0.7,
            "peer_weight": 0.3,
            "num_main_evaluators": num_main,
            "num_peer_evaluators": num_peer,
            "grading_components": [
                {"name": "Correctness", "max_points": 100, "weight": 1.0},
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


def _submit_grades(client, cid, aid, student_id, gc_id, score, evaluator_id="default"):
    client.put(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/grades",
        json={
            "evaluator_id": evaluator_id,
            "grades": [{"grading_component_id": gc_id, "score": score}],
        },
    )


def _setup_peer_eval(client, cid, aid, evaluator_student_id, evaluee_student_id, gc_id, score):
    from app.database import get_db
    from app.main import app
    from app.models import PeerAssignment, PeerEvaluation, Submission

    db_gen = app.dependency_overrides[get_db]()
    db = next(db_gen)
    sub = db.query(Submission).filter(
        Submission.student_id == evaluee_student_id,
        Submission.assignment_id == aid,
    ).first()
    pa = PeerAssignment(
        assignment_id=aid,
        evaluator_id=evaluator_student_id,
        evaluee_id=evaluee_student_id,
        repo_url=sub.repo_url if sub else "https://github.com/test/repo",
    )
    db.add(pa)
    db.flush()
    pe = PeerEvaluation(
        peer_assignment_id=pa.id,
        grading_component_id=gc_id,
        score=score,
    )
    db.add(pe)
    db.commit()
    db.close()


# ── Test: NULL counts = backward compat (no auto-weighting) ──


def test_null_counts_no_auto_weighting(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid, num_main=None, num_peer=None)
    aid = asgn["id"]
    gc_id = asgn["grading_components"][0]["id"]
    student_id = _create_student(client, cid)
    _clone(client, cid, aid)

    _submit_grades(client, cid, aid, student_id, gc_id, 80.0)

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 1
    # evaluator_weight=0.7, peer_weight=0.3, no peer scores -> peer treated as 0
    # consolidated = 0.7 * 80 + 0.3 * 0 = 56, final = 1.0 * 56 = 56
    assert rows[0]["final_grade"] == 56.0
    assert rows[0]["incomplete_pools"] == []


# ── Test: auto-weight when only main evaluators present ──


def test_auto_weight_only_main_evaluators(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid, num_main=2, num_peer=2)
    aid = asgn["id"]
    gc_id = asgn["grading_components"][0]["id"]
    student_id = _create_student(client, cid)
    _clone(client, cid, aid)

    _submit_grades(client, cid, aid, student_id, gc_id, 80.0, evaluator_id="ta1")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard")
    rows = resp.json()
    # No peer grades -> peer pool weight redistributed to main pool
    # effective weight: ew=1.0, pw=0.0
    # consolidated = 1.0 * 80 = 80
    assert rows[0]["final_grade"] == 80.0
    assert "peer" in rows[0]["incomplete_pools"]
    assert "evaluator" not in rows[0]["incomplete_pools"]


# ── Test: auto-weight when only peer evaluators present ──


def test_auto_weight_only_peer_evaluators(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid, num_main=1, num_peer=2)
    aid = asgn["id"]
    gc_id = asgn["grading_components"][0]["id"]
    student_id = _create_student(client, cid)
    evaluator_student = _create_student(client, cid, name="Bob", sid="B001", gh="bob")
    _clone(client, cid, aid)

    _setup_peer_eval(client, cid, aid, evaluator_student, student_id, gc_id, 90.0)

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard")
    rows = resp.json()
    alice_row = [r for r in rows if r["student_name"] == "Alice"][0]
    # No main grades -> main pool weight redistributed to peer pool
    # effective weight: ew=0.0, pw=1.0
    # consolidated = 1.0 * 90 = 90
    assert alice_row["final_grade"] == 90.0
    assert "evaluator" in alice_row["incomplete_pools"]


# ── Test: both pools present, no auto-weighting needed ──


def test_both_pools_present(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid, num_main=1, num_peer=1)
    aid = asgn["id"]
    gc_id = asgn["grading_components"][0]["id"]
    student_id = _create_student(client, cid)
    evaluator_student = _create_student(client, cid, name="Bob", sid="B001", gh="bob")
    _clone(client, cid, aid)

    _submit_grades(client, cid, aid, student_id, gc_id, 80.0)
    _setup_peer_eval(client, cid, aid, evaluator_student, student_id, gc_id, 90.0)

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard")
    rows = resp.json()
    alice_row = [r for r in rows if r["student_name"] == "Alice"][0]
    # Normal weighting: 0.7 * 80 + 0.3 * 90 = 56 + 27 = 83
    assert alice_row["final_grade"] == 83.0
    assert alice_row["incomplete_pools"] == []


# ── Test: multiple main evaluators averaged ──


def test_multiple_main_evaluators_averaged(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid, num_main=2, num_peer=None)
    aid = asgn["id"]
    gc_id = asgn["grading_components"][0]["id"]
    student_id = _create_student(client, cid)
    _clone(client, cid, aid)

    _submit_grades(client, cid, aid, student_id, gc_id, 80.0, evaluator_id="ta1")
    _submit_grades(client, cid, aid, student_id, gc_id, 90.0, evaluator_id="ta2")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard")
    rows = resp.json()
    # Average of main evaluators: (80 + 90) / 2 = 85
    # No peer expected (null) -> no auto-weighting for peer
    # But num_main is set, so auto-weighting is active
    # Only main pool present -> ew=1.0, pw=0.0
    assert rows[0]["final_grade"] == 85.0


# ── Test: zero in both pools = no final grade ──


def test_zero_both_pools_no_grade(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid, num_main=1, num_peer=1)
    aid = asgn["id"]
    student_id = _create_student(client, cid)
    _clone(client, cid, aid)

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard")
    rows = resp.json()
    assert rows[0]["final_grade"] is None
    assert "evaluator" in rows[0]["incomplete_pools"]
    assert "peer" in rows[0]["incomplete_pools"]


# ── Test: canvas export with auto-weighted grades ──


def test_canvas_export_auto_weighted(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid, num_main=1, num_peer=1)
    aid = asgn["id"]
    gc_id = asgn["grading_components"][0]["id"]
    student_id = _create_student(client, cid)
    _clone(client, cid, aid)

    _submit_grades(client, cid, aid, student_id, gc_id, 80.0)

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/canvas-export")
    assert resp.status_code == 200
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 1
    # Auto-weighted: only main present -> ew=1.0
    assert float(rows[0]["Final Grade"]) == 80.0


# ── Test: assignment CRUD with evaluator counts ──


def test_assignment_stores_evaluator_counts(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid, num_main=3, num_peer=5)
    assert asgn["num_main_evaluators"] == 3
    assert asgn["num_peer_evaluators"] == 5

    resp = client.get(f"/api/courses/{cid}/assignments/{asgn['id']}")
    data = resp.json()
    assert data["num_main_evaluators"] == 3
    assert data["num_peer_evaluators"] == 5


def test_assignment_null_counts_by_default(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    assert asgn["num_main_evaluators"] is None
    assert asgn["num_peer_evaluators"] is None


# ── Test: multiple main evaluators via API ──


def test_submit_grades_with_evaluator_id(client):
    cid = _create_course(client)
    asgn = _create_assignment(client, cid)
    aid = asgn["id"]
    gc_id = asgn["grading_components"][0]["id"]
    student_id = _create_student(client, cid)
    _clone(client, cid, aid)

    resp1 = client.put(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/grades",
        json={
            "evaluator_id": "ta1",
            "grades": [{"grading_component_id": gc_id, "score": 80.0}],
        },
    )
    assert resp1.status_code == 200

    resp2 = client.put(
        f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/grades",
        json={
            "evaluator_id": "ta2",
            "grades": [{"grading_component_id": gc_id, "score": 90.0}],
        },
    )
    assert resp2.status_code == 200

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/students/{student_id}/grades")
    data = resp.json()
    assert len(data) == 2
    scores = sorted([g["score"] for g in data])
    assert scores == [80.0, 90.0]
    evaluator_ids = sorted([g["evaluator_id"] for g in data])
    assert evaluator_ids == ["ta1", "ta2"]
