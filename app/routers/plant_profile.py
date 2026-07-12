from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import PlantProfile, SolarPlant, User

router = APIRouter(prefix="/api/plant-profile", tags=["Plant Profile"], dependencies=[Depends(get_current_user)])


class PlantProfileUpdate(BaseModel):
    meter_number: str | None = None
    meter_serial_number: str | None = None
    consumer_number: str | None = None
    customer_name: str | None = None
    mobile_number: str | None = None
    email: str | None = None
    address: str | None = None

    plant_name: str | None = None
    plant_capacity_kw: float | None = None
    panel_count: int | None = None
    inverter_name: str | None = None
    inverter_serial_number: str | None = None
    inverter_capacity: str | None = None
    installation_date: datetime | None = None

    meter_manufacturer: str | None = None
    meter_model: str | None = None
    phase: str | None = None
    voltage: str | None = None
    current_rating: str | None = None
    ct_pt_ratio: str | None = None

    state: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    connectivity_type: str | None = None
    data_logger_id: str | None = None
    gateway_id: str | None = None
    modbus_address: str | None = None
    modbus_slave_id: str | None = None


def _serialize(p: PlantProfile) -> dict:
    return {
        "meter_number": p.meter_number,
        "meter_serial_number": p.meter_serial_number,
        "consumer_number": p.consumer_number,
        "customer_name": p.customer_name,
        "mobile_number": p.mobile_number,
        "email": p.email,
        "address": p.address,
        "plant_name": p.plant_name,
        "plant_capacity_kw": p.plant_capacity_kw,
        "panel_count": p.panel_count,
        "inverter_name": p.inverter_name,
        "inverter_serial_number": p.inverter_serial_number,
        "inverter_capacity": p.inverter_capacity,
        "installation_date": p.installation_date.isoformat() if p.installation_date else None,
        "meter_manufacturer": p.meter_manufacturer,
        "meter_model": p.meter_model,
        "phase": p.phase,
        "voltage": p.voltage,
        "current_rating": p.current_rating,
        "ct_pt_ratio": p.ct_pt_ratio,
        "state": p.state,
        "city": p.city,
        "latitude": p.latitude,
        "longitude": p.longitude,
        "connectivity_type": p.connectivity_type,
        "data_logger_id": p.data_logger_id,
        "gateway_id": p.gateway_id,
        "modbus_address": p.modbus_address,
        "modbus_slave_id": p.modbus_slave_id,
    }


def _get_or_create(db: Session, user_id: int) -> PlantProfile:
    profile = db.query(PlantProfile).filter(PlantProfile.user_id == user_id).first()
    if profile:
        return profile
    profile = PlantProfile(user_id=user_id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("")
def read_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _serialize(_get_or_create(db, user.id))


def _ensure_plant_started(db: Session, user: User, profile: PlantProfile) -> None:
    """Once a customer has entered a plant name and capacity, spin up their own
    SolarPlant record so live monitoring starts generating readings for them."""
    if not profile.plant_name or not profile.plant_capacity_kw:
        return

    existing = db.query(SolarPlant).filter(SolarPlant.owner_username == user.username).first()
    if existing:
        existing.name = profile.plant_name
        existing.capacity_kw = profile.plant_capacity_kw
        existing.location = ", ".join(filter(None, [profile.city, profile.state])) or existing.location
        db.commit()
        return

    plant = SolarPlant(
        name=profile.plant_name,
        plant_code=f"USER-{user.id}",
        capacity_kw=profile.plant_capacity_kw,
        location=", ".join(filter(None, [profile.city, profile.state])) or None,
        owner_username=user.username,
        installed_on=profile.installation_date,
        status="active",
    )
    db.add(plant)
    db.commit()


@router.put("")
def write_profile(payload: PlantProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = _get_or_create(db, user.id)
    for key, value in payload.model_dump().items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    _ensure_plant_started(db, user, profile)
    return _serialize(profile)
