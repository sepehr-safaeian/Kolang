"""
Request context middleware for Kolang.

Assigns request_id and correlation_id to every request, binds them
to structlog context, and measures request duration.
"""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from acp_core.common.context import RequestContext, set_request_context

logger = structlog.get_logger()


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Middleware that sets request context and logs request lifecycle."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # ── Extract or generate IDs ──────────────────────────────────────
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        correlation_id = request.headers.get("X-Correlation-ID", request_id)

        # ── Set context ──────────────────────────────────────────────────
        ctx = RequestContext(request_id=request_id, correlation_id=correlation_id)
        set_request_context(ctx)

        # ── Bind to structlog ────────────────────────────────────────────
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            correlation_id=correlation_id,
        )

        logger.info(
            "request.start",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )

        # ── Process request ──────────────────────────────────────────────
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        # ── Add headers and log ──────────────────────────────────────────
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id

        logger.info(
            "request.complete",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        return response
