import math
import random
from datetime import datetime

from app.config import settings
from app.services.drivers.base import InverterDriver, RawTelemetry

PEAK_SYSTEM_KW = 3.0  # simulated inverter's peak output


class SimulatorDriver(InverterDriver):
    def _solar_curve_factor(self, hour: float) -> float:
        """0.0 at night, bell curve peaking at solar noon (12:00)."""
        if hour < 6 or hour > 18:
            return 0.0
        x = (hour - 12) / 6
        return max(0.0, math.cos(x * math.pi / 2))

    def read(self) -> RawTelemetry:
        local_hour = datetime.now().hour + datetime.now().minute / 60
        interval_hours = settings.SIM_INTERVAL_SECONDS / 3600

        factor = self._solar_curve_factor(local_hour)
        generated = max(0.0, PEAK_SYSTEM_KW * factor * interval_hours * random.uniform(0.85, 1.15))

        base_load_kw = random.uniform(0.3, 1.5)
        consumed = base_load_kw * interval_hours

        inverter_status = "fault" if random.random() < 0.01 else "ok"

        return RawTelemetry(
            generated_kwh=round(generated, 4),
            consumed_kwh=round(consumed, 4),
            inverter_status=inverter_status,
        )
