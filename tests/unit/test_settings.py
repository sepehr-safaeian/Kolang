"""
Unit tests for Kolang centralized application settings and environment validation.

Verifies:
- Default settings loading and type validation.
- Canonical ACP_* variables and backward compatibility aliases.
- Upstream host and CORS origin list parsing (comma-separated and JSON).
- File-based secret resolution via ACP_ENCRYPTION_KEY_PATH.
- Strict production environment validation (OIDC, encryption key, non-default secrets).
- Secret masking in safe_dump(), __str__(), and __repr__().
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from acp_core.common.errors import ConfigurationError
from acp_core.common.settings import Settings, get_settings

# Synthetic dummy values for testing only (strictly non-production, no real secrets)
DUMMY_PROD_KEY = "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
DUMMY_PROD_SECRET = "production-secret-must-be-at-least-32-chars-long"  # noqa: S105


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    """Clear lru_cache on get_settings before and after each test."""
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_default_settings_development() -> None:
    """Verify default settings loaded in standard development environment."""
    with patch.dict(os.environ, {}, clear=True):
        settings = Settings()

        assert settings.env == "development"
        assert settings.is_development is True
        assert settings.is_production is False
        assert settings.is_staging is False
        assert settings.is_test is False

        assert settings.app_name == "kolang"
        assert settings.app_debug is False
        assert settings.log_level == "info"

        assert settings.database_url.startswith("postgresql+asyncpg://")
        assert settings.request_timeout_seconds == 30.0
        assert settings.max_request_body_bytes == 10 * 1024 * 1024
        assert settings.allowed_upstream_hosts == ["localhost", "127.0.0.1"]
        assert settings.cors_origins == ["http://localhost:3000"]

        # Backward compatibility properties
        assert settings.app_env == "development"
        assert settings.app_log_level == "info"
        assert settings.credential_encryption_key == settings.encryption_key


def test_get_settings_singleton_and_caching() -> None:
    """Verify get_settings returns a cached singleton instance."""
    with patch.dict(os.environ, {}, clear=True):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

        get_settings.cache_clear()
        with patch.dict(os.environ, {"ACP_ENV": "test"}):
            s3 = get_settings()
            assert s3 is not s1
            assert s3.env == "test"
            assert s3.is_test is True


def test_canonical_acp_environment_variables() -> None:
    """Verify all canonical ACP_* environment variables are parsed correctly."""
    env_vars = {
        "ACP_ENV": "staging",
        "ACP_APP_NAME": "custom-kolang",
        "ACP_DEBUG": "true",
        "ACP_LOG_LEVEL": "WARNING",
        "ACP_DATABASE_URL": "postgresql+asyncpg://usr:pwd@db.internal:5432/acpdb",
        "ACP_DATABASE_POOL_SIZE": "25",
        "ACP_DATABASE_MAX_OVERFLOW": "50",
        "ACP_OIDC_ISSUER_URL": "https://auth.example.com/realms/prod",
        "ACP_OIDC_AUDIENCE": "custom-aud",
        "ACP_OIDC_CLIENT_ID": "acp-gateway",
        "ACP_OIDC_JWKS_URL": "https://auth.example.com/realms/prod/certs",
        "ACP_OPA_URL": "http://opa.internal:8181",
        "ACP_OPA_POLICY_PATH": "v1/data/custom/authz",
        "ACP_ENCRYPTION_KEY": DUMMY_PROD_KEY,
        "ACP_REQUEST_TIMEOUT_SECONDS": "45.5",
        "ACP_MAX_REQUEST_BODY_BYTES": "20971520",
        "ACP_ALLOWED_UPSTREAM_HOSTS": "api1.internal, api2.internal",
        "ACP_REDIS_URL": "redis://redis.internal:6379/1",
        "ACP_OTEL_EXPORTER_ENDPOINT": "http://otel.internal:4317",
        "ACP_OTEL_SERVICE_NAME": "acp-service",
        "ACP_RATE_LIMIT_ENABLED": "true",
        "ACP_RATE_LIMIT_DEFAULT_RPM": "120",
        "ACP_CORS_ORIGINS": "https://app.example.com, https://admin.example.com",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()

        assert settings.env == "staging"
        assert settings.is_staging is True
        assert settings.app_name == "custom-kolang"
        assert settings.app_debug is True
        assert settings.log_level == "warning"
        assert settings.database_url == "postgresql+asyncpg://usr:pwd@db.internal:5432/acpdb"
        assert settings.database_pool_size == 25
        assert settings.database_max_overflow == 50
        assert settings.oidc_issuer_url == "https://auth.example.com/realms/prod"
        assert settings.oidc_audience == "custom-aud"
        assert settings.oidc_client_id == "acp-gateway"
        assert settings.oidc_jwks_url == "https://auth.example.com/realms/prod/certs"
        assert settings.opa_url == "http://opa.internal:8181"
        assert settings.opa_policy_path == "v1/data/custom/authz"
        assert settings.encryption_key.get_secret_value() == DUMMY_PROD_KEY
        assert settings.request_timeout_seconds == 45.5
        assert settings.max_request_body_bytes == 20971520
        assert settings.allowed_upstream_hosts == ["api1.internal", "api2.internal"]
        assert settings.redis_url == "redis://redis.internal:6379/1"
        assert settings.otel_exporter_endpoint == "http://otel.internal:4317"
        assert settings.otel_service_name == "acp-service"
        assert settings.rate_limit_enabled is True
        assert settings.rate_limit_default_rpm == 120
        assert settings.cors_origins == ["https://app.example.com", "https://admin.example.com"]


def test_backward_compatibility_legacy_env_aliases() -> None:
    """Verify legacy environment variables (without ACP_ prefix) still resolve properly."""
    legacy_vars = {
        "APP_ENV": "development",
        "DATABASE_URL": "postgresql://usr:pwd@localhost:5432/legacydb",
        "OIDC_ISSUER_URL": "http://legacy.auth/realms/main",
        "OIDC_AUDIENCE": "legacy-aud",
        "CREDENTIAL_ENCRYPTION_KEY": DUMMY_PROD_KEY,
        "APP_LOG_LEVEL": "DEBUG",
        "REQUEST_TIMEOUT_SECONDS": "12.0",
        "MAX_REQUEST_BODY_BYTES": "1048576",
        "ALLOWED_UPSTREAM_HOSTS": "upstream1.internal,upstream2.internal",
    }

    with patch.dict(os.environ, legacy_vars, clear=True):
        settings = Settings()

        assert settings.env == "development"
        assert settings.database_url == "postgresql://usr:pwd@localhost:5432/legacydb"
        assert settings.oidc_issuer_url == "http://legacy.auth/realms/main"
        assert settings.oidc_audience == "legacy-aud"
        assert settings.encryption_key.get_secret_value() == DUMMY_PROD_KEY
        assert settings.log_level == "debug"
        assert settings.request_timeout_seconds == 12.0
        assert settings.max_request_body_bytes == 1048576
        assert settings.allowed_upstream_hosts == ["upstream1.internal", "upstream2.internal"]


def test_upstream_hosts_and_cors_json_parsing() -> None:
    """Verify allowed_upstream_hosts and cors_origins parse JSON array format properly."""
    env_vars = {
        "ACP_ALLOWED_UPSTREAM_HOSTS": '["mcp1.internal", "mcp2.internal"]',
        "ACP_CORS_ORIGINS": '["http://localhost:3000", "https://kolang.dev"]',
    }
    with patch.dict(os.environ, env_vars, clear=True):
        settings = Settings()
        assert settings.allowed_upstream_hosts == ["mcp1.internal", "mcp2.internal"]
        assert settings.cors_origins == ["http://localhost:3000", "https://kolang.dev"]


def test_type_validation_invalid_numeric_inputs() -> None:
    """Verify invalid numeric values raise validation errors."""
    with (
        patch.dict(os.environ, {"ACP_REQUEST_TIMEOUT_SECONDS": "invalid_seconds"}),
        pytest.raises(ValidationError),
    ):
        Settings()

    with (
        patch.dict(os.environ, {"ACP_REQUEST_TIMEOUT_SECONDS": "-1.0"}),
        pytest.raises(ValidationError),
    ):
        Settings()

    with (
        patch.dict(os.environ, {"ACP_MAX_REQUEST_BODY_BYTES": "0"}),
        pytest.raises(ValidationError),
    ):
        Settings()


def test_database_url_validation() -> None:
    """Verify invalid database URL schemes raise validation errors."""
    with (
        patch.dict(os.environ, {"ACP_DATABASE_URL": "mysql://user:pass@localhost/db"}),
        pytest.raises(ValidationError) as exc,
    ):
        Settings()
    assert "Invalid database scheme" in str(exc.value)

    with (
        patch.dict(os.environ, {"ACP_DATABASE_URL": ""}),
        pytest.raises(ValidationError),
    ):
        Settings()


def test_encryption_key_file_resolution(tmp_path: Path) -> None:
    """Verify reading encryption key from secret file via ACP_ENCRYPTION_KEY_PATH."""
    key_file = tmp_path / "secret.key"
    key_file.write_text(DUMMY_PROD_KEY + "\n", encoding="utf-8")

    with patch.dict(os.environ, {"ACP_ENCRYPTION_KEY_PATH": str(key_file)}):
        settings = Settings()
        assert settings.encryption_key.get_secret_value() == DUMMY_PROD_KEY


def test_encryption_key_file_missing_raises_error(tmp_path: Path) -> None:
    """Verify non-existent secret file raises ConfigurationError."""
    missing_file = tmp_path / "does_not_exist.key"
    with (
        patch.dict(os.environ, {"ACP_ENCRYPTION_KEY_PATH": str(missing_file)}),
        pytest.raises(ConfigurationError) as exc,
    ):
        Settings()
    assert "file does not exist" in str(exc.value)


def test_encryption_key_file_empty_raises_error(tmp_path: Path) -> None:
    """Verify empty secret file raises ConfigurationError."""
    empty_file = tmp_path / "empty.key"
    empty_file.write_text("   \n", encoding="utf-8")

    with (
        patch.dict(os.environ, {"ACP_ENCRYPTION_KEY_PATH": str(empty_file)}),
        pytest.raises(ConfigurationError) as exc,
    ):
        Settings()
    assert "file is empty" in str(exc.value)


def test_production_guardrail_missing_encryption_key() -> None:
    """Verify production halts if encryption key is missing."""
    prod_env = {
        "ACP_ENV": "production",
        "ACP_OIDC_ISSUER_URL": "https://auth.company.com/realms/prod",
        "ACP_OIDC_AUDIENCE": "kolang-prod",
        "ACP_DATABASE_URL": "postgresql+asyncpg://u:p@db.company.com:5432/prod_db",
        "ACP_SECRET_KEY": DUMMY_PROD_SECRET,
        "ACP_ENCRYPTION_KEY": "",
    }
    with (
        patch.dict(os.environ, prod_env, clear=True),
        pytest.raises(ConfigurationError) as exc,
    ):
        Settings()
    assert "Missing or insecure encryption key in production" in str(exc.value)


def test_production_guardrail_insecure_default_key() -> None:
    """Verify production halts if a default dev placeholder key is used."""
    prod_env = {
        "ACP_ENV": "production",
        "ACP_OIDC_ISSUER_URL": "https://auth.company.com/realms/prod",
        "ACP_OIDC_AUDIENCE": "kolang-prod",
        "ACP_DATABASE_URL": "postgresql+asyncpg://u:p@db.company.com:5432/prod_db",
        "ACP_SECRET_KEY": DUMMY_PROD_SECRET,
        "ACP_ENCRYPTION_KEY": "change-me-in-production",
    }
    with (
        patch.dict(os.environ, prod_env, clear=True),
        pytest.raises(ConfigurationError) as exc,
    ):
        Settings()
    assert "Missing or insecure encryption key in production" in str(exc.value)


def test_production_guardrail_key_too_short() -> None:
    """Verify production halts if an encryption key is shorter than 32 characters."""
    prod_env = {
        "ACP_ENV": "production",
        "ACP_OIDC_ISSUER_URL": "https://auth.company.com/realms/prod",
        "ACP_OIDC_AUDIENCE": "kolang-prod",
        "ACP_DATABASE_URL": "postgresql+asyncpg://u:p@db.company.com:5432/prod_db",
        "ACP_SECRET_KEY": DUMMY_PROD_SECRET,
        "ACP_ENCRYPTION_KEY": "short-key-12345",
    }
    with (
        patch.dict(os.environ, prod_env, clear=True),
        pytest.raises(ConfigurationError) as exc,
    ):
        Settings()
    assert "ACP_ENCRYPTION_KEY is too short" in str(exc.value)


def test_production_guardrail_missing_oidc() -> None:
    """Verify production halts if OIDC configuration is missing."""
    prod_env_no_issuer = {
        "ACP_ENV": "production",
        "ACP_DATABASE_URL": "postgresql+asyncpg://u:p@db.company.com:5432/prod_db",
        "ACP_SECRET_KEY": DUMMY_PROD_SECRET,
        "ACP_ENCRYPTION_KEY": DUMMY_PROD_KEY,
        "ACP_OIDC_ISSUER_URL": "",
        "ACP_OIDC_AUDIENCE": "kolang-prod",
    }
    with (
        patch.dict(os.environ, prod_env_no_issuer, clear=True),
        pytest.raises(ConfigurationError) as exc,
    ):
        Settings()
    assert "Missing required OIDC issuer URL in production" in str(exc.value)

    prod_env_no_aud = {
        "ACP_ENV": "production",
        "ACP_DATABASE_URL": "postgresql+asyncpg://u:p@db.company.com:5432/prod_db",
        "ACP_SECRET_KEY": DUMMY_PROD_SECRET,
        "ACP_ENCRYPTION_KEY": DUMMY_PROD_KEY,
        "ACP_OIDC_ISSUER_URL": "https://auth.company.com/realms/prod",
        "ACP_OIDC_AUDIENCE": "",
    }
    with (
        patch.dict(os.environ, prod_env_no_aud, clear=True),
        pytest.raises(ConfigurationError) as exc,
    ):
        Settings()
    assert "Missing required OIDC audience in production" in str(exc.value)


def test_production_guardrail_localhost_database() -> None:
    """Verify production rejects localhost database connections."""
    prod_env = {
        "ACP_ENV": "production",
        "ACP_OIDC_ISSUER_URL": "https://auth.company.com/realms/prod",
        "ACP_OIDC_AUDIENCE": "kolang-prod",
        "ACP_SECRET_KEY": DUMMY_PROD_SECRET,
        "ACP_ENCRYPTION_KEY": DUMMY_PROD_KEY,
        "ACP_DATABASE_URL": "postgresql+asyncpg://kolang:kolang@localhost:5432/kolang",
    }
    with (
        patch.dict(os.environ, prod_env, clear=True),
        pytest.raises(ConfigurationError) as exc,
    ):
        Settings()
    assert "Localhost ACP_DATABASE_URL is not allowed in production" in str(exc.value)


def test_valid_production_configuration() -> None:
    """Verify a properly configured production settings instance validates successfully."""
    prod_env = {
        "ACP_ENV": "production",
        "ACP_OIDC_ISSUER_URL": "https://auth.company.com/realms/prod",
        "ACP_OIDC_AUDIENCE": "kolang-prod",
        "ACP_SECRET_KEY": DUMMY_PROD_SECRET,
        "ACP_ENCRYPTION_KEY": DUMMY_PROD_KEY,
        "ACP_DATABASE_URL": "postgresql+asyncpg://app_user:pwd@db.prod.internal:5432/kolang",
    }
    with patch.dict(os.environ, prod_env, clear=True):
        settings = Settings()
        assert settings.is_production is True
        assert settings.env == "production"
        assert settings.encryption_key.get_secret_value() == DUMMY_PROD_KEY


def test_safe_masking_secrets_never_leaked() -> None:
    """Verify safe_dump, __str__, and __repr__ never expose plaintext secrets or passwords."""
    mock_secret = "dummy-raw-secret-key-123456789012345678"  # noqa: S105
    mock_db_pass = "dummy-raw-db-pass-xyz"  # noqa: S105
    mock_enc_key = "dummy-secret-encryption-key-test"

    with patch.dict(
        os.environ,
        {
            "ACP_SECRET_KEY": mock_secret,
            "ACP_ENCRYPTION_KEY": mock_enc_key,
            "ACP_DATABASE_URL": f"postgresql+asyncpg://admin:{mock_db_pass}@db.internal:5432/mydb",
        },
        clear=True,
    ):
        settings = Settings()

        # Check safe_dump()
        dumped = settings.safe_dump()
        assert dumped["encryption_key"] == "[REDACTED]"
        assert dumped["app_secret_key"] == "[REDACTED]"  # noqa: S105
        assert dumped["database_url"] == "postgresql+asyncpg://admin:***@db.internal:5432/mydb"

        # Check that raw secrets are absent from string representations
        str_repr = str(settings)
        repr_val = repr(settings)

        for representation in (str_repr, repr_val):
            assert mock_secret not in representation
            assert mock_db_pass not in representation
            assert mock_enc_key not in representation
            assert "[REDACTED]" in representation
            assert "admin:***@db.internal:5432/mydb" in representation
