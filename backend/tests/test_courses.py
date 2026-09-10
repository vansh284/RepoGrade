def test_create_course(client):
    resp = client.post("/api/courses", json={"name": "CS201 Fall 2026"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "CS201 Fall 2026"
    assert "id" in data


def test_list_courses_empty(client):
    resp = client.get("/api/courses")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_courses(client):
    client.post("/api/courses", json={"name": "CS201"})
    client.post("/api/courses", json={"name": "CS301"})
    resp = client.get("/api/courses")
    assert len(resp.json()) == 2


def test_get_course(client):
    create = client.post("/api/courses", json={"name": "CS201"})
    course_id = create.json()["id"]
    resp = client.get(f"/api/courses/{course_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "CS201"


def test_get_course_not_found(client):
    resp = client.get("/api/courses/999")
    assert resp.status_code == 404


def test_update_course(client):
    create = client.post("/api/courses", json={"name": "CS201"})
    course_id = create.json()["id"]
    resp = client.put(f"/api/courses/{course_id}", json={"name": "CS201 Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "CS201 Updated"


def test_update_course_not_found(client):
    resp = client.put("/api/courses/999", json={"name": "Nope"})
    assert resp.status_code == 404


def test_delete_course(client):
    create = client.post("/api/courses", json={"name": "CS201"})
    course_id = create.json()["id"]
    resp = client.delete(f"/api/courses/{course_id}")
    assert resp.status_code == 204
    assert client.get(f"/api/courses/{course_id}").status_code == 404


def test_delete_course_not_found(client):
    resp = client.delete("/api/courses/999")
    assert resp.status_code == 404
