"""
Application configuration loaded from environment variables.

Production secrets (DATABASE_URL, JWT secret, agent API key, default
admin credentials) MUST be supplied through the deployment environment.
Sensible defaults are provided only for local development.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Strongly-typed application settings."""

    # ---- Project metadata ----
    PROJECT_NAME: str = "Enterprise Print Tracking System"
    API_V1_PREFIX: str = "/api"
    ENVIRONMENT: str = Field(default="development")  # development | staging | production
    DEBUG: bool = Field(default=False)

    # ---- Database ----
    # Example: postgresql+psycopg2://user:pass@host:5432/dbname?sslmode=require
    DATABASE_URL: str = Field(
        default="sqlite:///./print_tracking.db",
        description="SQLAlchemy database URL. Use Neon Postgres in production.",
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800
    DB_POOL_PRE_PING: bool = True

    # ---- Security / JWT ----
    JWT_SECRET_KEY: str = Field(
        default="change-me-in-production-please-use-a-long-random-string",
        description="HS256 secret used to sign admin JWTs.",
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12  # 12 hours

    # API key used by the on-premise print-agent to push print logs.
    AGENT_API_KEY: str = Field(
        default="change-me-agent-api-key",
        description="Shared secret presented by the print-agent on /api/print-log.",
    )

    # ---- Default admin (auto-seeded if no admins exist) ----
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_EMAIL: str = "admin@printtracking.local"
    DEFAULT_ADMIN_PASSWORD: str = "Admin@123"
    DEFAULT_ADMIN_FULL_NAME: str = "System Administrator"

    # ---- CORS ----
    # Comma-separated list of allowed origins. Use "*" only for local dev.
    CORS_ORIGINS: str = "*"

    # ---- Office printer defaults (informational + analytics) ----
    DEFAULT_PRINTER_NAME: str = "HP Smart Tank 660-670 series"
    DEFAULT_PRINTER_IP: str = "192.168.1.131"
    DEFAULT_PRINTER_NETWORK: str = "CKP_WSPACE"

    # ---- Logging ----
    LOG_LEVEL: str = "INFO"

    # Resolve `.env` relative to the backend directory, not the process CWD.
    # This avoids confusing behaviour when running under reloaders, services,
    # or process managers that change the working directory.
    _ENV_PATH = str(Path(__file__).resolve().parents[1] / ".env")

    model_config = SettingsConfigDict(
        env_file=_ENV_PATH,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---- Helpers ----
    @field_validator("DATABASE_URL")
    @classmethod
    def normalize_db_url(cls, v: str) -> str:
        """Normalise common Postgres URL formats to a SQLAlchemy-compatible URL."""
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+psycopg2://", 1)
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        if self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()


settings = get_settings()
