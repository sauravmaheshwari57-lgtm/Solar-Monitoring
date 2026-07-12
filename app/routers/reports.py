from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.services import reports_service

router = APIRouter(prefix="/api/admin", tags=["Reports"], dependencies=[Depends(require_admin)])


@router.get("/reports")
def report(
    period: str = Query("weekly", pattern="^(daily|weekly|monthly|yearly)$"),
    db: Session = Depends(get_db),
):
    return reports_service.energy_report(db, period)
