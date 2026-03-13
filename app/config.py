from functools import lru_cache
from typing import List

from pydantic import field_validator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "UNIGOM Biométrie"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True  # Enable debug by default for development
    ENVIRONMENT: str = "development"
    
    # Database URLs - All using local MySQL
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/rhunigom_presence?charset=utf8mb4"
    DATABASE_PROD_URL: str = (
        "mysql+pymysql://root:password@localhost:3306/rhunigom__database_production?charset=utf8mb4"
    )
    DATABASE_PRESENCE_URL: str = (
        "mysql+pymysql://root:password@localhost:3306/rhunigom_presence?charset=utf8mb4"
    )
    
    # JWT / Security
    JWT_SECRET_KEY: str = "change-this-secret-key-in-production-unigom-2026"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440
    
    # CORS Configuration - Use string to avoid auto-JSON parsing issues
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:3001,https://unigom.onrender.com",
        description="CORS allowed origins (comma-separated)"
    )
    
    # Hikvision Terminal
    HIKVISION_IP: str = "192.168.1.115"
    HIKVISION_USER: str = "admin"
    HIKVISION_PASSWORD: str = "Unigom2026"
    HIKVISION_TIMEOUT: int = 30
    
    # Security Lockout
    MAX_FAILED_ATTEMPTS: int = 5
    LOCKOUT_MINUTES: int = 15
    
    # Location & Time
    TIMEZONE: str = "Africa/Lubumbashi"
    DEVICE_SENDS_LOCAL_TIME: bool = True
    
    # EHome Server
    EHOME_PORT: int = 7660
    EHOME_DEVICE_ACCOUNT: str = "Unigom"
    EHOME_KEY: str = "Unigom2026"
    EHOME_SERVER_IP: str = "95.216.18.174"
    
    # Campus & Device
    CAMPUS_ID: str = "GOMA"
    DEVICE_ID: str = "HIK001"
    
    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v) -> str:
        """Parse CORS_ORIGINS from string, ensuring it's never empty.

        This validator handles both bare comma‑separated strings *and* JSON
        list literals which are commonly written in an env file.  The former is
        what the application expects internally; the latter is what tools such
        as `docker-compose` will happily store when you use `CORS_ORIGINS=["a","b"]`.
        """
        if isinstance(v, str):
            txt = v.strip()
            if not txt or txt in ("[]", "None"):
                return "http://localhost:3000,http://localhost:3001"

            # try to parse a JSON list and convert back to comma string
            if txt.startswith("[") and txt.endswith("]"):
                try:
                    import json

                    parsed = json.loads(txt)
                    if isinstance(parsed, list):
                        return ",".join(parsed)
                except Exception:  # stay silent and fall back to manual splitting
                    pass

            return txt

        # Default fallback
        return "http://localhost:3000,http://localhost:3001"
    
    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def ensure_cors_is_list(cls, v) -> List[str]:
        """Convert CORS_ORIGINS string to list for the application.

        The input may still be a JSON‑style string with quoted entries; strip
        extraneous characters so that FastAPI sees bare origins.
        """
        if isinstance(v, str):
            txt = v.strip()
            # try again to parse json if we accidentally dropped it earlier
            if txt.startswith("[") and txt.endswith("]"):
                try:
                    import json

                    parsed = json.loads(txt)
                    if isinstance(parsed, list):
                        origins = [o.strip() for o in parsed if isinstance(o, str) and o.strip()]
                        if origins:
                            return origins
                except Exception:
                    pass

            # manual split and remove any surrounding quotes/brackets
            origins = [o.strip().strip('"').strip("'").strip("[]") for o in txt.split(",") if o.strip()]
            return origins if origins else ["http://localhost:3000", "http://localhost:3001"]
        if isinstance(v, list):
            return v
        return ["http://localhost:3000", "http://localhost:3001"]

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
