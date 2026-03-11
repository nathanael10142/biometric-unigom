from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "UNIGOM Biométrie"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Database URLs
    DATABASE_URL: str = "postgresql://postgres.abjlfxnvepxfazsagxtu:mGwH1hb9IeAJ1KO2193LACV6lQFwcpMoKfM996KFBJA@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
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
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]
    
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
    def parse_cors_origins(cls, v):
        """Parse CORS_ORIGINS from string or list"""
        # If already a list, return as-is
        if isinstance(v, list):
            return v
        
        # If string, try to parse
        if isinstance(v, str):
            # Handle empty strings
            if not v or v.strip() == "":
                return [
                    "http://localhost:3000",
                    "http://localhost:3001",
                ]
            
            # Try JSON parsing first
            import json
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                # Fall back to comma-separated parsing
                try:
                    return [o.strip() for o in v.split(",") if o.strip()]
                except Exception:
                    return [
                        "http://localhost:3000",
                        "http://localhost:3001",
                    ]
        
        # Default fallback
        return [
            "http://localhost:3000",
            "http://localhost:3001",
        ]

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
