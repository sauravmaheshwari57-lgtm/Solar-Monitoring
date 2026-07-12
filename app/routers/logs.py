from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models import AuthEvent, ErrorLog, PageVisit

router = APIRouter(prefix="/api/admin/logs", tags=["Logs"], dependencies=[Depends(require_admin)])


@router.get("/login")
def login_history(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    rows = db.query(AuthEvent).order_by(AuthEvent.id.desc()).limit(limit).all()
    return [
        {"username": e.username, "event_type": e.event_type, "timestamp": e.timestamp.isoformat()}
        for e in rows
    ]


@router.get("/activity")
def user_activity(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    rows = db.query(PageVisit).order_by(PageVisit.id.desc()).limit(limit).all()
    return [{"path": v.path, "timestamp": v.timestamp.isoformat()} for v in rows]


@router.get("/errors")
def error_logs(limit: int = Query(50, ge=1, le=500), db: Session = Depends(get_db)):
    rows = db.query(ErrorLog).order_by(ErrorLog.id.desc()).limit(limit).all()
    return [
        {"path": e.path, "message": e.message, "timestamp": e.timestamp.isoformat()}
        for e in rows
    ]
