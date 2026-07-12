from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.services import energy_service, plant_service

router = APIRouter(prefix="/api/energy", tags=["Energy"])


@router.get("/today")
def today(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plant = plant_service.get_user_plant(db, user.username)
    return energy_service.today_summary(db, plant_id=plant.id)


@router.get("/history")
def history(days: int = Query(7, ge=1, le=90), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plant = plant_service.get_user_plant(db, user.username)
    return energy_service.history(db, days, plant_id=plant.id)


@router.get("/recent")
def recent(limit: int = Query(60, ge=1, le=500), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plant = plant_service.get_user_plant(db, user.username)
    return energy_service.recent_series(db, limit, plant_id=plant.id)
