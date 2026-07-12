from datetime import datetime, timezone
from sqlalchemy import Column, ForeignKey, Integer, Float, String, DateTime, Boolean
from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class SolarPlant(Base):
    __tablename__ = "solar_plants"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    name           = Column(String(100), nullable=False)
    plant_code     = Column(String(50), unique=True, nullable=False)
    capacity_kw    = Column(Float, nullable=False)
    location       = Column(String(200))
    owner_username = Column(String(50))
    installed_on   = Column(DateTime)
    status         = Column(String(20), default="active")  # active | inactive
    created_at     = Column(DateTime, default=_now)


class EnergyReading(Base):
    __tablename__ = "energy_readings"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    plant_id         = Column(Integer, ForeignKey("solar_plants.id"), index=True)
    timestamp        = Column(DateTime, default=_now, index=True)
    generated_kwh    = Column(Float, nullable=False)   # produced since last reading
    consumed_kwh     = Column(Float, nullable=False)   # consumed since last reading
    grid_export_kwh  = Column(Float, nullable=False)   # surplus sent to grid
    grid_import_kwh  = Column(Float, nullable=False)   # drawn from grid
    battery_pct      = Column(Float, nullable=False)
    inverter_status  = Column(String(20), default="ok")  # ok | fault


class Alert(Base):
    __tablename__ = "alerts"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    plant_id   = Column(Integer, ForeignKey("solar_plants.id"), index=True)
    timestamp  = Column(DateTime, default=_now, index=True)
    level      = Column(String(20), nullable=False)   # info | warning | critical
    message    = Column(String(255), nullable=False)
    resolved   = Column(Boolean, default=False)


class Device(Base):
    __tablename__ = "devices"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    plant_id    = Column(Integer, ForeignKey("solar_plants.id"), nullable=False, index=True)
    device_type = Column(String(20), nullable=False)  # inverter | smart_meter | battery | sensor
    device_code = Column(String(50), nullable=False)
    status      = Column(String(20), default="online")  # online | offline
    last_seen   = Column(DateTime, default=_now)
    created_at  = Column(DateTime, default=_now)


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    plant_id          = Column(Integer, ForeignKey("solar_plants.id"), nullable=False, index=True)
    service_date      = Column(DateTime, nullable=False)
    next_service_date = Column(DateTime)
    engineer_name     = Column(String(100))
    notes             = Column(String(500))
    created_at        = Column(DateTime, default=_now)


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_admin      = Column(Boolean, default=False, nullable=False)
    role          = Column(String(20), default="customer", nullable=False)  # super_admin | admin | engineer | customer
    totp_secret   = Column(String(32))
    totp_enabled  = Column(Boolean, default=False, nullable=False)
    created_at    = Column(DateTime, default=_now)


class SystemSettings(Base):
    __tablename__ = "system_settings"

    id                    = Column(Integer, primary_key=True)
    tariff_rate           = Column(Float, nullable=False)
    feed_in_rate          = Column(Float, nullable=False)
    battery_capacity_kwh  = Column(Float, nullable=False)
    company_name          = Column(String(100), default="Solar Monitoring Dashboard")
    logo_url              = Column(String(255))
    theme                 = Column(String(20), default="dark")     # dark | light
    language              = Column(String(10), default="en")
    timezone              = Column(String(50), default="Asia/Kolkata")


class AuthEvent(Base):
    __tablename__ = "auth_events"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    username   = Column(String(50), nullable=False, index=True)
    event_type = Column(String(20), nullable=False)  # register | login | logout
    timestamp  = Column(DateTime, default=_now, index=True)


class PageVisit(Base):
    __tablename__ = "page_visits"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    path      = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime, default=_now, index=True)


class PlantProfile(Base):
    __tablename__ = "plant_profiles"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    user_id               = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Basic Details
    meter_number          = Column(String(50))
    meter_serial_number   = Column(String(50))
    consumer_number       = Column(String(50))
    customer_name         = Column(String(100))
    mobile_number         = Column(String(20))
    email                 = Column(String(100))
    address               = Column(String(255))

    # Solar Plant Details
    plant_name            = Column(String(100))
    plant_capacity_kw     = Column(Float)
    panel_count           = Column(Integer)
    inverter_name         = Column(String(100))
    inverter_serial_number = Column(String(50))
    inverter_capacity     = Column(String(50))
    installation_date     = Column(DateTime)

    # Meter Details
    meter_manufacturer    = Column(String(100))
    meter_model           = Column(String(100))
    phase                 = Column(String(20))  # single | three
    voltage               = Column(String(20))
    current_rating        = Column(String(20))
    ct_pt_ratio           = Column(String(20))

    # Location
    state                 = Column(String(50))
    city                  = Column(String(50))
    latitude              = Column(Float)
    longitude             = Column(Float)

    # Monitoring
    connectivity_type     = Column(String(20))  # wifi | ethernet | 4g
    data_logger_id        = Column(String(50))
    gateway_id            = Column(String(50))
    modbus_address        = Column(String(20))
    modbus_slave_id       = Column(String(20))

    updated_at            = Column(DateTime, default=_now)


class ErrorLog(Base):
    __tablename__ = "error_logs"

    id        = Column(Integer, primary_key=True, autoincrement=True)
    path      = Column(String(255))
    message   = Column(String(1000), nullable=False)
    timestamp = Column(DateTime, default=_now, index=True)
