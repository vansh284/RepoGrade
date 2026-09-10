import subprocess
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
            "grading_components": [],
            "environment_variables": [],
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


# ── Clone endpoint ──────────────────────────────────────────────


@patch("app.routes.submissions.git_service")
def test_clone_repos_success(mock_git, client):
    mock_git.clone_repo.return_value = None
    mock_git.repo_exists.return_value = False

    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    _create_student(client, cid, "Alice", "A001", "alice")
    _create_student(client, cid, "Bob", "A002", "bob")

    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/clone")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["completed"] == 2
    assert data["failed"] == 0

    assert mock_git.clone_repo.call_count == 2


@patch("app.routes.submissions.git_service")
def test_clone_repos_missing_repo(mock_git, client):
    mock_git.clone_repo.side_effect = subprocess.CalledProcessError(128, "git clone")
    mock_git.repo_exists.return_value = False

    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    _create_student(client, cid, "Alice", "A001", "alice")

    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/clone")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["completed"] == 0
    assert data["failed"] == 1


@patch("app.routes.submissions.git_service")
def test_clone_repos_partial_failure(mock_git, client):
    call_count = 0

    def fake_clone(url, dest):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise subprocess.CalledProcessError(128, "git clone")

    mock_git.clone_repo.side_effect = fake_clone
    mock_git.repo_exists.return_value = False

    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    _create_student(client, cid, "Alice", "A001", "alice")
    _create_student(client, cid, "Bob", "A002", "bob")

    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/clone")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["completed"] == 1
    assert data["failed"] == 1


@patch("app.routes.submissions.git_service")
def test_clone_skips_already_cloned(mock_git, client):
    mock_git.clone_repo.return_value = None
    mock_git.repo_exists.return_value = False

    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    _create_student(client, cid, "Alice", "A001", "alice")

    client.post(f"/api/courses/{cid}/assignments/{aid}/clone")

    mock_git.repo_exists.return_value = True
    mock_git.clone_repo.reset_mock()

    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/clone")
    assert resp.status_code == 200
    assert resp.json()["completed"] == 1
    mock_git.clone_repo.assert_not_called()


def test_clone_no_students(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    resp = client.post(f"/api/courses/{cid}/assignments/{aid}/clone")
    assert resp.status_code == 400


def test_clone_course_not_found(client):
    resp = client.post("/api/courses/999/assignments/1/clone")
    assert resp.status_code == 404


def test_clone_assignment_not_found(client):
    cid = _create_course(client)
    resp = client.post(f"/api/courses/{cid}/assignments/999/clone")
    assert resp.status_code == 404


# ── Dashboard endpoint ──────────────────────────────────────────


@patch("app.routes.submissions.git_service")
def test_dashboard_returns_all_students(mock_git, client):
    mock_git.clone_repo.return_value = None
    mock_git.repo_exists.return_value = False

    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    _create_student(client, cid, "Alice", "A001", "alice")
    _create_student(client, cid, "Bob", "A002", "bob")

    client.post(f"/api/courses/{cid}/assignments/{aid}/clone")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard")
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 2
    names = {r["student_name"] for r in rows}
    assert names == {"Alice", "Bob"}


@patch("app.routes.submissions.git_service")
def test_dashboard_shows_missing_status(mock_git, client):
    mock_git.clone_repo.side_effect = subprocess.CalledProcessError(128, "git clone")
    mock_git.repo_exists.return_value = False

    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    _create_student(client, cid, "Alice", "A001", "alice")

    client.post(f"/api/courses/{cid}/assignments/{aid}/clone")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard")
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["clone_status"] == "missing"


def test_dashboard_before_clone_shows_pending(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    _create_student(client, cid, "Alice", "A001", "alice")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard")
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["clone_status"] == "pending"


@patch("app.routes.submissions.git_service")
def test_dashboard_filter_by_status(mock_git, client):
    call_count = 0

    def fake_clone(url, dest):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise subprocess.CalledProcessError(128, "git clone")

    mock_git.clone_repo.side_effect = fake_clone
    mock_git.repo_exists.return_value = False

    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    _create_student(client, cid, "Alice", "A001", "alice")
    _create_student(client, cid, "Bob", "A002", "bob")

    client.post(f"/api/courses/{cid}/assignments/{aid}/clone")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard?status=cloned")
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["clone_status"] == "cloned"


@patch("app.routes.submissions.git_service")
def test_dashboard_search_by_name(mock_git, client):
    mock_git.clone_repo.return_value = None
    mock_git.repo_exists.return_value = False

    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    _create_student(client, cid, "Alice", "A001", "alice")
    _create_student(client, cid, "Bob", "A002", "bob")

    client.post(f"/api/courses/{cid}/assignments/{aid}/clone")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/dashboard?search=ali")
    rows = resp.json()
    assert len(rows) == 1
    assert rows[0]["student_name"] == "Alice"


@patch("app.routes.submissions.git_service")
def test_dashboard_sort_desc(mock_git, client):
    mock_git.clone_repo.return_value = None
    mock_git.repo_exists.return_value = False

    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    _create_student(client, cid, "Alice", "A001", "alice")
    _create_student(client, cid, "Bob", "A002", "bob")

    client.post(f"/api/courses/{cid}/assignments/{aid}/clone")

    resp = client.get(
        f"/api/courses/{cid}/assignments/{aid}/dashboard?sort=student_name&order=desc"
    )
    rows = resp.json()
    assert rows[0]["student_name"] == "Bob"
    assert rows[1]["student_name"] == "Alice"


def test_dashboard_course_not_found(client):
    resp = client.get("/api/courses/999/assignments/1/dashboard")
    assert resp.status_code == 404


def test_dashboard_assignment_not_found(client):
    cid = _create_course(client)
    resp = client.get(f"/api/courses/{cid}/assignments/999/dashboard")
    assert resp.status_code == 404


# ── Progress endpoint ───────────────────────────────────────────


@patch("app.routes.submissions.git_service")
def test_clone_progress(mock_git, client):
    mock_git.clone_repo.return_value = None
    mock_git.repo_exists.return_value = False

    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    _create_student(client, cid, "Alice", "A001", "alice")
    _create_student(client, cid, "Bob", "A002", "bob")

    client.post(f"/api/courses/{cid}/assignments/{aid}/clone")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/clone/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    assert data["completed"] == 2
    assert data["failed"] == 0


def test_clone_progress_before_clone(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid)
    _create_student(client, cid, "Alice", "A001", "alice")

    resp = client.get(f"/api/courses/{cid}/assignments/{aid}/clone/progress")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["completed"] == 0
    assert data["failed"] == 0
