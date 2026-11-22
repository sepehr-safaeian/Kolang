"""
Error hierarchy for Kolang.

All application errors inherit from KolangError, providing consistent
error codes, messages, and serialization for API responses.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class KolangError(Exception):
    """Base exception for all Kolang errors."""

    code: str = "KOLANG_ERROR"
    status_code: int = 500

    def __init__(
        self,
        message: str = "An unexpected error occurred.",
        *,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.request_id = request_id


class ValidationError(KolangError):
    code = "VALIDATION_ERROR"
    status_code = 422


class AuthenticationError(KolangError):
    code = "AUTHENTICATION_ERROR"
    status_code = 401


class AuthorizationError(KolangError):
    code = "AUTHORIZATION_ERROR"
    status_code = 403


class NotFoundError(KolangError):
    code = "NOT_FOUND"
    status_code = 404


class ConflictError(KolangError):
    code = "CONFLICT"
    status_code = 409


class PolicyVersionImmutableError(ConflictError):
    """Raised when an attempt is made to mutate an immutable published policy version."""

    code = "POLICY_VERSION_IMMUTABLE"
    status_code = 409


class RateLimitError(KolangError):
    code = "RATE_LIMIT_EXCEEDED"
    status_code = 429


class UpstreamError(KolangError):
    code = "UPSTREAM_ERROR"
    status_code = 502


class InternalError(KolangError):
    code = "INTERNAL_ERROR"
    status_code = 500


class PayloadTooLargeError(KolangError):
    code = "PAYLOAD_TOO_LARGE"
    status_code = 413


class UpstreamTimeoutError(KolangError):
    code = "TIMEOUT"
    status_code = 504


class DatabaseError(KolangError):
    """Raised when a database operation fails."""

    code = "DATABASE_ERROR"
    status_code = 500

    def __init__(
        self,
        message: str = "A database error occurred.",
        *,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message, details=details, request_id=request_id)


class DatabaseConnectionError(DatabaseError):
    """Raised when connection to the database cannot be established."""

    code = "DATABASE_CONNECTION_ERROR"
    status_code = 503

    def __init__(
        self,
        message: str = "Database service is currently unavailable.",
        *,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message, details=details, request_id=request_id)


class ConfigurationError(KolangError):
    """Raised when runtime configuration or environment variables are invalid or missing."""

    code = "CONFIGURATION_ERROR"
    status_code = 500


# Backward-compatible alias
TimeoutError = UpstreamTimeoutError  # noqa: A001


# ── API Error Response Model ─────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    """Standardized error response for the Kolang API."""

    error: str = Field(description="Machine-readable error code")
    message: str = Field(description="Human-readable error message")
    details: dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    request_id: str | None = Field(default=None, description="Request ID for tracing")

    @classmethod
    def from_error(cls, err: KolangError) -> ErrorResponse:
        return cls(
            error=err.code,
            message=err.message,
            details=err.details,
            request_id=err.request_id,
        )
