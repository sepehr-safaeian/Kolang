"""
Request context middleware for Kolang.

Assigns, validates, and propagates request_id, correlation_id, and workspace_id
across the entire request lifecycle, binds them to structlog context, and
safely logs request lifecycle metrics without exposing sensitive headers or tokens.
"""

from __future__ import annotations

import time

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from acp_core.common.context import (
    RequestContext,
    sanitize_correlation_id,
    sanitize_request_id,
    set_request_context,
)
from acp_core.common.redaction import redact_data, redact_exception, redact_text

logger = structlog.get_logger()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware that sets validated request context and logs request lifecycle."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # ── Extract and sanitize IDs ─────────────────────────────────────
        raw_req_id = request.headers.get("X-Request-ID")
        raw_corr_id = request.headers.get("X-Correlation-ID")
        raw_workspace_id = request.headers.get("X-Workspace-ID")

        request_id = sanitize_request_id(raw_req_id)
        correlation_id = sanitize_correlation_id(raw_corr_id, fallback=request_id)
        workspace_id = sanitize_correlation_id(raw_workspace_id) if raw_workspace_id else None

        # ── Initialize context ───────────────────────────────────────────
        ctx = RequestContext(
            request_id=request_id,
            correlation_id=correlation_id,
            workspace_id=workspace_id,
            client_id=request.client.host if request.client else None,
        )
        set_request_context(ctx)

        # ── Bind context to structlog ────────────────────────────────────
        structlog.contextvars.clear_contextvars()
        bind_kwargs: dict[str, str] = {
            "request_id": request_id,
            "correlation_id": correlation_id,
            "component": "middleware",
        }
        if workspace_id:
            bind_kwargs["workspace_id"] = workspace_id
        structlog.contextvars.bind_contextvars(**bind_kwargs)

        # ── Log request arrival safely (no raw headers or tokens) ────────
        logger.info(
            "request.start",
            event_name="request.start",
            component="middleware",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )

        # ── Process request with timing and exception safety ─────────────
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            error_code = getattr(exc, "code", "INTERNAL_ERROR")
            status_code = getattr(exc, "status_code", 500)
            safe_err = redact_exception(exc)

            logger.error(
                "request.failed",
                event_name="request.failed",
                component="middleware",
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
                error_code=error_code,
                error=safe_err,
            )

            # Defensive fail-safe: Ensure application never crashes or leaks raw traceback
            safe_msg = (
                "An internal server error occurred."
                if status_code == 500
                else redact_text(str(exc))
            )
            raw_details = getattr(exc, "details", {})
            safe_details = redact_data(raw_details) if isinstance(raw_details, dict) else {}

            return JSONResponse(
                status_code=status_code,
                content={
                    "error": error_code,
                    "message": safe_msg,
                    "details": safe_details,
                    "request_id": request_id,
                },
                headers={
                    "X-Request-ID": request_id,
                    "X-Correlation-ID": correlation_id,
                },
            )

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        # ── Attach response headers ──────────────────────────────────────
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id

        # ── Log request completion ───────────────────────────────────────
        logger.info(
            "request.complete",
            event_name="request.complete",
            component="middleware",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response
