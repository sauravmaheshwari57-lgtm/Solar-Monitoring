from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Device, EnergyReading, SolarPlant
from app.services import plant_service, settings_service
from app.services.drivers.simulator_driver import SimulatorDriver
from app.services.drivers.modbus_driver import ModbusDriver

_DRIVERS = {
    "simulator": SimulatorDriver,
    "modbus": ModbusDriver,
}

_drivers_by_plant: dict[int, object] = {}


def _get_driver(plant_id: int):
    if plant_id not in _drivers_by_plant:
        driver_cls = _DRIVERS.get(settings.DATA_SOURCE, SimulatorDriver)
        _drivers_by_plant[plant_id] = driver_cls()
    return _drivers_by_plant[plant_id]


def active_plants(db: Session) -> list[SolarPlant]:
    plants = db.query(SolarPlant).filter(SolarPlant.status == "active").all()
    if not plants:
        plants = [plant_service.get_default_plant(db)]
    return plants


def generate_reading(db: Session, plant: SolarPlant) -> EnergyReading:
    telemetry = _get_driver(plant.id).read()

    last = (
        db.query(EnergyReading)
        .filter(EnergyReading.plant_id == plant.id)
        .order_by(EnergyReading.id.desc())
        .first()
    )
    battery_pct = last.battery_pct if last else 50.0
    battery_capacity = settings_service.get_settings(db).battery_capacity_kwh

    surplus = telemetry.generated_kwh - telemetry.consumed_kwh
    grid_export = 0.0
    grid_import = 0.0

    if surplus > 0:
        room_kwh = (100 - battery_pct) / 100 * battery_capacity
        charge = min(surplus, room_kwh)
        battery_pct += (charge / battery_capacity) * 100
        grid_export = surplus - charge
    else:
        deficit = -surplus
        available_kwh = (battery_pct / 100) * battery_capacity
        discharge = min(deficit, available_kwh)
        battery_pct -= (discharge / battery_capacity) * 100
        grid_import = deficit - discharge

    battery_pct = max(0.0, min(100.0, battery_pct))

    reading = EnergyReading(
        plant_id=plant.id,
        timestamp=datetime.now(timezone.utc),
        generated_kwh=telemetry.generated_kwh,
        consumed_kwh=telemetry.consumed_kwh,
        grid_export_kwh=round(grid_export, 4),
        grid_import_kwh=round(grid_import, 4),
        battery_pct=round(battery_pct, 2),
        inverter_status=telemetry.inverter_status,
    )
    db.add(reading)
    _heartbeat_inverter(db, plant.id, telemetry.inverter_status)
    db.commit()
    db.refresh(reading)
    return reading


def _heartbeat_inverter(db, plant_id: int, inverter_status: str) -> None:
    device = db.query(Device).filter(Device.plant_id == plant_id, Device.device_type == "inverter").first()
    if not device:
        device = Device(plant_id=plant_id, device_type="inverter", device_code=f"PLANT-{plant_id}-INV")
        db.add(device)
    device.last_seen = datetime.now(timezone.utc)
    device.status = "online" if inverter_status == "ok" else "offline"
