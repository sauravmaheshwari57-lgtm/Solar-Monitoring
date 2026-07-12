from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import settings_service

router = APIRouter(prefix="/api/public", tags=["Public"])


@router.get("/info")
def public_info(db: Session = Depends(get_db)):
    s = settings_service.get_settings(db)
    return {
        "company_name": s.company_name,
        "tariff_rate": s.tariff_rate,
        "feed_in_rate": s.feed_in_rate,
        "battery_capacity_kwh": s.battery_capacity_kwh,
    }
