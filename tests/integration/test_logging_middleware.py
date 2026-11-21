"""
Integration tests for RequestContextMiddleware, structured logging, and safe exception handling.
"""

from __future__ import annotations

import contextlib
import io
import json
import logging
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from acp_core.common.errors import AuthenticationError, UpstreamError
from acp_core.telemetry.setup import setup_structlog
from apps.api.app.main import create_app


@pytest.fixture
def app_with_routes():
    """Create test application instance with deliberate error-triggering endpoints."""
    app = create_app()

    @app.get("/test/upstream-failure")
    async def route_upstream_failure() -> dict[str, str]:
        raise UpstreamError(
            message=(
                "Connection failed to http://upstream.service:8080/mcp"
                "?token=sk-live-secret-token-12345"
            ),
            details={
                "Authorization": "Bearer sample-upstream-bearer-secret",
                "upstream_host": "upstream.service",
            },
        )

    @app.get("/test/auth-failure")
    async def route_auth_failure() -> dict[str, str]:
        token_str = (
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."  # noqa: S105
            "eyJzdWIiOiIxMjM0NTY3ODkwIn0.test"
        )
        raise AuthenticationError(
            message=f"Invalid token {token_str}",
            details={"access_token": "raw-sensitive-token"},
        )

    @app.get("/test/unhandled-crash")
    async def route_unhandled_crash() -> dict[str, str]:
        raise RuntimeError("Fatal DB timeout: password 'SuperSecretDBPass!' was rejected")

    return app


@pytest.fixture
async def integration_client(app_with_routes):
    transport = ASGITransport(app=app_with_routes)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def log_capture() -> io.StringIO:
    """Fixture that captures structured log output during integration calls."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.DEBUG)

    setup_structlog(log_level="debug", service="kolang-api-test", environment="test")

    root_logger = logging.getLogger()
    old_handlers = root_logger.handlers[:]
    root_logger.addHandler(handler)

    try:
        yield stream
    finally:
        root_logger.removeHandler(handler)
        root_logger.handlers = old_handlers


def _get_log_records(stream: io.StringIO) -> list[dict[str, Any]]:
    stream.seek(0)
    lines = [line.strip() for line in stream.getvalue().splitlines() if line.strip()]
    records: list[dict[str, Any]] = []
    for line in lines:
        with contextlib.suppress(json.JSONDecodeError):
            records.append(json.loads(line))
    return records


@pytest.mark.asyncio
async def test_middleware_generates_and_propagates_ids(integration_client: AsyncClient) -> None:
    """When no request IDs are provided, middleware generates valid, matching UUID4s."""
    response = await integration_client.get("/healthz")
    assert response.status_code == 200

    req_id = response.headers.get("X-Request-ID")
    corr_id = response.headers.get("X-Correlation-ID")

    assert req_id is not None
    assert len(req_id) >= 16
    assert corr_id is not None
    assert len(corr_id) >= 16
    assert req_id == corr_id


@pytest.mark.asyncio
async def test_middleware_preserves_valid_incoming_ids(integration_client: AsyncClient) -> None:
    """Middleware preserves valid client-supplied request and correlation IDs."""
    custom_req = "req-client-12345"
    custom_corr = "corr-chain-99999"

    response = await integration_client.get(
        "/healthz",
        headers={
            "X-Request-ID": custom_req,
            "X-Correlation-ID": custom_corr,
        },
    )
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_req
    assert response.headers.get("X-Correlation-ID") == custom_corr


@pytest.mark.asyncio
async def test_middleware_sanitizes_malicious_request_ids(integration_client: AsyncClient) -> None:
    """Middleware rejects invalid/malicious request IDs (CRLF injection or excessive length)."""
    malicious_crlf_id = "req-123\r\nInjected-Header: evil"
    excessive_id = "a" * 256

    response = await integration_client.get(
        "/healthz",
        headers={"X-Request-ID": malicious_crlf_id},
    )
    assert response.status_code == 200
    cleaned_req = response.headers.get("X-Request-ID")
    assert cleaned_req is not None
    assert "\r" not in cleaned_req
    assert "\n" not in cleaned_req
    assert "Injected-Header" not in cleaned_req

    response_excessive = await integration_client.get(
        "/healthz",
        headers={"X-Request-ID": excessive_id},
    )
    assert response_excessive.status_code == 200
    cleaned_excessive = response_excessive.headers.get("X-Request-ID")
    assert len(cleaned_excessive) < 256


@pytest.mark.asyncio
async def test_middleware_does_not_log_client_tokens_or_cookies(
    integration_client: AsyncClient,
    log_capture: io.StringIO,
) -> None:
    """Client Authorization and Cookie headers must never appear in structured logs."""
    client_secret_token = "mock-secret-bearer-token-112233"  # noqa: S105
    client_session_cookie = "session_id=mock-secret-session-cookie-445566"

    response = await integration_client.get(
        "/healthz",
        headers={
            "Authorization": f"Bearer {client_secret_token}",
            "Cookie": client_session_cookie,
        },
    )
    assert response.status_code == 200

    logs_text = log_capture.getvalue()
    assert client_secret_token not in logs_text
    assert client_session_cookie not in logs_text
    assert "mock-secret-session-cookie-445566" not in logs_text


@pytest.mark.asyncio
async def test_upstream_error_endpoint_redacts_secrets_in_response_and_logs(
    integration_client: AsyncClient,
    log_capture: io.StringIO,
) -> None:
    """
    Acceptance Criteria:
    - Upstream exceptions do not leak secrets or sensitive headers.
    - Error response contains machine-readable error code and request correlation.
    """
    response = await integration_client.get("/test/upstream-failure")
    assert response.status_code == 502
    data = response.json()

    # Response structure
    assert data["error"] == "UPSTREAM_ERROR"
    assert "request_id" in data
    assert response.headers.get("X-Request-ID") is not None

    # Verify secrets are scrubbed from HTTP response body
    assert "sk-live-secret-token-12345" not in data["message"]
    assert "token=[REDACTED]" in data["message"]
    assert data["details"]["Authorization"] == "[REDACTED]"
    assert "sample-upstream-bearer-secret" not in str(data)

    # Verify secrets are scrubbed from structured logs
    logs_text = log_capture.getvalue()
    assert "sk-live-secret-token-12345" not in logs_text
    assert "sample-upstream-bearer-secret" not in logs_text

    # Log record contains error_code and correlation
    records = _get_log_records(log_capture)
    error_records = [r for r in records if r.get("level") == "error"]
    assert len(error_records) >= 1
    err_rec = error_records[-1]
    assert err_rec["error_code"] == "UPSTREAM_ERROR"
    assert err_rec["request_id"] == data["request_id"]


@pytest.mark.asyncio
async def test_auth_error_redacts_tokens(integration_client: AsyncClient) -> None:
    """Authentication errors scrub JWT tokens and credential dictionaries."""
    response = await integration_client.get("/test/auth-failure")
    assert response.status_code == 401
    data = response.json()

    assert data["error"] == "AUTHENTICATION_ERROR"
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in data["message"]
    assert data["details"]["access_token"] == "[REDACTED]"  # noqa: S105


@pytest.mark.asyncio
async def test_unhandled_crash_returns_500_without_leaking_internal_secrets(
    integration_client: AsyncClient,
    log_capture: io.StringIO,
) -> None:
    """Unhandled server errors return standardized 500 without leaking secrets to client."""
    response = await integration_client.get("/test/unhandled-crash")
    assert response.status_code == 500
    data = response.json()

    assert data["error"] == "INTERNAL_ERROR"
    assert "SuperSecretDBPass!" not in str(data)

    logs_text = log_capture.getvalue()
    # Log contains error without crashing, and secret is redacted if matched
    assert "INTERNAL_ERROR" in logs_text
