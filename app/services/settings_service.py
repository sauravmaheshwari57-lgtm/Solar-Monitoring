from sqlalchemy.orm import Session

from app.config import settings as env_settings
from app.models import SystemSettings

_SETTINGS_ID = 1


def get_settings(db: Session) -> SystemSettings:
    row = db.query(SystemSettings).filter(SystemSettings.id == _SETTINGS_ID).first()
    if row:
        return row

    row = SystemSettings(
        id=_SETTINGS_ID,
        tariff_rate=env_settings.TARIFF_RATE,
        feed_in_rate=env_settings.FEED_IN_RATE,
        battery_capacity_kwh=env_settings.BATTERY_CAPACITY_KWH,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_settings(db: Session, **fields) -> SystemSettings:
    row = get_settings(db)
    for key, value in fields.items():
        if value is not None:
            setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row
