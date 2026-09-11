import os
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import DATABASE_URL, engine, get_db
from app.models import AppSetting
from app.schemas import AppSettingOut, BackupInfo, BackupResult, RestoreResult

router = APIRouter(tags=["backup"])

BACKUP_DIR_KEY = "backup_directory"


def _get_db_path() -> Path:
    """Extract the file path from the SQLite DATABASE_URL."""
    # DATABASE_URL is like "sqlite:///./repograde.db"
    prefix = "sqlite:///"
    if not DATABASE_URL.startswith(prefix):
        raise RuntimeError("Only SQLite databases are supported for backup")
    return Path(DATABASE_URL[len(prefix):]).resolve()


class BackupPathBody(BaseModel):
    path: str


# ── Settings ────────────────────────────────────────────────────


@router.get("/api/settings/backup-path", response_model=AppSettingOut)
def get_backup_path(db: Session = Depends(get_db)):
    setting = db.query(AppSetting).filter(AppSetting.key == BACKUP_DIR_KEY).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Backup path not configured")
    return setting


@router.put("/api/settings/backup-path", response_model=AppSettingOut)
def set_backup_path(body: BackupPathBody, db: Session = Depends(get_db)):
    backup_dir = Path(body.path).resolve()
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Cannot create directory: {exc}")

    setting = db.query(AppSetting).filter(AppSetting.key == BACKUP_DIR_KEY).first()
    if setting:
        setting.value = str(backup_dir)
    else:
        setting = AppSetting(key=BACKUP_DIR_KEY, value=str(backup_dir))
        db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


# ── Backup ──────────────────────────────────────────────────────


@router.post("/api/backup", response_model=BackupResult)
def create_backup(db: Session = Depends(get_db)):
    setting = db.query(AppSetting).filter(AppSetting.key == BACKUP_DIR_KEY).first()
    if not setting:
        raise HTTPException(status_code=400, detail="Backup path not configured")

    backup_dir = Path(setting.value)
    if not backup_dir.is_dir():
        raise HTTPException(status_code=400, detail="Backup directory does not exist")

    db_path = _get_db_path()
    if not db_path.is_file():
        raise HTTPException(status_code=500, detail="Database file not found")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    filename = f"repograde_backup_{timestamp}.db"
    dest = backup_dir / filename

    shutil.copy2(str(db_path), str(dest))

    return BackupResult(filename=filename, path=str(dest))


@router.get("/api/backups", response_model=list[BackupInfo])
def list_backups(db: Session = Depends(get_db)):
    setting = db.query(AppSetting).filter(AppSetting.key == BACKUP_DIR_KEY).first()
    if not setting:
        return []

    backup_dir = Path(setting.value)
    if not backup_dir.is_dir():
        return []

    backups = []
    for f in backup_dir.glob("repograde_backup_*.db"):
        stat = f.stat()
        backups.append(
            BackupInfo(
                filename=f.name,
                created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                size_bytes=stat.st_size,
            )
        )
    backups.sort(key=lambda b: b.created_at, reverse=True)
    return backups


# ── Restore ─────────────────────────────────────────────────────


@router.post("/api/restore", response_model=RestoreResult)
def restore_backup(body: dict, db: Session = Depends(get_db)):
    filename = body.get("filename")
    if not filename:
        raise HTTPException(status_code=400, detail="filename is required")

    setting = db.query(AppSetting).filter(AppSetting.key == BACKUP_DIR_KEY).first()
    if not setting:
        raise HTTPException(status_code=400, detail="Backup path not configured")

    backup_file = Path(setting.value) / filename
    if not backup_file.is_file():
        raise HTTPException(status_code=404, detail="Backup file not found")

    db_path = _get_db_path()

    # Close all pooled connections before overwriting the DB file
    db.close()
    engine.dispose()

    shutil.copy2(str(backup_file), str(db_path))

    return RestoreResult(message=f"Database restored from {filename}. Please restart the application.")
