from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.services import billing_service, plant_service

router = APIRouter(prefix="/api/billing", tags=["Billing"])


@router.get("/estimate")
def estimate(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plant = plant_service.get_user_plant(db, user.username)
    return billing_service.monthly_estimate(db, plant_id=plant.id)
