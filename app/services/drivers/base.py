from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RawTelemetry:
    generated_kwh: float   # energy produced since last reading
    consumed_kwh: float    # energy consumed since last reading
    inverter_status: str   # "ok" | "fault"


class InverterDriver(ABC):
    @abstractmethod
    def read(self) -> RawTelemetry:
        ...
