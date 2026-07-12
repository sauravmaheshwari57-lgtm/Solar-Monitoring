from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.database import get_db
from app.models import Device, SolarPlant

router = APIRouter(prefix="/api/admin", tags=["Plants & Devices"], dependencies=[Depends(require_admin)])

_OFFLINE_AFTER_MINUTES = 5


class PlantRequest(BaseModel):
    name: str
    plant_code: str
    capacity_kw: float
    location: str | None = None
    owner_username: str | None = None
    status: str = "active"


class DeviceRequest(BaseModel):
    device_type: str
    device_code: str
    status: str = "online"


def _serialize_plant(p: SolarPlant) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "plant_code": p.plant_code,
        "capacity_kw": p.capacity_kw,
        "location": p.location,
        "owner_username": p.owner_username,
        "status": p.status,
        "installed_on": p.installed_on.isoformat() if p.installed_on else None,
        "created_at": p.created_at.isoformat(),
    }


def _serialize_device(d: Device) -> dict:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=_OFFLINE_AFTER_MINUTES)
    last_seen = d.last_seen.replace(tzinfo=timezone.utc) if d.last_seen and d.last_seen.tzinfo is None else d.last_seen
    live_status = "online" if last_seen and last_seen >= cutoff else "offline"
    return {
        "id": d.id,
        "plant_id": d.plant_id,
        "device_type": d.device_type,
        "device_code": d.device_code,
        "status": live_status,
        "last_seen": d.last_seen.isoformat() if d.last_seen else None,
    }


@router.get("/plants")
def list_plants(db: Session = Depends(get_db)):
    return [_serialize_plant(p) for p in db.query(SolarPlant).order_by(SolarPlant.id).all()]


@router.post("/plants")
def create_plant(payload: PlantRequest, db: Session = Depends(get_db)):
    if db.query(SolarPlant).filter(SolarPlant.plant_code == payload.plant_code).first():
        raise HTTPException(status_code=400, detail="Plant code already exists")

    plant = SolarPlant(**payload.model_dump())
    db.add(plant)
    db.commit()
    db.refresh(plant)
    return _serialize_plant(plant)


@router.put("/plants/{plant_id}")
def update_plant(plant_id: int, payload: PlantRequest, db: Session = Depends(get_db)):
    plant = db.query(SolarPlant).filter(SolarPlant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")

    for key, value in payload.model_dump().items():
        setattr(plant, key, value)
    db.commit()
    db.refresh(plant)
    return _serialize_plant(plant)


@router.delete("/plants/{plant_id}")
def delete_plant(plant_id: int, db: Session = Depends(get_db)):
    plant = db.query(SolarPlant).filter(SolarPlant.id == plant_id).first()
    if not plant:
        raise HTTPException(status_code=404, detail="Plant not found")
    if plant.plant_code == "DEFAULT":
        raise HTTPException(status_code=400, detail="The default plant cannot be deleted")

    db.delete(plant)
    db.commit()
    return {"message": "Plant deleted"}


@router.get("/plants/{plant_id}/devices")
def list_devices(plant_id: int, db: Session = Depends(get_db)):
    rows = db.query(Device).filter(Device.plant_id == plant_id).order_by(Device.id).all()
    return [_serialize_device(d) for d in rows]


@router.post("/plants/{plant_id}/devices")
def create_device(plant_id: int, payload: DeviceRequest, db: Session = Depends(get_db)):
    if not db.query(SolarPlant).filter(SolarPlant.id == plant_id).first():
        raise HTTPException(status_code=404, detail="Plant not found")

    device = Device(plant_id=plant_id, **payload.model_dump())
    db.add(device)
    db.commit()
    db.refresh(device)
    return _serialize_device(device)


@router.delete("/devices/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = db.query(Device).filter(Device.id == device_id).first()
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")

    db.delete(device)
    db.commit()
    return {"message": "Device deleted"}
