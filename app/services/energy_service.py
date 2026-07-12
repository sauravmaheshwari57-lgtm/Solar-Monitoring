from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.models import EnergyReading


def today_summary(db: Session, plant_id: int | None = None) -> dict:
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    q = db.query(EnergyReading).filter(EnergyReading.timestamp >= today_start)
    if plant_id is not None:
        q = q.filter(EnergyReading.plant_id == plant_id)
    rows = q.all()

    latest = rows[-1] if rows else None
    return {
        "generated_kwh": round(sum(r.generated_kwh for r in rows), 3),
        "consumed_kwh": round(sum(r.consumed_kwh for r in rows), 3),
        "grid_export_kwh": round(sum(r.grid_export_kwh for r in rows), 3),
        "grid_import_kwh": round(sum(r.grid_import_kwh for r in rows), 3),
        "battery_pct": latest.battery_pct if latest else None,
        "inverter_status": latest.inverter_status if latest else "unknown",
        "reading_count": len(rows),
    }


def history(db: Session, days: int = 7, plant_id: int | None = None) -> list[dict]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    q = db.query(EnergyReading).filter(EnergyReading.timestamp >= since)
    if plant_id is not None:
        q = q.filter(EnergyReading.plant_id == plant_id)
    rows = q.order_by(EnergyReading.timestamp).all()

    buckets: dict[str, dict] = {}
    for r in rows:
        day = r.timestamp.date().isoformat()
        b = buckets.setdefault(day, {"generated_kwh": 0.0, "consumed_kwh": 0.0, "grid_export_kwh": 0.0, "grid_import_kwh": 0.0})
        b["generated_kwh"] += r.generated_kwh
        b["consumed_kwh"] += r.consumed_kwh
        b["grid_export_kwh"] += r.grid_export_kwh
        b["grid_import_kwh"] += r.grid_import_kwh

    return [{"date": d, **{k: round(v, 3) for k, v in vals.items()}} for d, vals in sorted(buckets.items())]


def recent_series(db: Session, limit: int = 60, plant_id: int | None = None) -> list[dict]:
    q = db.query(EnergyReading)
    if plant_id is not None:
        q = q.filter(EnergyReading.plant_id == plant_id)
    rows = q.order_by(EnergyReading.id.desc()).limit(limit).all()
    rows.reverse()
    return [
        {
            "timestamp": r.timestamp.isoformat(),
            "generated_kwh": r.generated_kwh,
            "consumed_kwh": r.consumed_kwh,
            "battery_pct": r.battery_pct,
        }
        for r in rows
    ]
