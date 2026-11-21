"""
Application settings and runtime environment configuration for Kolang.

Uses pydantic-settings to load, validate, and manage configuration from
environment variables and .env files with strict type safety, environment
isolation, secret masking, and fail-fast startup validation.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from acp_core.common.errors import ConfigurationError


class _LenientEnvSettingsSource(EnvSettingsSource):
    """Env source supporting comma-separated strings as fallback for complex types."""

    def decode_complex_value(self, field_name: str, field: FieldInfo, value: Any) -> Any:
        try:
            return super().decode_complex_value(field_name, field, value)
        except (json.JSONDecodeError, ValueError):
            if isinstance(value, str):
                return [item.strip() for item in value.split(",") if item.strip()]
            raise


class _LenientDotEnvSettingsSource(DotEnvSettingsSource):
    """DotEnv source supporting comma-separated strings as fallback for complex types."""

    def decode_complex_value(self, field_name: str, field: FieldInfo, value: Any) -> Any:
        try:
            return super().decode_complex_value(field_name, field, value)
        except (json.JSONDecodeError, ValueError):
            if isinstance(value, str):
                return [item.strip() for item in value.split(",") if item.strip()]
            raise


class Settings(BaseSettings):
    """Kolang application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customise settings sources to allow comma-separated lists in environment variables."""
        return (
            init_settings,
            _LenientEnvSettingsSource(settings_cls),
            _LenientDotEnvSettingsSource(settings_cls),
            file_secret_settings,
        )

    # ── Environment & Application ─────────────────────────────────────────
    env: Literal["development", "staging", "production", "test"] = Field(
        default="development",
        validation_alias=AliasChoices("ACP_ENV", "APP_ENV", "ENV"),
        description="Runtime deployment environment.",
    )
    app_name: str = Field(
        default="kolang",
        validation_alias=AliasChoices("ACP_APP_NAME", "APP_NAME"),
        description="Application service identifier.",
    )
    app_debug: bool = Field(
        default=False,
        validation_alias=AliasChoices("ACP_DEBUG", "APP_DEBUG"),
        description="Enable debug mode and verbose diagnostic logging.",
    )
    app_secret_key: SecretStr = Field(
        default=SecretStr("dev-insecure-secret-key-change-in-production"),
        validation_alias=AliasChoices("ACP_SECRET_KEY", "APP_SECRET_KEY"),
        description="Internal application secret key for cryptographic signing.",
    )

    # ── Database (PostgreSQL) ─────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql+asyncpg://kolang:kolang@localhost:5432/kolang",
        validation_alias=AliasChoices("ACP_DATABASE_URL", "DATABASE_URL"),
        description="PostgreSQL connection string.",
    )
    database_pool_size: int = Field(
        default=10,
        ge=1,
        validation_alias=AliasChoices("ACP_DATABASE_POOL_SIZE", "DATABASE_POOL_SIZE"),
        description="Database connection pool size.",
    )
    database_max_overflow: int = Field(
        default=20,
        ge=0,
        validation_alias=AliasChoices("ACP_DATABASE_MAX_OVERFLOW", "DATABASE_MAX_OVERFLOW"),
        description="Maximum temporary connections above pool size.",
    )

    # ── Identity / OIDC ───────────────────────────────────────────────────
    oidc_issuer_url: str = Field(
        default="",
        validation_alias=AliasChoices("ACP_OIDC_ISSUER_URL", "OIDC_ISSUER_URL"),
        description="OIDC issuer discovery URL.",
    )
    oidc_audience: str = Field(
        default="",
        validation_alias=AliasChoices("ACP_OIDC_AUDIENCE", "OIDC_AUDIENCE"),
        description="Expected audience for OIDC token verification.",
    )
    oidc_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("ACP_OIDC_CLIENT_ID", "OIDC_CLIENT_ID"),
        description="OIDC Client ID for gateway integration.",
    )
    oidc_jwks_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ACP_OIDC_JWKS_URL", "OIDC_JWKS_URL"),
        description="Direct JWKS endpoint URL if bypassing OIDC discovery.",
    )

    # ── OPA Policy Engine ─────────────────────────────────────────────────
    opa_url: str = Field(
        default="http://localhost:8181",
        validation_alias=AliasChoices("ACP_OPA_URL", "OPA_URL"),
        description="Open Policy Agent REST endpoint URL.",
    )
    opa_policy_path: str = Field(
        default="v1/data/kolang/authz",
        validation_alias=AliasChoices("ACP_OPA_POLICY_PATH", "OPA_POLICY_PATH"),
        description="Policy evaluation path inside OPA.",
    )

    # ── Credentials & Encryption ──────────────────────────────────────────
    encryption_key: SecretStr = Field(
        default=SecretStr(""),
        validation_alias=AliasChoices("ACP_ENCRYPTION_KEY", "CREDENTIAL_ENCRYPTION_KEY"),
        description="Symmetric encryption key for secrets and credentials.",
    )
    encryption_key_path: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("ACP_ENCRYPTION_KEY_PATH", "CREDENTIAL_ENCRYPTION_KEY_PATH"),
        description="Path to a file containing the symmetric encryption key.",
    )

    # ── Logging & Gateway Operational Controls ────────────────────────────
    log_level: Literal["debug", "info", "warning", "error", "critical"] = Field(
        default="info",
        validation_alias=AliasChoices("ACP_LOG_LEVEL", "APP_LOG_LEVEL"),
        description="Standardized structured log severity level.",
    )
    request_timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        validation_alias=AliasChoices("ACP_REQUEST_TIMEOUT_SECONDS", "REQUEST_TIMEOUT_SECONDS"),
        description="Default upstream and gateway request timeout in seconds.",
    )
    max_request_body_bytes: int = Field(
        default=10 * 1024 * 1024,
        gt=0,
        validation_alias=AliasChoices("ACP_MAX_REQUEST_BODY_BYTES", "MAX_REQUEST_BODY_BYTES"),
        description="Maximum allowed request payload size in bytes (default 10 MB).",
    )
    allowed_upstream_hosts: list[str] = Field(
        default_factory=lambda: ["localhost", "127.0.0.1"],
        validation_alias=AliasChoices("ACP_ALLOWED_UPSTREAM_HOSTS", "ALLOWED_UPSTREAM_HOSTS"),
        description="Allowlist of allowed upstream hostnames or IP addresses.",
    )

    # ── Cache & Telemetry ─────────────────────────────────────────────────
    redis_url: str = Field(
        default="",
        validation_alias=AliasChoices("ACP_REDIS_URL", "REDIS_URL"),
        description="Optional Redis URL for rate limiting or distributed state.",
    )
    otel_exporter_endpoint: str = Field(
        default="",
        validation_alias=AliasChoices(
            "ACP_OTEL_EXPORTER_ENDPOINT",
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "OTEL_EXPORTER_ENDPOINT",
        ),
        description="OpenTelemetry OTLP collector endpoint.",
    )
    otel_service_name: str = Field(
        default="kolang",
        validation_alias=AliasChoices("ACP_OTEL_SERVICE_NAME", "OTEL_SERVICE_NAME"),
        description="OpenTelemetry service name.",
    )

    # ── Rate Limiting & CORS ──────────────────────────────────────────────
    rate_limit_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("ACP_RATE_LIMIT_ENABLED", "RATE_LIMIT_ENABLED"),
        description="Enable API rate limiting.",
    )
    rate_limit_default_rpm: int = Field(
        default=60,
        gt=0,
        validation_alias=AliasChoices("ACP_RATE_LIMIT_DEFAULT_RPM", "RATE_LIMIT_DEFAULT_RPM"),
        description="Default requests per minute allowed.",
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        validation_alias=AliasChoices("ACP_CORS_ORIGINS", "CORS_ORIGINS"),
        description="Allowed CORS origin domains.",
    )

    # ── Field Normalization & Parsing Validators ──────────────────────────

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @field_validator("allowed_upstream_hosts", "cors_origins", mode="before")
    @classmethod
    def _parse_string_list(cls, value: Any) -> Any:
        """Parse comma-separated strings or JSON arrays into a list of strings."""
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("[") and stripped.endswith("]"):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except json.JSONDecodeError:
                    pass
            return [item.strip() for item in stripped.split(",") if item.strip()]
        return value

    @field_validator("database_url")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        """Ensure the database URL conforms to PostgreSQL scheme standards."""
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("ACP_DATABASE_URL must not be empty.")
        valid_schemes = ("postgresql://", "postgresql+asyncpg://", "postgres://")
        if not any(trimmed.startswith(s) for s in valid_schemes):
            raise ValueError(
                f"Invalid database scheme in ACP_DATABASE_URL: {trimmed}. "
                "Expected postgresql:// or postgresql+asyncpg://"
            )
        return trimmed

    # ── Cross-Field & Environment Validation ──────────────────────────────

    @model_validator(mode="after")
    def _validate_environment_and_secrets(self) -> Self:
        """
        Enforce environment-specific constraints and file-based secret resolution.

        - Resolves secret files if encryption_key_path is provided.
        - Enforces that production environments have non-empty, non-default encryption keys.
        - Enforces that production environments have valid OIDC issuer and audience.
        - Enforces that production environments do not use default dev keys or localhost DB.
        """
        # 1. Resolve encryption key file if configured
        if self.encryption_key_path is not None:
            key_file = Path(self.encryption_key_path)
            if not key_file.is_file():
                raise ConfigurationError(
                    f"Configured encryption key file does not exist: {key_file}",
                    details={"path": str(key_file)},
                )
            try:
                raw_key = key_file.read_text(encoding="utf-8").strip()
                if not raw_key:
                    raise ConfigurationError(
                        f"Configured encryption key file is empty: {key_file}",
                        details={"path": str(key_file)},
                    )
                self.encryption_key = SecretStr(raw_key)
            except OSError as err:
                raise ConfigurationError(
                    f"Failed to read encryption key file {key_file}: {err}",
                    details={"path": str(key_file), "error": str(err)},
                ) from err

        # 2. Strict Production Guardrails
        if self.is_production:
            # Enforce non-empty and non-default encryption key
            key_val = self.encryption_key.get_secret_value().strip()
            insecure_key_placeholders = {
                "",
                "change-me",
                "change-me-in-production",
                "generate-with-scripts/generate-key.py",
                "dev-secret-key-change-in-production",
            }
            if not key_val or key_val in insecure_key_placeholders:
                raise ConfigurationError(
                    "Missing or insecure encryption key in production. "
                    "A valid 256-bit key must be supplied via ACP_ENCRYPTION_KEY "
                    "or ACP_ENCRYPTION_KEY_PATH.",
                    details={"env": self.env},
                )
            if len(key_val) < 32:
                raise ConfigurationError(
                    "ACP_ENCRYPTION_KEY is too short for production use "
                    "(minimum 32 characters or 256-bit base64).",
                    details={"env": self.env, "key_length": len(key_val)},
                )

            # Enforce OIDC configuration in production
            if not self.oidc_issuer_url.strip():
                raise ConfigurationError(
                    "Missing required OIDC issuer URL in production. Set ACP_OIDC_ISSUER_URL.",
                    details={"env": self.env},
                )
            if not self.oidc_audience.strip():
                raise ConfigurationError(
                    "Missing required OIDC audience in production. Set ACP_OIDC_AUDIENCE.",
                    details={"env": self.env},
                )

            # Enforce production application secret key
            secret_key_val = self.app_secret_key.get_secret_value().strip()
            if not secret_key_val or secret_key_val in insecure_key_placeholders:
                raise ConfigurationError(
                    "Insecure default ACP_SECRET_KEY detected in production. "
                    "Set a cryptographically strong secret.",
                    details={"env": self.env},
                )

            # Enforce non-localhost production database
            if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
                raise ConfigurationError(
                    "Localhost ACP_DATABASE_URL is not allowed in production environment.",
                    details={"env": self.env},
                )

        return self

    # ── Backward-Compatibility Accessors ──────────────────────────────────

    @property
    def app_env(self) -> str:
        """Backward-compatible alias for env."""
        return self.env

    @property
    def app_log_level(self) -> str:
        """Backward-compatible alias for log_level."""
        return self.log_level

    @property
    def credential_encryption_key(self) -> SecretStr:
        """Backward-compatible alias for encryption_key."""
        return self.encryption_key

    @property
    def is_production(self) -> bool:
        """Return True if running in production."""
        return self.env == "production"

    @property
    def is_staging(self) -> bool:
        """Return True if running in staging."""
        return self.env == "staging"

    @property
    def is_development(self) -> bool:
        """Return True if running in development."""
        return self.env == "development"

    @property
    def is_test(self) -> bool:
        """Return True if running in test environment."""
        return self.env == "test"

    # ── Secret Masking and Safe Serialization ─────────────────────────────

    @staticmethod
    def sanitize_url(url: str) -> str:
        """
        Mask sensitive credentials (e.g., passwords) inside a connection URL.

        Example:
            postgresql+asyncpg://user:secret@localhost:5432/db ->
            postgresql+asyncpg://user:***@localhost:5432/db
        """
        if not url:
            return ""
        # Match pattern: scheme://username:password@host
        return re.sub(r"://([^:@]+):([^@]+)@", r"://\1:***@", url)

    def safe_dump(self) -> dict[str, Any]:
        """
        Return application settings dictionary with all sensitive fields redacted.

        Guarantees that no passwords, secret keys, or encryption keys are leaked
        when dumping settings for inspection or logging.
        """
        data = self.model_dump()
        for key in list(data.keys()):
            val = getattr(self, key, None)
            if isinstance(val, SecretStr):
                data[key] = "[REDACTED]"
        if "database_url" in data and isinstance(data["database_url"], str):
            data["database_url"] = self.sanitize_url(data["database_url"])
        return data

    def __repr__(self) -> str:
        """Safe representation masking all sensitive fields."""
        masked = self.safe_dump()
        items = ", ".join(f"{k}={v!r}" for k, v in masked.items())
        return f"{self.__class__.__name__}({items})"

    def __str__(self) -> str:
        """Safe string representation masking all sensitive fields."""
        return self.__repr__()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton."""
    return Settings()
