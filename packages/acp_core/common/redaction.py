"""
Central Redaction Utility for Kolang.

Provides comprehensive data sanitization and masking for logs, exceptions,
request contexts, and upstream error reporting. Guarantees that credentials,
tokens, passwords, authorization headers, and unnecessary sensitive information
are never leaked in structured logs, traces, or API responses.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from typing import Any

from acp_core.common.errors import UpstreamError

# ── Redaction Constants ───────────────────────────────────────────────────────

REDACTED_STR = "[REDACTED]"
REDACTED_PASSWORD = "***"  # noqa: S105
REDACTED_PAYLOAD_TRUNCATED = "[TRUNCATED]"

# Sensitive key names (case-insensitive substring or normalized match)
SENSITIVE_KEY_NAMES: frozenset[str] = frozenset(
    {
        "authorization",
        "proxy_authorization",
        "proxy-authorization",
        "access_token",
        "refresh_token",
        "id_token",
        "token",
        "secret",
        "client_secret",
        "password",
        "passwd",
        "api_key",
        "apikey",
        "x_api_key",
        "x-api-key",
        "private_key",
        "privatekey",
        "credential",
        "credentials",
        "cookie",
        "set_cookie",
        "set-cookie",
        "session",
        "session_id",
        "sessionid",
        "auth",
        "bearer",
        "secret_key",
        "encryption_key",
    }
)

# ── Regular Expression Redaction Patterns ─────────────────────────────────────

# Bearer token pattern: Bearer <token>
RE_BEARER = re.compile(r"(Bearer\s+)[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)

# Basic auth pattern: Basic <base64>
RE_BASIC = re.compile(r"(Basic\s+)[A-Za-z0-9+/=]+", re.IGNORECASE)

# JWT token pattern (three base64url segments separated by dots)
RE_JWT = re.compile(
    r"\beyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b",
    re.IGNORECASE,
)

# Passwords/credentials embedded in connection URLs (e.g. proto://user:pass@host)
RE_URL_CREDENTIALS = re.compile(r"(://[^:@\s]+):([^@\s]+)@")

# Sensitive URL query parameters (e.g., ?token=..., &api_key=..., &secret=...)
RE_URL_SENSITIVE_QUERY = re.compile(
    r"([?&](?:token|access_token|refresh_token|api_key|apikey|secret|password|passwd|key)=)[^&\s]+",
    re.IGNORECASE,
)

# API key patterns (e.g., sk-..., kolang-..., ghp_..., etc.)
RE_API_KEY = re.compile(
    r"\b(?:sk|pk|key|kolang|ghp|gho|xoxb|xoxp)-[A-Za-z0-9_\-]{16,}\b",
    re.IGNORECASE,
)

# Cookie key-value pairs (stops at semicolon, whitespace, or ampersand)
RE_COOKIE_VALUE = re.compile(
    r"((?:session|token|access_token|refresh_token|auth|sessionId)=)[^;\s&]+",
    re.IGNORECASE,
)

# Credit card numbers (13-19 digits formatted or unformatted)
RE_CREDIT_CARD = re.compile(r"\b(?:\d{4}[- ]?){3}\d{4}\b|\b\d{13,19}\b")

# Social Security Numbers (US format: 000-00-0000)
RE_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


# ── Inspection Helpers ────────────────────────────────────────────────────────


def is_sensitive_key(key: str) -> bool:
    """
    Check if a dictionary key or field name matches known sensitive keywords.

    Normalizes the key by stripping spaces, lowering case, and converting
    hyphens to underscores.
    """
    if not isinstance(key, str):
        return False
    normalized = key.strip().lower().replace("-", "_")
    if normalized in SENSITIVE_KEY_NAMES:
        return True
    return any(sensitive in normalized for sensitive in SENSITIVE_KEY_NAMES)


def redact_text(text: str) -> str:
    """
    Scrub sensitive credentials, tokens, JWTs, and keys from a string.

    This function is completely exception-safe: if any error occurs, it returns
    a safe fallback rather than crashing the caller.
    """
    if not text or not isinstance(text, str):
        return ""

    try:
        # 1. Redact URL credentials (protocol://user:password@host -> protocol://user:***@host)
        sanitized = RE_URL_CREDENTIALS.sub(r"\1:***@", text)

        # 2. Redact sensitive query parameters (?token=... -> ?token=[REDACTED])
        sanitized = RE_URL_SENSITIVE_QUERY.sub(r"\1[REDACTED]", sanitized)

        # 3. Redact Authorization Bearer headers
        sanitized = RE_BEARER.sub(r"\1[REDACTED]", sanitized)

        # 4. Redact Authorization Basic headers
        sanitized = RE_BASIC.sub(r"\1[REDACTED]", sanitized)

        # 5. Redact JWT tokens
        sanitized = RE_JWT.sub("[REDACTED_JWT]", sanitized)

        # 6. Redact identifiable API keys
        sanitized = RE_API_KEY.sub("[REDACTED_API_KEY]", sanitized)

        # 7. Redact cookie pairs
        sanitized = RE_COOKIE_VALUE.sub(r"\1[REDACTED]", sanitized)

        # 8. Redact credit card patterns (check length > 12)
        sanitized = RE_CREDIT_CARD.sub("[REDACTED_CARD]", sanitized)

        # 9. Redact SSN
        return RE_SSN.sub("[REDACTED_SSN]", sanitized)
    except Exception:
        return REDACTED_STR


def redact_headers(headers: Mapping[str, Any] | Iterable[tuple[str, Any]]) -> dict[str, str]:
    """
    Scrub sensitive HTTP headers such as Authorization, Cookie, and API keys.

    Any header with a sensitive name is completely replaced with [REDACTED].
    Other header values are filtered through text pattern redaction.
    """
    clean_headers: dict[str, str] = {}
    if not headers:
        return clean_headers

    items: Iterable[tuple[str, Any]] = headers.items() if isinstance(headers, Mapping) else headers

    for raw_k, raw_v in items:
        k = str(raw_k)
        v = str(raw_v)
        if is_sensitive_key(k):
            clean_headers[k] = REDACTED_STR
        else:
            clean_headers[k] = redact_text(v)

    return clean_headers


def redact_data(
    data: Any,
    *,
    max_depth: int = 5,
    max_string_length: int = 500,
    seen: set[int] | None = None,
) -> Any:
    """
    Recursively sanitize arbitrary data structures (dicts, lists, tuples, models).

    - Keys matching sensitive names have their primitive values replaced with [REDACTED].
    - Container values (dicts, lists) under sensitive keys are recursively redacted.
    - String values are scanned for embedded tokens, credentials, and cards.
    - Large strings are truncated safely to prevent log flooding.
    - Circular references and deep nesting are handled safely.
    """
    if seen is None:
        seen = set()

    if max_depth <= 0:
        return "[MAX_DEPTH_REACHED]"

    # Handle None, primitives
    if data is None or isinstance(data, (int, float, bool)):
        return data

    # Handle strings
    if isinstance(data, str):
        sanitized = redact_text(data)
        if len(sanitized) > max_string_length:
            return sanitized[:max_string_length] + " " + REDACTED_PAYLOAD_TRUNCATED
        return sanitized

    # Handle SecretStr or similar objects
    if hasattr(data, "get_secret_value"):
        return REDACTED_STR

    # Cycle detection
    obj_id = id(data)
    if obj_id in seen:
        return "[CIRCULAR_REFERENCE]"

    seen_next = seen | {obj_id}

    # Handle Pydantic models
    if hasattr(data, "model_dump") and callable(data.model_dump):
        try:
            return redact_data(
                data.model_dump(),
                max_depth=max_depth - 1,
                max_string_length=max_string_length,
                seen=seen_next,
            )
        except Exception:
            return REDACTED_STR

    # Handle Dictionaries / Mappings
    if isinstance(data, Mapping):
        clean_dict: dict[str, Any] = {}
        for key, val in data.items():
            k_str = str(key)
            if is_sensitive_key(k_str):
                # If the value is a nested collection, recurse to preserve structure
                # while redacting sensitive leaves
                if isinstance(val, (Mapping, list, tuple, set)) or hasattr(val, "model_dump"):
                    clean_dict[k_str] = redact_data(
                        val,
                        max_depth=max_depth - 1,
                        max_string_length=max_string_length,
                        seen=seen_next,
                    )
                else:
                    clean_dict[k_str] = REDACTED_STR
            else:
                clean_dict[k_str] = redact_data(
                    val,
                    max_depth=max_depth - 1,
                    max_string_length=max_string_length,
                    seen=seen_next,
                )
        return clean_dict

    # Handle Lists & Tuples
    if isinstance(data, (list, tuple)):
        clean_list = [
            redact_data(
                item,
                max_depth=max_depth - 1,
                max_string_length=max_string_length,
                seen=seen_next,
            )
            for item in data
        ]
        return tuple(clean_list) if isinstance(data, tuple) else clean_list

    # Handle Sets
    if isinstance(data, set):
        return [
            redact_data(
                item,
                max_depth=max_depth - 1,
                max_string_length=max_string_length,
                seen=seen_next,
            )
            for item in data
        ]

    # Handle arbitrary objects via string representation
    try:
        return redact_text(str(data))
    except Exception:
        return REDACTED_STR


def redact_tool_payload(
    payload: Any,
    *,
    summary_only: bool = True,
    max_arg_length: int = 250,
) -> Any:
    """
    Sanitize tool invocation request or response payloads.

    By default (`summary_only=True`), never logs full payloads raw. Instead,
    produces a minimal safe summary (tool name, argument keys count, and safe types).
    If full payload is required, all arguments and secrets are deeply redacted.
    """
    if payload is None:
        return None

    if summary_only:
        if isinstance(payload, Mapping):
            tool_name = payload.get("tool_name") or payload.get("name")
            args = payload.get("arguments") or payload.get("args") or {}
            arg_keys = list(args.keys()) if isinstance(args, Mapping) else []
            return {
                "tool_name": tool_name,
                "argument_keys": arg_keys,
                "argument_count": len(arg_keys),
            }
        return {"payload_type": type(payload).__name__}

    return redact_data(payload, max_string_length=max_arg_length)


def redact_exception(exc: BaseException) -> str:
    """
    Extract and sanitize the string representation of an exception.

    Ensures that any secrets, URLs with credentials, bearer tokens, or sensitive
    headers embedded in the exception message are thoroughly redacted.
    """
    if exc is None:
        return ""
    try:
        raw_msg = f"{type(exc).__name__}: {exc}"
        return redact_text(raw_msg)
    except Exception:
        return "Exception: [REDACTED_DUE_TO_ERROR]"


def sanitize_upstream_error(
    exc: Exception,
    *,
    request_id: str | None = None,
    default_message: str = "Upstream MCP service invocation failed.",
) -> UpstreamError:
    """
    Convert an upstream exception into a safe, redacted UpstreamError.

    Strips any raw tokens, secrets, or sensitive headers from the exception
    message and details dictionary before returning.
    """
    safe_msg = redact_text(str(exc)) if str(exc) else default_message
    details: dict[str, Any] = {}

    if hasattr(exc, "details") and isinstance(exc.details, dict):
        details = redact_data(exc.details)
    else:
        details = {"original_error_type": type(exc).__name__}

    return UpstreamError(
        message=safe_msg,
        details=details,
        request_id=request_id,
    )
