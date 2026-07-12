from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Alert, EnergyReading

_FAULT_MSG = "Inverter fault detected"
_LOW_BATTERY_PREFIX = "Battery low"
_NO_GEN_MSG = "No generation during peak sunlight hours — check panels/inverter"


def _has_active(db: Session, plant_id: int | None, message_prefix: str) -> bool:
    return (
        db.query(Alert)
        .filter(Alert.plant_id == plant_id, Alert.resolved == False, Alert.message.like(f"{message_prefix}%"))  # noqa: E712
        .first()
        is not None
    )


def _resolve_active(db: Session, plant_id: int | None, message_prefix: str) -> None:
    db.query(Alert).filter(
        Alert.plant_id == plant_id, Alert.resolved == False, Alert.message.like(f"{message_prefix}%")  # noqa: E712
    ).update({"resolved": True}, synchronize_session=False)


def evaluate_reading(db: Session, reading: EnergyReading) -> list[Alert]:
    new_alerts: list[Alert] = []
    plant_id = reading.plant_id

    if reading.inverter_status == "fault":
        if not _has_active(db, plant_id, _FAULT_MSG):
            new_alerts.append(Alert(plant_id=plant_id, level="critical", message=_FAULT_MSG))
    else:
        _resolve_active(db, plant_id, _FAULT_MSG)

    if reading.battery_pct < 15:
        if not _has_active(db, plant_id, _LOW_BATTERY_PREFIX):
            new_alerts.append(Alert(plant_id=plant_id, level="warning", message=f"Battery low: {reading.battery_pct:.0f}%"))
    else:
        _resolve_active(db, plant_id, _LOW_BATTERY_PREFIX)

    hour = datetime.now().hour
    if 9 <= hour <= 15 and reading.generated_kwh == 0:
        if not _has_active(db, plant_id, _NO_GEN_MSG):
            new_alerts.append(Alert(plant_id=plant_id, level="warning", message=_NO_GEN_MSG))
    else:
        _resolve_active(db, plant_id, _NO_GEN_MSG)

    for a in new_alerts:
        db.add(a)
    db.commit()

    return new_alerts
