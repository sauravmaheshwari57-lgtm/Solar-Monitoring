from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.services import settings_service

router = APIRouter(prefix="/api/settings", tags=["Settings"], dependencies=[Depends(get_current_user)])


class SettingsUpdate(BaseModel):
    tariff_rate: float | None = None
    feed_in_rate: float | None = None
    battery_capacity_kwh: float | None = None


def _serialize(row):
    return {
        "tariff_rate": row.tariff_rate,
        "feed_in_rate": row.feed_in_rate,
        "battery_capacity_kwh": row.battery_capacity_kwh,
    }


@router.get("")
def read_settings(db: Session = Depends(get_db)):
    return _serialize(settings_service.get_settings(db))


@router.put("")
def write_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    row = settings_service.update_settings(db, **payload.model_dump())
    return _serialize(row)
