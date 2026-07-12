from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import EnergyReading
from app.services import settings_service


def monthly_estimate(db: Session, plant_id: int | None = None) -> dict:
    sys_settings = settings_service.get_settings(db)
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    q = db.query(EnergyReading).filter(EnergyReading.timestamp >= month_start)
    if plant_id is not None:
        q = q.filter(EnergyReading.plant_id == plant_id)
    rows = q.all()

    imported = sum(r.grid_import_kwh for r in rows)
    exported = sum(r.grid_export_kwh for r in rows)
    consumed = sum(r.consumed_kwh for r in rows)

    grid_cost = imported * sys_settings.tariff_rate
    export_credit = exported * sys_settings.feed_in_rate
    estimated_bill = max(0.0, grid_cost - export_credit)

    hypothetical_bill = consumed * sys_settings.tariff_rate  # what it would cost with no solar at all
    savings = max(0.0, hypothetical_bill - estimated_bill)

    return {
        "period_start": month_start.date().isoformat(),
        "grid_import_kwh": round(imported, 3),
        "grid_export_kwh": round(exported, 3),
        "grid_cost": round(grid_cost, 2),
        "export_credit": round(export_credit, 2),
        "estimated_bill": round(estimated_bill, 2),
        "estimated_savings": round(savings, 2),
        "tariff_rate": sys_settings.tariff_rate,
        "feed_in_rate": sys_settings.feed_in_rate,
    }
