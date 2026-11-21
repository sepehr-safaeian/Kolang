"""
Unit tests for the centralized redaction utility in Kolang.
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, SecretStr

from acp_core.common.errors import UpstreamError
from acp_core.common.redaction import (
    REDACTED_STR,
    is_sensitive_key,
    redact_data,
    redact_exception,
    redact_headers,
    redact_text,
    redact_tool_payload,
    sanitize_upstream_error,
)


def test_is_sensitive_key() -> None:
    assert is_sensitive_key("authorization") is True
    assert is_sensitive_key("Authorization") is True
    assert is_sensitive_key("AUTHORIZATION") is True
    assert is_sensitive_key("x-api-key") is True
    assert is_sensitive_key("X_API_KEY") is True
    assert is_sensitive_key("access_token") is True
    assert is_sensitive_key("refreshToken") is True
    assert is_sensitive_key("client_secret") is True
    assert is_sensitive_key("password") is True
    assert is_sensitive_key("Cookie") is True
    assert is_sensitive_key("set-cookie") is True
    assert is_sensitive_key("bearer") is True

    # Non-sensitive keys
    assert is_sensitive_key("content-type") is False
    assert is_sensitive_key("username") is False
    assert is_sensitive_key("tool_name") is False
    assert is_sensitive_key("request_id") is False


def test_redact_text_bearer_and_basic_auth() -> None:
    bearer_text = "Sending request with header Authorization: Bearer mock-access-token-123456"
    redacted = redact_text(bearer_text)
    assert "mock-access-token-123456" not in redacted
    assert "Bearer [REDACTED]" in redacted

    basic_text = "Basic authentication used: Basic dXNlcjpwYXNzd29yZDEyMw=="
    redacted_basic = redact_text(basic_text)
    assert "dXNlcjpwYXNzd29yZDEyMw==" not in redacted_basic
    assert "Basic [REDACTED]" in redacted_basic


def test_redact_text_jwt_tokens() -> None:
    jwt_token = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."  # noqa: S105
        "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0."
        "G5bX_Yj56_k7b8x9z_test_signature"
    )
    text = f"User session active: {jwt_token} inside payload"
    redacted = redact_text(text)
    assert jwt_token not in redacted
    assert "[REDACTED_JWT]" in redacted


def test_redact_text_url_credentials_and_query_secrets() -> None:
    url_text = (
        "Connecting to postgresql://admin_user:SuperSecretPassword123@db.internal:5432/kolang "
        "and https://api.upstream.mcp/v1/tools?token=sk-9999888877776666&other=valid"
    )
    redacted = redact_text(url_text)
    assert "SuperSecretPassword123" not in redacted
    assert "sk-9999888877776666" not in redacted
    assert "postgresql://admin_user:***@db.internal:5432/kolang" in redacted
    assert "token=[REDACTED]" in redacted
    assert "other=valid" in redacted


def test_redact_text_cookies_and_pii() -> None:
    cookie_str = "Cookie: session=sess_abc123xyz; token=tok_987654321; lang=en"
    redacted_cookie = redact_text(cookie_str)
    assert "sess_abc123xyz" not in redacted_cookie
    assert "tok_987654321" not in redacted_cookie
    assert "session=[REDACTED]" in redacted_cookie
    assert "token=[REDACTED]" in redacted_cookie
    assert "lang=en" in redacted_cookie

    pii_text = "Customer card 4532-1234-5678-9010 and SSN 123-45-6789"
    redacted_pii = redact_text(pii_text)
    assert "4532-1234-5678-9010" not in redacted_pii
    assert "123-45-6789" not in redacted_pii
    assert "[REDACTED_CARD]" in redacted_pii
    assert "[REDACTED_SSN]" in redacted_pii


def test_redact_headers() -> None:
    raw_headers = {
        "Host": "api.kolang.internal",
        "Authorization": "Bearer mock-secret-token",
        "X-API-Key": "sk-12345678901234567890",
        "Cookie": "session_id=mock-secret-session-id",
        "User-Agent": "Kolang-Agent/0.1.0",
        "Content-Type": "application/json",
    }
    cleaned = redact_headers(raw_headers)
    assert cleaned["Authorization"] == REDACTED_STR
    assert cleaned["X-API-Key"] == REDACTED_STR
    assert cleaned["Cookie"] == REDACTED_STR
    assert cleaned["Host"] == "api.kolang.internal"
    assert cleaned["Content-Type"] == "application/json"


def test_redact_data_nested_structures() -> None:
    nested = {
        "user_id": "usr-123",
        "credentials": {
            "password": "ClearTextPassword!",
            "api_key": "sk-live-09876543210987654321",
        },
        "tokens": ["mock-plain-string", "Bearer mock-token-embedded"],
        "metadata": {
            "env": "production",
            "auth_header": "Bearer secret_header_token",
        },
    }
    redacted = redact_data(nested)
    assert redacted["user_id"] == "usr-123"
    assert redacted["credentials"]["password"] == REDACTED_STR
    assert redacted["credentials"]["api_key"] == REDACTED_STR
    assert "ClearTextPassword!" not in str(redacted)
    assert "sk-live-09876543210987654321" not in str(redacted)
    assert "mock-token-embedded" not in str(redacted)
    assert redacted["metadata"]["auth_header"] == REDACTED_STR


def test_redact_data_pydantic_and_secrets() -> None:
    class SampleModel(BaseModel):
        name: str
        secret_field: SecretStr
        access_token: str

    model = SampleModel(
        name="test-model",
        secret_field=SecretStr("super_secret_value"),
        access_token="mock-token-abc",  # noqa: S106
    )
    redacted = redact_data(model)
    assert redacted["name"] == "test-model"
    assert redacted["secret_field"] == REDACTED_STR
    assert redacted["access_token"] == REDACTED_STR
    assert "super_secret_value" not in str(redacted)


def test_redact_data_circular_reference() -> None:
    circular_dict: dict[str, Any] = {"name": "test_node"}
    circular_dict["self_ref"] = circular_dict

    redacted = redact_data(circular_dict)
    assert redacted["name"] == "test_node"
    assert redacted["self_ref"] == "[CIRCULAR_REFERENCE]"


def test_redact_tool_payload() -> None:
    tool_call = {
        "tool_name": "execute_query",
        "arguments": {
            "query": "SELECT * FROM users",
            "db_password": "super_secret_db_pass",
        },
    }
    # Default summary mode
    summary = redact_tool_payload(tool_call, summary_only=True)
    assert summary["tool_name"] == "execute_query"
    assert summary["argument_count"] == 2
    assert "super_secret_db_pass" not in str(summary)
    assert "SELECT * FROM users" not in str(summary)

    # Detailed redacted mode
    detailed = redact_tool_payload(tool_call, summary_only=False)
    assert detailed["tool_name"] == "execute_query"
    assert detailed["arguments"]["db_password"] == REDACTED_STR
    assert "super_secret_db_pass" not in str(detailed)


def test_redact_exception() -> None:
    raw_error = ValueError(
        "Failed connecting to https://upstream.mcp?key=sk-12345678901234567890 "
        "with Bearer mock-secret-token"
    )
    redacted_msg = redact_exception(raw_error)
    assert "ValueError:" in redacted_msg
    assert "sk-12345678901234567890" not in redacted_msg
    assert "mock-secret-token" not in redacted_msg
    assert "[REDACTED]" in redacted_msg


def test_sanitize_upstream_error() -> None:
    upstream_exc = httpx.HTTPStatusError(
        message="401 Unauthorized for https://service.internal/tool?token=sk-9999888877776666",
        request=httpx.Request("GET", "https://service.internal/tool"),
        response=httpx.Response(401),
    )
    sanitized = sanitize_upstream_error(upstream_exc, request_id="req-test-999")
    assert isinstance(sanitized, UpstreamError)
    assert sanitized.code == "UPSTREAM_ERROR"
    assert sanitized.request_id == "req-test-999"
    assert "sk-9999888877776666" not in sanitized.message
    assert "token=[REDACTED]" in sanitized.message
