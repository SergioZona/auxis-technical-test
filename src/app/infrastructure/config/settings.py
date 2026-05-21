"""
Application settings — clear split between config and secrets.

Config  → loaded from src/env/{APP_ENV}.env (committed, non-sensitive)
Secrets → injected at runtime via environment variables (Dokploy / GH Actions)
"""

import os
from typing import Any

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
    app_name: str = "auxis-technical-test"
    app_version: str = "1.0.0"
    api_version: str = "v1"
    debug: bool = False
    log_level: str = "INFO"
    allowed_hosts: str | list[str] = ["*"]
    database_host: str = "localhost"
    database_port: int = 5432
    database_name: str = "app_dev"
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "documents"
    max_upload_size_mb: int = 10

    # ── Secrets (injected at runtime — NEVER commit these) ──────────────────
    database_password: str = Field(default="", min_length=1)
    secret_key: str = Field(default="", min_length=1)
    openai_api_key: str = Field(default="")
    gemini_api_key: str = Field(default="")

    api_username: str = Field(default="auxis")
    api_password: str = Field(default="")

    @field_validator("api_password", mode="before")
    @classmethod
    def fallback_ui_pwd(cls, v: Any) -> Any:
        if not v:
            return os.getenv("UI_PASSWORD") or ""
        return v

    # ── Computed ─────────────────────────────────────────────────────────────
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://"
            f"app:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_name}"
        )

    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql://"
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

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def validate_allowed_hosts(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            val = v.strip()
            if val.startswith("[") and val.endswith("]"):
                try:
                    import json

                    parsed = json.loads(val)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed]
                except Exception:
                    # Strip the brackets and process as comma-separated
                    val = val[1:-1]
            return [
                item.strip().strip("'\"") for item in val.split(",") if item.strip()
            ]
        elif isinstance(v, list):
            return [str(item).strip() for item in v]
        return []

    model_config = SettingsConfigDict(
        env_file=_env_file,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


def get_settings() -> Settings:
    """Dependency-injectable settings factory."""
    return Settings()
