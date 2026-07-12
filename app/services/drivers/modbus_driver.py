from app.config import settings
from app.services.drivers.base import InverterDriver, RawTelemetry


class ModbusDriver(InverterDriver):
    """Reads live telemetry from a real inverter over Modbus TCP.

    Register addresses differ by brand/model (Growatt, Deye, Solis, Huawei, ...).
    Look up the holding-register map in your inverter's Modbus documentation and
    set MODBUS_GENERATED_REGISTER / MODBUS_CONSUMED_REGISTER / MODBUS_STATUS_REGISTER
    in .env accordingly before switching DATA_SOURCE=modbus.

    Requires: pip install pymodbus
    """

    def __init__(self):
        from pymodbus.client import ModbusTcpClient  # optional dependency, only needed for this driver

        self._client = ModbusTcpClient(settings.MODBUS_HOST, port=settings.MODBUS_PORT)
        self._last_generated_total: float | None = None
        self._last_consumed_total: float | None = None

    def read(self) -> RawTelemetry:
        if not self._client.connect():
            return RawTelemetry(generated_kwh=0.0, consumed_kwh=0.0, inverter_status="fault")

        try:
            gen_reg = self._client.read_holding_registers(
                settings.MODBUS_GENERATED_REGISTER, count=2, slave=settings.MODBUS_UNIT_ID
            )
            load_reg = self._client.read_holding_registers(
                settings.MODBUS_CONSUMED_REGISTER, count=2, slave=settings.MODBUS_UNIT_ID
            )
            status_reg = self._client.read_holding_registers(
                settings.MODBUS_STATUS_REGISTER, count=1, slave=settings.MODBUS_UNIT_ID
            )
        except Exception:
            return RawTelemetry(generated_kwh=0.0, consumed_kwh=0.0, inverter_status="fault")

        if gen_reg.isError() or load_reg.isError() or status_reg.isError():
            return RawTelemetry(generated_kwh=0.0, consumed_kwh=0.0, inverter_status="fault")

        # Most inverters report cumulative lifetime energy as a 32-bit value split
        # across two 16-bit registers (high word, low word), scaled by 100.
        generated_total = (gen_reg.registers[0] << 16 | gen_reg.registers[1]) / 100.0
        consumed_total = (load_reg.registers[0] << 16 | load_reg.registers[1]) / 100.0
        status_ok = status_reg.registers[0] == 0

        generated_kwh = 0.0 if self._last_generated_total is None else max(0.0, generated_total - self._last_generated_total)
        consumed_kwh = 0.0 if self._last_consumed_total is None else max(0.0, consumed_total - self._last_consumed_total)

        self._last_generated_total = generated_total
        self._last_consumed_total = consumed_total

        return RawTelemetry(
            generated_kwh=round(generated_kwh, 4),
            consumed_kwh=round(consumed_kwh, 4),
            inverter_status="ok" if status_ok else "fault",
        )
