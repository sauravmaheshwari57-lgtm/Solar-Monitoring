import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.auth import require_admin
from app.config import settings

router = APIRouter(prefix="/api/admin/backup", tags=["Backup"], dependencies=[Depends(require_admin)])

_PG_BIN = Path(r"C:\Program Files\PostgreSQL\16\bin")


def _db_parts():
    parsed = urlparse(settings.DATABASE_URL)
    return {
        "user": parsed.username,
        "password": unquote(parsed.password or ""),
        "host": parsed.hostname,
        "port": str(parsed.port or 5432),
        "dbname": parsed.path.lstrip("/"),
    }


@router.get("")
def create_backup():
    db = _db_parts()
    out_path = Path(tempfile.gettempdir()) / f"{db['dbname']}_backup.sql"

    result = subprocess.run(
        [
            str(_PG_BIN / "pg_dump.exe"),
            "-U", db["user"],
            "-h", db["host"],
            "-p", db["port"],
            "-d", db["dbname"],
            "--clean", "--if-exists",
            "-f", str(out_path),
        ],
        env={**os.environ, "PGPASSWORD": db["password"]},
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Backup failed: {result.stderr[:500]}")

    return FileResponse(out_path, filename=f"{db['dbname']}_backup.sql", media_type="application/sql")


@router.post("/restore")
async def restore_backup(file: UploadFile):
    if not file.filename.endswith(".sql"):
        raise HTTPException(status_code=400, detail="Please upload a .sql backup file")

    db = _db_parts()
    tmp_path = Path(tempfile.gettempdir()) / f"restore_{file.filename}"
    tmp_path.write_bytes(await file.read())

    result = subprocess.run(
        [
            str(_PG_BIN / "psql.exe"),
            "-U", db["user"],
            "-h", db["host"],
            "-p", db["port"],
            "-d", db["dbname"],
            "-f", str(tmp_path),
        ],
        env={**os.environ, "PGPASSWORD": db["password"]},
        capture_output=True,
        text=True,
    )
    tmp_path.unlink(missing_ok=True)

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Restore failed: {result.stderr[:500]}")

    return {"message": "Database restored successfully"}
