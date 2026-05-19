"""
Application settings — clear split between config and secrets.

Config  → loaded from src/env/{APP_ENV}.env (committed, non-sensitive)
Secrets → injected at runtime via environment variables (Dokploy / GH Actions)
"""

import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_app_env = os.getenv("APP_ENV", "").strip().lower()

# Resolution order:
#   1. APP_ENV is set → load src/env/{APP_ENV}.env  (e.g. DEV.env, TEST.env)
#   2. APP_ENV is not set → load src/env/.env  (local default, gitignored)
_env_file = f"src/env/{_app_env.upper()}.env" if _app_env else "src/env/.env"


class Settings(BaseSettings):
    # ── Config (from .env file — safe to version control) ──────────────────
    app_env: str = "dev"
    app_name: str = "hexagonal-backend-template"
    app_version: str = "0.0.0"  # bumped by Release Please on every release
    api_version: str = "v1"
    debug: bool = False
    log_level: str = "INFO"
    allowed_hosts: list[str] = ["*"]
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "app_dev"

    # ── Secrets (injected at runtime — NEVER commit these) ──────────────────
    database_password: str = Field(default="", min_length=1)
    secret_key: str = Field(default="", min_length=1)

    # ── Computed ─────────────────────────────────────────────────────────────
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"app:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in allowed:
            raise ValueError(f"log_level must be one of {allowed}")
        return upper

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


def get_settings() -> Settings:
    """Dependency-injectable settings factory."""
    return Settings()
