"""
Unit tests for structured logging, request correlation, and redaction in Kolang.
"""

from __future__ import annotations

import contextlib
import io
import json
import logging
from typing import Any

import pytest
import structlog

from acp_core.common.context import (
    RequestContext,
    request_context_scope,
    set_request_context,
    set_request_workspace_id,
)
from acp_core.common.errors import UpstreamError
from acp_core.telemetry.setup import setup_structlog


@pytest.fixture
def log_capture() -> io.StringIO:
    """Fixture that captures logging output into an in-memory stream."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setLevel(logging.DEBUG)

    # Initialize structlog first
    setup_structlog(log_level="debug", service="kolang-test", environment="test")

    root_logger = logging.getLogger()
    old_handlers = root_logger.handlers[:]
    root_logger.addHandler(handler)

    try:
        yield stream
    finally:
        root_logger.removeHandler(handler)
        root_logger.handlers = old_handlers


def _get_log_records(stream: io.StringIO) -> list[dict[str, Any]]:
    """Parse JSON log lines from captured stream."""
    stream.seek(0)
    lines = [line.strip() for line in stream.getvalue().splitlines() if line.strip()]
    records: list[dict[str, Any]] = []
    for line in lines:
        with contextlib.suppress(json.JSONDecodeError):
            records.append(json.loads(line))
    return records


def test_structured_json_fields_present(log_capture: io.StringIO) -> None:
    """Verify that all mandatory structured log fields are present in emitted JSON."""
    logger = structlog.get_logger("test_component")

    with request_context_scope(
        request_id="req-unit-123",
        correlation_id="corr-unit-456",
        workspace_id="ws-enterprise-99",
    ):
        logger.info(
            "test.event",
            event_name="test.event",
            component="gateway_test",
            action="verify_fields",
        )

    records = _get_log_records(log_capture)
    assert len(records) >= 1
    record = records[-1]

    # Required structured fields
    assert "timestamp" in record
    assert record["level"] == "info"
    assert record["service"] == "kolang-test"
    assert record["environment"] == "test"
    assert record["request_id"] == "req-unit-123"
    assert record["correlation_id"] == "corr-unit-456"
    assert record["workspace_id"] == "ws-enterprise-99"
    assert record["component"] == "gateway_test"
    assert record["event_name"] == "test.event"


def test_request_correlation_across_context(log_capture: io.StringIO) -> None:
    """Verify request_id and correlation_id propagate across log events."""
    logger = structlog.get_logger("correlation_checker")

    ctx = RequestContext(request_id="req-trace-001", correlation_id="chain-xyz-888")
    set_request_context(ctx)

    logger.info("step.one", event_name="step.one")
    set_request_workspace_id("ws-tenant-alpha")
    logger.info("step.two", event_name="step.two")

    records = _get_log_records(log_capture)
    assert len(records) >= 2

    # Verify step one
    rec1 = records[-2]
    assert rec1["request_id"] == "req-trace-001"
    assert rec1["correlation_id"] == "chain-xyz-888"

    # Verify step two retains correlation and includes workspace_id
    rec2 = records[-1]
    assert rec2["request_id"] == "req-trace-001"
    assert rec2["correlation_id"] == "chain-xyz-888"
    assert rec2["workspace_id"] == "ws-tenant-alpha"


def test_tokens_and_secrets_never_appear_in_logs(log_capture: io.StringIO) -> None:
    """
    Acceptance Criterion:
    A dedicated test proves sample tokens and secrets NEVER appear in logs.
    """
    logger = structlog.get_logger("security_redaction_test")

    sample_token = "mock-secret-access-token-999888"  # noqa: S105
    sample_api_key = "sk-live-secret-key-1234567890123456"
    sample_password = "SuperSecretPassword123!"  # noqa: S105
    sample_cookie = "mock_session_id_456"
    sample_jwt = (
        "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIn0."
        "G5bX_Yj56_k7b8x9z_test_signature"
    )

    with request_context_scope(request_id="req-sec-01", correlation_id="corr-sec-01"):
        logger.info(
            "authentication_attempt",
            event_name="auth.attempt",
            authorization=f"Bearer {sample_token}",
            api_key=sample_api_key,
            password=sample_password,
            cookie=f"session={sample_cookie}",
            jwt_token=sample_jwt,
            details={
                "client_secret": "raw-client-secret-to-redact",
                "nested_token": sample_token,
            },
        )

    log_output = log_capture.getvalue()

    # None of the raw sensitive values must appear anywhere in the output
    assert sample_token not in log_output
    assert sample_api_key not in log_output
    assert sample_password not in log_output
    assert sample_cookie not in log_output
    assert sample_jwt not in log_output
    assert "raw-client-secret-to-redact" not in log_output

    # Structured JSON must still be valid
    records = _get_log_records(log_capture)
    assert len(records) >= 1
    record = records[-1]
    assert record["authorization"] == "[REDACTED]"
    assert record["api_key"] == "[REDACTED]"
    assert record["password"] == "[REDACTED]"  # noqa: S105
    assert record["details"]["client_secret"] == "[REDACTED]"  # noqa: S105
    assert record["details"]["nested_token"] == "[REDACTED]"  # noqa: S105


def test_upstream_exceptions_do_not_leak_secrets(log_capture: io.StringIO) -> None:
    """
    Acceptance Criterion:
    Upstream exceptions do not leak secrets, credentials, or sensitive headers.
    """
    logger = structlog.get_logger("upstream_service")

    secret_in_url = "super_secret_upstream_password"  # noqa: S105
    secret_api_key = "sk-upstreamkey1234567890123456"  # noqa: S105
    secret_header_val = "mock-upstream-auth-token-777"  # noqa: S105

    upstream_exc = UpstreamError(
        message=(
            f"Failed calling upstream at http://admin:{secret_in_url}@mcp-upstream.internal:8000/call"
            f"?api_key={secret_api_key}"
        ),
        details={
            "Authorization": f"Bearer {secret_header_val}",
            "endpoint": "http://mcp-upstream.internal",
        },
        request_id="req-upstream-001",
    )

    with request_context_scope(request_id="req-upstream-001"):
        logger.error(
            "upstream_call_failed",
            event_name="upstream.call_failed",
            component="upstream_client",
            error_code=upstream_exc.code,
            exc_info=upstream_exc,
        )

    log_output = log_capture.getvalue()

    # Secrets must not leak
    assert secret_in_url not in log_output
    assert secret_api_key not in log_output
    assert secret_header_val not in log_output

    records = _get_log_records(log_capture)
    assert len(records) >= 1
    record = records[-1]
    assert record["error_code"] == "UPSTREAM_ERROR"
    assert record["component"] == "upstream_client"
    assert record["event_name"] == "upstream.call_failed"


def test_logging_never_crashes_on_pathological_inputs(log_capture: io.StringIO) -> None:
    """
    Acceptance Criterion:
    Logging does not alter behavior or crash the application on edge cases,
    unhashable objects, deep nesting, or circular references.
    """
    logger = structlog.get_logger("resilience_test")

    # Pathological circular reference
    circular: dict[str, Any] = {"a": 1}
    circular["loop"] = circular

    # Extremely deep nesting
    deep: dict[str, Any] = {}
    current = deep
    for i in range(20):
        current["sub"] = {"level": i}
        current = current["sub"]

    # Giant string
    giant_string = "A" * 10000

    # These must execute without raising any exception
    logger.info("circular_test", circular=circular)
    logger.info("deep_nesting_test", deep=deep)
    logger.info("giant_string_test", giant=giant_string)
    logger.info("none_test", empty_val=None, empty_dict={})

    records = _get_log_records(log_capture)
    assert len(records) >= 4
