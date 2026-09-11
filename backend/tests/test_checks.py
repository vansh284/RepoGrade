import csv
import io
import subprocess
from unittest.mock import patch

from app.check_service import CheckOutput


def _create_course(client):
    return client.post("/api/courses", json={"name": "CS201"}).json()["id"]


def _create_assignment(client, course_id, checks_dir="/checks/hw1"):
    return client.post(
        f"/api/courses/{course_id}/assignments",
        json={
            "name": "HW1",
            "github_repo_name": "cs201-hw1",
            "checks_directory": checks_dir,
            "evaluator_weight": 0.7,
            "peer_weight": 0.3,
            "grading_components": [],
            "environment_variables": [{"key": "DEADLINE", "value": "2026-10-01"}],
        },
    ).json()["id"]


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


def _clone_repos(client, course_id, assignment_id, mock_git):
    mock_git.clone_repo.return_value = None
    mock_git.repo_exists.return_value = False
    client.post(f"/api/courses/{course_id}/assignments/{assignment_id}/clone")


def _setup_cloned(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    _create_student(client, cid, "Alice", "A001", "alice")
    _create_student(client, cid, "Bob", "A002", "bob")
    return cid, aid


# ── Run checks endpoint ────────────────────────────────────────


@patch("app.routes.checks.check_service")
@patch("app.routes.submissions.git_service")
def test_run_checks_success(mock_git, mock_checks, client):
    cid, aid = _setup_cloned(client)
    _clone_repos(client, cid, aid, mock_git)

    mock_checks.discover_checks.return_value = ["/checks/hw1/style.py", "/checks/hw1/tests.py"]
    mock_checks.run_check.return_value = CheckOutput(
        passed=True, message="All tests passed", details="", stderr=""
    )

    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/run-checks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4  # 2 students * 2 checks
    assert data["completed"] == 4

    assert mock_checks.run_check.call_count == 4


@patch("app.routes.checks.check_service")
@patch("app.routes.submissions.git_service")
def test_run_checks_failure(mock_git, mock_checks, client):
    cid, aid = _setup_cloned(client)
    _clone_repos(client, cid, aid, mock_git)

    mock_checks.discover_checks.return_value = ["/checks/hw1/style.py"]
    mock_checks.run_check.return_value = CheckOutput(
        passed=False, message="Style errors found", details="line 5: bad indent", stderr="traceback"
    )

    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/run-checks")
    assert resp.status_code == 200

    dashboard = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard").json()
    for row in dashboard:
        assert len(row["check_results"]) == 1
        cr = row["check_results"][0]
        assert cr["passed"] is False
        assert cr["message"] == "Style errors found"
        assert cr["details"] == "line 5: bad indent"
        assert cr["stderr"] == "traceback"


@patch("app.routes.checks.check_service")
@patch("app.routes.submissions.git_service")
def test_run_checks_env_vars(mock_git, mock_checks, client):
    cid, aid = _setup_cloned(client)
    _clone_repos(client, cid, aid, mock_git)

    mock_checks.discover_checks.return_value = ["/checks/hw1/check.py"]

    captured_envs = []

    def capture_run_check(script_path, cwd, env):
        captured_envs.append(dict(env))
        return CheckOutput(passed=True, message="ok", details="", stderr="")

    mock_checks.run_check.side_effect = capture_run_check

    client.post(f"/api/courses/{cid}/assignments/{aid}/run-checks")

    assert len(captured_envs) == 2
    for env in captured_envs:
        assert env["ASSIGNMENT_NAME"] == "HW1"
        assert "STUDENT_USERNAME" in env
        assert env["DEADLINE"] == "2026-10-01"

    usernames = {env["STUDENT_USERNAME"] for env in captured_envs}
    assert usernames == {"alice", "bob"}


@patch("app.routes.checks.check_service")
@patch("app.routes.submissions.git_service")
def test_run_checks_reruns_update_results(mock_git, mock_checks, client):
    cid, aid = _setup_cloned(client)
    _clone_repos(client, cid, aid, mock_git)

    mock_checks.discover_checks.return_value = ["/checks/hw1/check.py"]
    mock_checks.run_check.return_value = CheckOutput(
        passed=False, message="fail", details="", stderr=""
    )

    client.post(f"/api/courses/{cid}/assignments/{aid}/run-checks")

    mock_checks.run_check.return_value = CheckOutput(
        passed=True, message="pass", details="", stderr=""
    )

    client.post(f"/api/courses/{cid}/assignments/{aid}/run-checks")

    results = client.get(f"/api/courses/{cid}/assignments/{aid}/check-results").json()
    assert all(r["passed"] for r in results)
    assert all(r["message"] == "pass" for r in results)
    assert len(results) == 2


@patch("app.routes.checks.check_service")
def test_run_checks_no_scripts(mock_checks, client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    mock_checks.discover_checks.return_value = []

    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/run-checks")
    assert resp.status_code == 400


@patch("app.routes.checks.check_service")
@patch("app.routes.submissions.git_service")
def test_run_checks_no_cloned_submissions(mock_git, mock_checks, client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    _create_student(client, cid)

    mock_checks.discover_checks.return_value = ["/checks/hw1/check.py"]

    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/run-checks")
    assert resp.status_code == 400


def test_run_checks_course_not_found(client):
    resp = client.post("/api/courses/999/assignments/1/run-checks")
    assert resp.status_code == 404


def test_run_checks_assignment_not_found(client):
    cid = _create_course(client)
    resp = client.post(f"/api/courses/{cid}/assignments/999/run-checks")
    assert resp.status_code == 404


# ── Dashboard includes check results ───────────────────────────


@patch("app.routes.checks.check_service")
@patch("app.routes.submissions.git_service")
def test_dashboard_includes_check_results(mock_git, mock_checks, client):
    cid, aid = _setup_cloned(client)
    _clone_repos(client, cid, aid, mock_git)

    mock_checks.discover_checks.return_value = ["/checks/hw1/style.py"]
    mock_checks.run_check.return_value = CheckOutput(
        passed=True, message="Clean", details="no issues", stderr=""
    )

    client.post(f"/api/courses/{cid}/assignments/{aid}/run-checks")

    rows = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard").json()
    for row in rows:
        assert "check_results" in row
        assert len(row["check_results"]) == 1
        assert row["check_results"][0]["check_name"] == "style"
        assert row["check_results"][0]["passed"] is True


def test_dashboard_empty_check_results_before_run(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    _create_student(client, cid)

    rows = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard").json()
    assert len(rows) == 1
    assert rows[0]["check_results"] == []


# ── Progress endpoint ──────────────────────────────────────────


@patch("app.routes.checks.check_service")
@patch("app.routes.submissions.git_service")
def test_check_progress(mock_git, mock_checks, client):
    cid, aid = _setup_cloned(client)
    _clone_repos(client, cid, aid, mock_git)

    mock_checks.discover_checks.return_value = ["/checks/hw1/style.py", "/checks/hw1/tests.py"]
    mock_checks.run_check.return_value = CheckOutput(
        passed=True, message="ok", details="", stderr=""
    )

    client.post(f"/api/courses/{cid}/assignments/{aid}/run-checks")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/check-results/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert data["completed"] == 4


@patch("app.routes.checks.check_service")
@patch("app.routes.submissions.git_service")
def test_check_progress_before_run(mock_git, mock_checks, client):
    cid, aid = _setup_cloned(client)
    _clone_repos(client, cid, aid, mock_git)

    mock_checks.discover_checks.return_value = ["/checks/hw1/check.py"]

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/check-results/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["completed"] == 0


# ── CSV export ─────────────────────────────────────────────────


@patch("app.routes.checks.check_service")
@patch("app.routes.submissions.git_service")
def test_export_check_results_csv(mock_git, mock_checks, client):
    cid, aid = _setup_cloned(client)
    _clone_repos(client, cid, aid, mock_git)

    mock_checks.discover_checks.return_value = ["/checks/hw1/style.py"]
    mock_checks.run_check.return_value = CheckOutput(
        passed=True, message="Clean", details="", stderr=""
    )

    client.post(f"/api/courses/{cid}/assignments/{aid}/run-checks")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/check-results/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]

    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 2
    assert "style_passed" in reader.fieldnames
    assert "style_message" in reader.fieldnames
    for row in rows:
        assert row["style_passed"] == "True"
        assert row["style_message"] == "Clean"


@patch("app.routes.submissions.git_service")
def test_export_check_results_csv_empty(mock_git, client):
    cid, aid = _setup_cloned(client)
    _clone_repos(client, cid, aid, mock_git)

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/check-results/export")
    assert resp.status_code == 200
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 2
    assert set(reader.fieldnames) == {"student_name", "github_username"}


# ── Check results list endpoint ────────────────────────────────


@patch("app.routes.checks.check_service")
@patch("app.routes.submissions.git_service")
def test_list_check_results(mock_git, mock_checks, client):
    cid, aid = _setup_cloned(client)
    _clone_repos(client, cid, aid, mock_git)

    mock_checks.discover_checks.return_value = ["/checks/hw1/check.py"]
    mock_checks.run_check.return_value = CheckOutput(
        passed=True, message="ok", details="d", stderr="e"
    )

    client.post(f"/api/courses/{cid}/assignments/{aid}/run-checks")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/check-results")
    assert resp.status_code == 200
    results = resp.json()
    assert len(results) == 2
    assert all(r["check_name"] == "check" for r in results)
    assert all(r["passed"] for r in results)
