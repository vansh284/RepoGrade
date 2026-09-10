import csv
import io


def _create_course(client):
    resp = client.post("/api/courses", json={"name": "CS201"})
    return resp.json()["id"]


# ── CRUD ──────────────────────────────────────────────────────────


def test_create_student(client):
    cid = _create_course(client)
    resp = client.post(
        f"/api/courses/{cid}/students",
        json={
            "name": "Alice",
            "student_id": "A001",
            "email": "alice@example.com",
            "github_username": "alice",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Alice"
    assert data["student_id"] == "A001"
    assert data["email"] == "alice@example.com"
    assert data["github_username"] == "alice"
    assert "id" in data


def test_create_student_course_not_found(client):
    resp = client.post(
        "/api/courses/999/students",
        json={
            "name": "Alice",
            "student_id": "A001",
            "email": "alice@example.com",
            "github_username": "alice",
        },
    )
    assert resp.status_code == 404


def test_create_student_duplicate_student_id(client):
    cid = _create_course(client)
    payload = {
        "name": "Alice",
        "student_id": "A001",
        "email": "alice@example.com",
        "github_username": "alice",
    }
    client.post(f"/api/courses/{cid}/students", json=payload)
    resp = client.post(f"/api/courses/{cid}/students", json=payload)
    assert resp.status_code == 409


def test_list_students_empty(client):
    cid = _create_course(client)
    resp = client.get(f"/api/courses/{cid}/students")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_students(client):
    cid = _create_course(client)
    client.post(
        f"/api/courses/{cid}/students",
        json={"name": "Alice", "student_id": "A001", "email": "a@e.com", "github_username": "alice"},
    )
    client.post(
        f"/api/courses/{cid}/students",
        json={"name": "Bob", "student_id": "A002", "email": "b@e.com", "github_username": "bob"},
    )
    resp = client.get(f"/api/courses/{cid}/students")
    assert len(resp.json()) == 2


def test_get_student(client):
    cid = _create_course(client)
    create = client.post(
        f"/api/courses/{cid}/students",
        json={"name": "Alice", "student_id": "A001", "email": "a@e.com", "github_username": "alice"},
    )
    sid = create.json()["id"]
    resp = client.get(f"/api/courses/{cid}/students/{sid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Alice"


def test_get_student_not_found(client):
    cid = _create_course(client)
    resp = client.get(f"/api/courses/{cid}/students/999")
    assert resp.status_code == 404


def test_update_student(client):
    cid = _create_course(client)
    create = client.post(
        f"/api/courses/{cid}/students",
        json={"name": "Alice", "student_id": "A001", "email": "a@e.com", "github_username": "alice"},
    )
    sid = create.json()["id"]
    resp = client.put(
        f"/api/courses/{cid}/students/{sid}",
        json={"name": "Alice Updated", "student_id": "A001", "email": "a2@e.com", "github_username": "alice2"},
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Alice Updated"
    assert resp.json()["email"] == "a2@e.com"


def test_update_student_not_found(client):
    cid = _create_course(client)
    resp = client.put(
        f"/api/courses/{cid}/students/999",
        json={"name": "X", "student_id": "X", "email": "x@e.com", "github_username": "x"},
    )
    assert resp.status_code == 404


def test_delete_student(client):
    cid = _create_course(client)
    create = client.post(
        f"/api/courses/{cid}/students",
        json={"name": "Alice", "student_id": "A001", "email": "a@e.com", "github_username": "alice"},
    )
    sid = create.json()["id"]
    resp = client.delete(f"/api/courses/{cid}/students/{sid}")
    assert resp.status_code == 204
    assert client.get(f"/api/courses/{cid}/students/{sid}").status_code == 404


def test_delete_student_not_found(client):
    cid = _create_course(client)
    resp = client.delete(f"/api/courses/{cid}/students/999")
    assert resp.status_code == 404


# ── CSV Import ────────────────────────────────────────────────────


def _csv_file(rows: list[dict]) -> dict:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
    buf.seek(0)
    return {"file": ("roster.csv", buf.getvalue(), "text/csv")}


def test_import_csv_success(client):
    cid = _create_course(client)
    files = _csv_file([
        {"name": "Alice", "student_id": "A001", "email": "a@e.com", "github_username": "alice"},
        {"name": "Bob", "student_id": "A002", "email": "b@e.com", "github_username": "bob"},
    ])
    resp = client.post(f"/api/courses/{cid}/students/import", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 2
    assert data["errors"] == []
    assert len(client.get(f"/api/courses/{cid}/students").json()) == 2


def test_import_csv_reordered_columns(client):
    cid = _create_course(client)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["email", "github_username", "student_id", "name"])
    writer.writeheader()
    writer.writerow({"email": "a@e.com", "github_username": "alice", "student_id": "A001", "name": "Alice"})
    buf.seek(0)
    resp = client.post(
        f"/api/courses/{cid}/students/import",
        files={"file": ("roster.csv", buf.getvalue(), "text/csv")},
    )
    assert resp.status_code == 200
    assert resp.json()["imported"] == 1


def test_import_csv_missing_required_column(client):
    cid = _create_course(client)
    buf = io.StringIO("name,student_id\nAlice,A001\n")
    resp = client.post(
        f"/api/courses/{cid}/students/import",
        files={"file": ("roster.csv", buf.getvalue(), "text/csv")},
    )
    assert resp.status_code == 400


def test_import_csv_row_level_errors(client):
    cid = _create_course(client)
    client.post(
        f"/api/courses/{cid}/students",
        json={"name": "Alice", "student_id": "A001", "email": "a@e.com", "github_username": "alice"},
    )
    files = _csv_file([
        {"name": "Alice Dup", "student_id": "A001", "email": "a2@e.com", "github_username": "alice2"},
        {"name": "Bob", "student_id": "A002", "email": "b@e.com", "github_username": "bob"},
    ])
    resp = client.post(f"/api/courses/{cid}/students/import", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert data["imported"] == 1
    assert len(data["errors"]) == 1
    assert data["errors"][0]["row"] == 2
    students = client.get(f"/api/courses/{cid}/students").json()
    assert len(students) == 2
    assert {s["student_id"] for s in students} == {"A001", "A002"}


def test_import_csv_course_not_found(client):
    files = _csv_file([
        {"name": "Alice", "student_id": "A001", "email": "a@e.com", "github_username": "alice"},
    ])
    resp = client.post("/api/courses/999/students/import", files=files)
    assert resp.status_code == 404


# ── CSV Export ────────────────────────────────────────────────────


def test_export_csv(client):
    cid = _create_course(client)
    client.post(
        f"/api/courses/{cid}/students",
        json={"name": "Alice", "student_id": "A001", "email": "a@e.com", "github_username": "alice"},
    )
    client.post(
        f"/api/courses/{cid}/students",
        json={"name": "Bob", "student_id": "A002", "email": "b@e.com", "github_username": "bob"},
    )
    resp = client.get(f"/api/courses/{cid}/students/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    reader = csv.DictReader(io.StringIO(resp.text))
    rows = list(reader)
    assert len(rows) == 2
    assert set(reader.fieldnames) == {"name", "student_id", "email", "github_username"}


def test_export_csv_empty(client):
    cid = _create_course(client)
    resp = client.get(f"/api/courses/{cid}/students/export")
    assert resp.status_code == 200
    reader = csv.DictReader(io.StringIO(resp.text))
    assert list(reader) == []
