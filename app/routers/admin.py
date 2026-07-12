from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sqlalchemy import func

from app.auth import require_admin
from app.database import get_db
from app.models import Alert, AuthEvent, Device, EnergyReading, PageVisit, SolarPlant, User
from app.services import billing_service, settings_service

router = APIRouter(prefix="/api/admin", tags=["Admin"], dependencies=[Depends(require_admin)])

_DEVICE_OFFLINE_AFTER_MINUTES = 5


def _today_start() -> datetime:
    return datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    latest = db.query(EnergyReading).order_by(EnergyReading.id.desc()).first()
    today_start = _today_start()

    total_generated = db.query(func.coalesce(func.sum(EnergyReading.generated_kwh), 0.0)).scalar()
    today_generated = db.query(func.coalesce(func.sum(EnergyReading.generated_kwh), 0.0)).filter(
        EnergyReading.timestamp >= today_start
    ).scalar()

    device_cutoff = datetime.now(timezone.utc) - timedelta(minutes=_DEVICE_OFFLINE_AFTER_MINUTES)
    devices = db.query(Device).all()
    online_devices = sum(
        1 for d in devices
        if d.last_seen and d.last_seen.replace(tzinfo=timezone.utc if d.last_seen.tzinfo is None else d.last_seen.tzinfo) >= device_cutoff
    )

    billing = billing_service.monthly_estimate(db)

    return {
        "total_users": db.query(User).count(),
        "total_plants": db.query(SolarPlant).count(),
        "total_readings": db.query(EnergyReading).count(),
        "total_energy_generated_kwh": round(total_generated, 2),
        "today_energy_kwh": round(today_generated, 2),
        "total_savings_this_month": billing["estimated_savings"],
        "unresolved_alerts": db.query(Alert).filter(Alert.resolved == False).count(),  # noqa: E712
        "resolved_alerts": db.query(Alert).filter(Alert.resolved == True).count(),  # noqa: E712
        "online_devices": online_devices,
        "offline_devices": len(devices) - online_devices,
        "total_visits": db.query(PageVisit).count(),
        "visits_today": db.query(PageVisit).filter(PageVisit.timestamp >= today_start).count(),
        "signups_today": db.query(AuthEvent).filter(
            AuthEvent.event_type == "register", AuthEvent.timestamp >= today_start
        ).count(),
        "logins_today": db.query(AuthEvent).filter(
            AuthEvent.event_type == "login", AuthEvent.timestamp >= today_start
        ).count(),
        "latest_reading": {
            "timestamp": latest.timestamp.isoformat(),
            "battery_pct": latest.battery_pct,
            "inverter_status": latest.inverter_status,
        } if latest else None,
    }


@router.get("/activity")
def activity(db: Session = Depends(get_db)):
    events = db.query(AuthEvent).order_by(AuthEvent.id.desc()).limit(30).all()

    since = datetime.now(timezone.utc) - timedelta(days=7)
    visits = db.query(PageVisit).filter(PageVisit.timestamp >= since).all()
    visits_per_day: dict[str, int] = {}
    for v in visits:
        day = v.timestamp.date().isoformat()
        visits_per_day[day] = visits_per_day.get(day, 0) + 1

    top_pages: dict[str, int] = {}
    for v in visits:
        top_pages[v.path] = top_pages.get(v.path, 0) + 1

    return {
        "recent_events": [
            {"username": e.username, "event_type": e.event_type, "timestamp": e.timestamp.isoformat()}
            for e in events
        ],
        "visits_per_day": [{"date": d, "count": c} for d, c in sorted(visits_per_day.items())],
        "top_pages": sorted(
            [{"path": p, "count": c} for p, c in top_pages.items()], key=lambda x: -x["count"]
        )[:10],
    }


@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    rows = db.query(User).order_by(User.id).all()
    return [
        {"id": u.id, "username": u.username, "is_admin": u.is_admin, "role": u.role, "created_at": u.created_at.isoformat()}
        for u in rows
    ]


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current: User = Depends(require_admin)):
    if user_id == current.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"message": "User deleted"}


class SiteSettingsUpdate(BaseModel):
    company_name: str | None = None
    logo_url: str | None = None
    theme: str | None = None
    language: str | None = None
    timezone: str | None = None


def _serialize_site_settings(row) -> dict:
    return {
        "company_name": row.company_name,
        "logo_url": row.logo_url,
        "theme": row.theme,
        "language": row.language,
        "timezone": row.timezone,
    }


@router.get("/site-settings")
def read_site_settings(db: Session = Depends(get_db)):
    return _serialize_site_settings(settings_service.get_settings(db))


@router.put("/site-settings")
def write_site_settings(payload: SiteSettingsUpdate, db: Session = Depends(get_db)):
    row = settings_service.update_settings(db, **payload.model_dump())
    return _serialize_site_settings(row)
