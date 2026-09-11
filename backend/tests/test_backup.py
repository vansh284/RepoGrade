import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture
def file_db(tmp_path):
    """Fixture that uses a file-based SQLite DB so backup/restore can copy it."""
    db_path = tmp_path / "test.db"
    url = f"sqlite:///{db_path}"
    eng = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestSess = sessionmaker(bind=eng)
    Base.metadata.create_all(bind=eng)

    def override_get_db():
        db = TestSess()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.routes.backup._get_db_path", return_value=db_path), \
         patch("app.routes.backup.engine", eng):
        yield TestClient(app), tmp_path, db_path

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=eng)


# ── Settings endpoints ──────────────────────────────────────────


def test_get_backup_path_not_configured(file_db):
    client, _, _ = file_db
    resp = client.get("/api/settings/backup-path")
    assert resp.status_code == 404


def test_set_and_get_backup_path(file_db):
    client, tmp_path, _ = file_db
    backup_dir = str(tmp_path / "backups")
    resp = client.put("/api/settings/backup-path", json={"path": backup_dir})
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "backup_directory"
    assert Path(data["value"]).is_dir()

    resp = client.get("/api/settings/backup-path")
    assert resp.status_code == 200
    assert resp.json()["key"] == "backup_directory"


def test_set_backup_path_creates_directory(file_db):
    client, tmp_path, _ = file_db
    nested = str(tmp_path / "a" / "b" / "c")
    resp = client.put("/api/settings/backup-path", json={"path": nested})
    assert resp.status_code == 200
    assert Path(nested).is_dir()


# ── Backup ──────────────────────────────────────────────────────


def test_backup_no_path_configured(file_db):
    client, _, _ = file_db
    resp = client.post("/api/backup")
    assert resp.status_code == 400
    assert "not configured" in resp.json()["detail"]


def test_backup_creates_file(file_db):
    client, tmp_path, _ = file_db
    backup_dir = str(tmp_path / "backups")
    client.put("/api/settings/backup-path", json={"path": backup_dir})

    resp = client.post("/api/backup")
    assert resp.status_code == 200
    data = resp.json()
    assert data["filename"].startswith("repograde_backup_")
    assert data["filename"].endswith(".db")
    assert Path(data["path"]).is_file()


# ── List backups ────────────────────────────────────────────────


def test_list_backups_empty(file_db):
    client, tmp_path, _ = file_db
    resp = client.get("/api/backups")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_backups(file_db):
    client, tmp_path, _ = file_db
    backup_dir = str(tmp_path / "backups")
    client.put("/api/settings/backup-path", json={"path": backup_dir})
    client.post("/api/backup")
    client.post("/api/backup")

    resp = client.get("/api/backups")
    assert resp.status_code == 200
    backups = resp.json()
    assert len(backups) >= 1
    assert "filename" in backups[0]
    assert "created_at" in backups[0]
    assert "size_bytes" in backups[0]


# ── Restore ─────────────────────────────────────────────────────


def test_restore_no_filename(file_db):
    client, tmp_path, _ = file_db
    backup_dir = str(tmp_path / "backups")
    client.put("/api/settings/backup-path", json={"path": backup_dir})
    resp = client.post("/api/restore", json={})
    assert resp.status_code == 400


def test_restore_file_not_found(file_db):
    client, tmp_path, _ = file_db
    backup_dir = str(tmp_path / "backups")
    client.put("/api/settings/backup-path", json={"path": backup_dir})
    resp = client.post("/api/restore", json={"filename": "nonexistent.db"})
    assert resp.status_code == 404


def test_restore_success(file_db):
    client, tmp_path, _ = file_db
    backup_dir = str(tmp_path / "backups")
    client.put("/api/settings/backup-path", json={"path": backup_dir})

    # Create a backup first
    backup_resp = client.post("/api/backup")
    filename = backup_resp.json()["filename"]

    resp = client.post("/api/restore", json={"filename": filename})
    assert resp.status_code == 200
    assert "restored" in resp.json()["message"].lower()
