"""
Application settings for Kolang.

Uses pydantic-settings to load configuration from environment variables
and .env files with type validation.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Kolang application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────────────────
    app_name: str = "kolang"
    app_env: Literal["development", "staging", "production"] = "development"
    app_debug: bool = False
    app_log_level: str = "info"
    app_secret_key: SecretStr = SecretStr("change-me-in-production")

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://kolang:kolang@localhost:5432/kolang"
    database_pool_size: int = 10
    database_max_overflow: int = 20

    # ── Identity / OIDC ──────────────────────────────────────────────────
    oidc_issuer_url: str = ""
    oidc_client_id: str = ""
    oidc_audience: str = ""

    # ── OPA Policy Engine ────────────────────────────────────────────────
    opa_url: str = "http://localhost:8181"
    opa_policy_path: str = "v1/data/kolang/authz"

    # ── Redis (optional) ─────────────────────────────────────────────────
    redis_url: str = ""

    # ── Telemetry ────────────────────────────────────────────────────────
    otel_exporter_endpoint: str = ""
    otel_service_name: str = "kolang"

    # ── Credentials ──────────────────────────────────────────────────────
    credential_encryption_key: SecretStr = SecretStr("")

    # ── Rate Limiting ────────────────────────────────────────────────────
    rate_limit_enabled: bool = False
    rate_limit_default_rpm: int = 60

    # ── CORS ─────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
