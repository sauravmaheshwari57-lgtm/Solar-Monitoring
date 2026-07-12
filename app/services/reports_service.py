from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.models import EnergyReading

_PERIODS = {
    "daily": (timedelta(hours=24), "%H:00"),
    "weekly": (timedelta(days=7), "%Y-%m-%d"),
    "monthly": (timedelta(days=30), "%Y-%m-%d"),
    "yearly": (timedelta(days=365), "%Y-%m"),
}


def energy_report(db: Session, period: str) -> dict:
    span, fmt = _PERIODS.get(period, _PERIODS["weekly"])
    since = datetime.now(timezone.utc) - span

    rows = (
        db.query(EnergyReading)
        .filter(EnergyReading.timestamp >= since)
        .order_by(EnergyReading.timestamp)
        .all()
    )

    buckets: dict[str, dict] = {}
    totals = {"generated": 0.0, "consumed": 0.0, "exported": 0.0, "imported": 0.0}

    for r in rows:
        key = r.timestamp.strftime(fmt)
        b = buckets.setdefault(key, {"generated": 0.0, "consumed": 0.0, "exported": 0.0, "imported": 0.0})
        b["generated"] += r.generated_kwh
        b["consumed"] += r.consumed_kwh
        b["exported"] += r.grid_export_kwh
        b["imported"] += r.grid_import_kwh
        totals["generated"] += r.generated_kwh
        totals["consumed"] += r.consumed_kwh
        totals["exported"] += r.grid_export_kwh
        totals["imported"] += r.grid_import_kwh

    buckets_list = [
        {"label": k, **{kk: round(vv, 3) for kk, vv in v.items()}}
        for k, v in sorted(buckets.items())
    ]

    self_used = max(0.0, min(totals["generated"], totals["consumed"]) - 0.0)
    return {
        "period": period,
        "buckets": buckets_list,
        "totals": {kk: round(vv, 3) for kk, vv in totals.items()},
        "flow_split": {
            "used_at_home": round(self_used, 3),
            "sent_to_grid": round(totals["exported"], 3),
            "charged_to_battery": round(max(0.0, totals["generated"] - self_used - totals["exported"]), 3),
        },
    }
