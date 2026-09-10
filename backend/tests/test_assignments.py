def _create_course(client):
    resp = client.post("/api/courses", json={"name": "CS201"})
    return resp.json()["id"]


def _create_assignment(client, course_id, **overrides):
    payload = {
        "name": "HW1",
        "github_repo_name": "cs201-hw1",
        "checks_directory": "/checks/hw1",
        "evaluator_weight": 0.7,
        "peer_weight": 0.3,
        "grading_components": [],
        "environment_variables": [],
        **overrides,
    }
    return client.post(f"/api/courses/{course_id}/assignments", json=payload)


# ── Assignment CRUD ──────────────────────────────────────────────


def test_create_assignment(client):
    cid = _create_course(client)
    resp = _create_assignment(client, cid)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "HW1"
    assert data["github_repo_name"] == "cs201-hw1"
    assert data["checks_directory"] == "/checks/hw1"
    assert data["evaluator_weight"] == 0.7
    assert data["peer_weight"] == 0.3
    assert "id" in data


def test_create_assignment_with_components_and_env_vars(client):
    cid = _create_course(client)
    resp = _create_assignment(
        client,
        cid,
        grading_components=[
            {"name": "Correctness", "max_points": 100, "weight": 0.6},
            {"name": "Style", "max_points": 50, "weight": 0.4},
        ],
        environment_variables=[
            {"key": "DEADLINE", "value": "2026-10-01"},
        ],
    )
    assert resp.status_code == 201
    data = resp.json()
    assert len(data["grading_components"]) == 2
    assert data["grading_components"][0]["name"] == "Correctness"
    assert data["grading_components"][0]["max_points"] == 100
    assert data["grading_components"][0]["weight"] == 0.6
    assert len(data["environment_variables"]) == 1
    assert data["environment_variables"][0]["key"] == "DEADLINE"
    assert data["environment_variables"][0]["value"] == "2026-10-01"


def test_create_assignment_course_not_found(client):
    resp = _create_assignment(client, 999)
    assert resp.status_code == 404


def test_list_assignments_empty(client):
    cid = _create_course(client)
    resp = client.get(f"/api/courses/{cid}/assignments")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_assignments(client):
    cid = _create_course(client)
    _create_assignment(client, cid, name="HW1")
    _create_assignment(client, cid, name="HW2")
    resp = client.get(f"/api/courses/{cid}/assignments")
    assert len(resp.json()) == 2


def test_get_assignment(client):
    cid = _create_course(client)
    create = _create_assignment(client, cid)
    aid = create.json()["id"]
    resp = client.get(f"/api/courses/{cid}/assignments/{aid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "HW1"
    assert "grading_components" in resp.json()
    assert "environment_variables" in resp.json()


def test_get_assignment_not_found(client):
    cid = _create_course(client)
    resp = client.get(f"/api/courses/{cid}/assignments/999")
    assert resp.status_code == 404


def test_update_assignment(client):
    cid = _create_course(client)
    create = _create_assignment(client, cid)
    aid = create.json()["id"]
    resp = client.put(
        f"/api/courses/{cid}/assignments/{aid}",
        json={
            "name": "HW1 Updated",
            "github_repo_name": "cs201-hw1-v2",
            "checks_directory": "/checks/hw1-v2",
            "evaluator_weight": 0.6,
            "peer_weight": 0.4,
            "grading_components": [
                {"name": "Correctness", "max_points": 100, "weight": 1.0},
            ],
            "environment_variables": [
                {"key": "DEADLINE", "value": "2026-11-01"},
            ],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "HW1 Updated"
    assert data["github_repo_name"] == "cs201-hw1-v2"
    assert len(data["grading_components"]) == 1
    assert data["grading_components"][0]["name"] == "Correctness"
    assert len(data["environment_variables"]) == 1
    assert data["environment_variables"][0]["key"] == "DEADLINE"


def test_update_assignment_not_found(client):
    cid = _create_course(client)
    resp = client.put(
        f"/api/courses/{cid}/assignments/999",
        json={
            "name": "X",
            "github_repo_name": "x",
            "checks_directory": "/x",
            "evaluator_weight": 0.5,
            "peer_weight": 0.5,
            "grading_components": [],
            "environment_variables": [],
        },
    )
    assert resp.status_code == 404


def test_delete_assignment(client):
    cid = _create_course(client)
    create = _create_assignment(client, cid)
    aid = create.json()["id"]
    resp = client.delete(f"/api/courses/{cid}/assignments/{aid}")
    assert resp.status_code == 204
    assert client.get(f"/api/courses/{cid}/assignments/{aid}").status_code == 404


def test_delete_assignment_not_found(client):
    cid = _create_course(client)
    resp = client.delete(f"/api/courses/{cid}/assignments/999")
    assert resp.status_code == 404


def test_delete_assignment_cascades_components_and_env_vars(client):
    cid = _create_course(client)
    create = _create_assignment(
        client,
        cid,
        grading_components=[{"name": "Correctness", "max_points": 100, "weight": 1.0}],
        environment_variables=[{"key": "K", "value": "V"}],
    )
    aid = create.json()["id"]
    client.delete(f"/api/courses/{cid}/assignments/{aid}")
    assert client.get(f"/api/courses/{cid}/assignments/{aid}").status_code == 404


# ── Grading Component CRUD ───────────────────────────────────────


def test_add_grading_component(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid).json()["id"]
    resp = client.post(
        f"/api/assignments/{aid}/grading-components",
        json={"name": "Correctness", "max_points": 100, "weight": 0.8},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Correctness"
    assert data["max_points"] == 100
    assert data["weight"] == 0.8
    assert "id" in data


def test_add_grading_component_assignment_not_found(client):
    resp = client.post(
        "/api/assignments/999/grading-components",
        json={"name": "X", "max_points": 10, "weight": 1.0},
    )
    assert resp.status_code == 404


def test_list_grading_components(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid).json()["id"]
    client.post(f"/api/assignments/{aid}/grading-components", json={"name": "A", "max_points": 50, "weight": 0.5})
    client.post(f"/api/assignments/{aid}/grading-components", json={"name": "B", "max_points": 50, "weight": 0.5})
    resp = client.get(f"/api/assignments/{aid}/grading-components")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_grading_component(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid).json()["id"]
    gc = client.post(
        f"/api/assignments/{aid}/grading-components",
        json={"name": "A", "max_points": 50, "weight": 0.5},
    ).json()
    resp = client.put(
        f"/api/assignments/{aid}/grading-components/{gc['id']}",
        json={"name": "A Updated", "max_points": 100, "weight": 1.0},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "A Updated"
    assert resp.json()["max_points"] == 100


def test_update_grading_component_not_found(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid).json()["id"]
    resp = client.put(
        f"/api/assignments/{aid}/grading-components/999",
        json={"name": "X", "max_points": 10, "weight": 1.0},
    )
    assert resp.status_code == 404


def test_delete_grading_component(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid).json()["id"]
    gc = client.post(
        f"/api/assignments/{aid}/grading-components",
        json={"name": "A", "max_points": 50, "weight": 0.5},
    ).json()
    resp = client.delete(f"/api/assignments/{aid}/grading-components/{gc['id']}")
    assert resp.status_code == 204
    assert len(client.get(f"/api/assignments/{aid}/grading-components").json()) == 0


def test_delete_grading_component_not_found(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid).json()["id"]
    resp = client.delete(f"/api/assignments/{aid}/grading-components/999")
    assert resp.status_code == 404


# ── Environment Variable CRUD ────────────────────────────────────


def test_add_environment_variable(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid).json()["id"]
    resp = client.post(
        f"/api/assignments/{aid}/env-vars",
        json={"key": "DEADLINE", "value": "2026-10-01"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["key"] == "DEADLINE"
    assert data["value"] == "2026-10-01"
    assert "id" in data


def test_add_env_var_assignment_not_found(client):
    resp = client.post(
        "/api/assignments/999/env-vars",
        json={"key": "K", "value": "V"},
    )
    assert resp.status_code == 404


def test_list_environment_variables(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid).json()["id"]
    client.post(f"/api/assignments/{aid}/env-vars", json={"key": "A", "value": "1"})
    client.post(f"/api/assignments/{aid}/env-vars", json={"key": "B", "value": "2"})
    resp = client.get(f"/api/assignments/{aid}/env-vars")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_update_environment_variable(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid).json()["id"]
    ev = client.post(
        f"/api/assignments/{aid}/env-vars",
        json={"key": "DEADLINE", "value": "2026-10-01"},
    ).json()
    resp = client.put(
        f"/api/assignments/{aid}/env-vars/{ev['id']}",
        json={"key": "DEADLINE", "value": "2026-11-01"},
    )
    assert resp.status_code == 200
    assert resp.json()["value"] == "2026-11-01"


def test_update_env_var_not_found(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid).json()["id"]
    resp = client.put(
        f"/api/assignments/{aid}/env-vars/999",
        json={"key": "K", "value": "V"},
    )
    assert resp.status_code == 404


def test_delete_environment_variable(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid).json()["id"]
    ev = client.post(
        f"/api/assignments/{aid}/env-vars",
        json={"key": "DEADLINE", "value": "2026-10-01"},
    ).json()
    resp = client.delete(f"/api/assignments/{aid}/env-vars/{ev['id']}")
    assert resp.status_code == 204
    assert len(client.get(f"/api/assignments/{aid}/env-vars").json()) == 0


def test_delete_env_var_not_found(client):
    cid = _create_course(client)
    aid = _create_assignment(client, cid).json()["id"]
    resp = client.delete(f"/api/assignments/{aid}/env-vars/999")
    assert resp.status_code == 404


# ── Update replaces nested collections ───────────────────────────


def test_update_assignment_replaces_grading_components(client):
    cid = _create_course(client)
    create = _create_assignment(
        client,
        cid,
        grading_components=[
            {"name": "A", "max_points": 50, "weight": 0.5},
            {"name": "B", "max_points": 50, "weight": 0.5},
        ],
    )
    aid = create.json()["id"]
    resp = client.put(
        f"/api/courses/{cid}/assignments/{aid}",
        json={
            "name": "HW1",
            "github_repo_name": "cs201-hw1",
            "checks_directory": "/checks/hw1",
            "evaluator_weight": 0.7,
            "peer_weight": 0.3,
            "grading_components": [
                {"name": "C", "max_points": 100, "weight": 1.0},
            ],
            "environment_variables": [],
        },
    )
    assert resp.status_code == 200
    assert len(resp.json()["grading_components"]) == 1
    assert resp.json()["grading_components"][0]["name"] == "C"


def test_update_assignment_replaces_env_vars(client):
    cid = _create_course(client)
    create = _create_assignment(
        client,
        cid,
        environment_variables=[
            {"key": "A", "value": "1"},
            {"key": "B", "value": "2"},
        ],
    )
    aid = create.json()["id"]
    resp = client.put(
        f"/api/courses/{cid}/assignments/{aid}",
        json={
            "name": "HW1",
            "github_repo_name": "cs201-hw1",
            "checks_directory": "/checks/hw1",
            "evaluator_weight": 0.7,
            "peer_weight": 0.3,
            "grading_components": [],
            "environment_variables": [{"key": "C", "value": "3"}],
        },
    )
    assert resp.status_code == 200
    assert len(resp.json()["environment_variables"]) == 1
    assert resp.json()["environment_variables"][0]["key"] == "C"


def test_delete_course_cascades_assignments(client):
    cid = _create_course(client)
    _create_assignment(client, cid)
    client.delete(f"/api/courses/{cid}")
    resp = client.get(f"/api/courses/{cid}/assignments")
    assert resp.status_code == 404
