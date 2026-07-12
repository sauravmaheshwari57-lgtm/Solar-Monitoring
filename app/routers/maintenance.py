from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models import MaintenanceRecord, SolarPlant

router = APIRouter(prefix="/api/admin", tags=["Maintenance"], dependencies=[Depends(require_admin)])


class MaintenanceRequest(BaseModel):
    service_date: datetime
    next_service_date: datetime | None = None
    engineer_name: str | None = None
    notes: str | None = None


def _serialize(m: MaintenanceRecord) -> dict:
    return {
        "id": m.id,
        "plant_id": m.plant_id,
        "service_date": m.service_date.isoformat(),
        "next_service_date": m.next_service_date.isoformat() if m.next_service_date else None,
        "engineer_name": m.engineer_name,
        "notes": m.notes,
        "created_at": m.created_at.isoformat(),
    }


@router.get("/plants/{plant_id}/maintenance")
def list_maintenance(plant_id: int, db: Session = Depends(get_db)):
    rows = (
        db.query(MaintenanceRecord)
        .filter(MaintenanceRecord.plant_id == plant_id)
        .order_by(MaintenanceRecord.service_date.desc())
        .all()
    )
    return [_serialize(m) for m in rows]


@router.post("/plants/{plant_id}/maintenance")
def create_maintenance(plant_id: int, payload: MaintenanceRequest, db: Session = Depends(get_db)):
    if not db.query(SolarPlant).filter(SolarPlant.id == plant_id).first():
        raise HTTPException(status_code=404, detail="Plant not found")

    record = MaintenanceRecord(plant_id=plant_id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return _serialize(record)


@router.delete("/maintenance/{record_id}")
def delete_maintenance(record_id: int, db: Session = Depends(get_db)):
    record = db.query(MaintenanceRecord).filter(MaintenanceRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    db.delete(record)
    db.commit()
    return {"message": "Maintenance record deleted"}
