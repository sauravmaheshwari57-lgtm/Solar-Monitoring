from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "Solar Monitoring Dashboard"
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/solar_monitor"
    TARIFF_RATE: float = 8.0        # cost per kWh drawn from grid
    FEED_IN_RATE: float = 3.5       # credit per kWh exported to grid
    BATTERY_CAPACITY_KWH: float = 10.0
    SIM_INTERVAL_SECONDS: int = 10  # how often the simulated inverter reports a reading

    JWT_SECRET: str = "change-this-secret-in-.env"
    JWT_EXPIRE_HOURS: int = 24

    DATA_SOURCE: str = "simulator"  # simulator | modbus
    MODBUS_HOST: str = "192.168.1.100"
    MODBUS_PORT: int = 502
    MODBUS_UNIT_ID: int = 1
    MODBUS_GENERATED_REGISTER: int = 0
    MODBUS_CONSUMED_REGISTER: int = 2
    MODBUS_STATUS_REGISTER: int = 4

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
