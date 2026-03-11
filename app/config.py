from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "UNIGOM Biométrie"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    # Supabase PostgreSQL URL
    DATABASE_URL: str = "postgresql://postgres.abjlfxnvepxfazsagxtu:mGwH1hb9IeAJ1KO2193LACV6lQFwcpMoKfM996KFBJA@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
    DATABASE_PROD_URL: str = (
        "mysql+pymysql://root:password@localhost:3306/rhunigom__database_production?charset=utf8mb4"
    )
    DATABASE_PRESENCE_URL: str = (
        "mysql+pymysql://root:password@localhost:3306/rhunigom_presence?charset=utf8mb4"
    )
    JWT_SECRET_KEY: str = "change-this-secret-key-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]
    HIKVISION_IP: str = "192.168.1.115"
    HIKVISION_USER: str = "admin"
    HIKVISION_PASSWORD: str = "Unigom2026"
    HIKVISION_TIMEOUT: int = 30
    MAX_FAILED_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15
    TIMEZONE: str = "Africa/Lubumbashi"
    DEVICE_SENDS_LOCAL_TIME: bool = True
    EHOME_PORT: int = 7660
    EHOME_DEVICE_ACCOUNT: str = "Unigom"
    EHOME_KEY: str = "Unigom2026"
    EHOME_SERVER_IP: str = "95.216.18.174"
    CAMPUS_ID: str = "GOMA"
    DEVICE_ID: str = "HIK001"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except Exception:
                return [o.strip() for o in v.split(",")]
        return v

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
