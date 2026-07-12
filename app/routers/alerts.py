from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Alert, User
from app.services import plant_service

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


@router.get("")
def list_alerts(
    unresolved_only: bool = Query(True),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    plant = plant_service.get_user_plant(db, user.username)
    q = db.query(Alert).filter(Alert.plant_id == plant.id).order_by(Alert.id.desc())
    if unresolved_only:
        q = q.filter(Alert.resolved == False)  # noqa: E712
    rows = q.limit(limit).all()
    return [
        {"id": a.id, "timestamp": a.timestamp.isoformat(), "level": a.level, "message": a.message, "resolved": a.resolved}
        for a in rows
    ]
