"""
Kolang — FastAPI application entrypoint.

Configures the application with structured logging, OpenTelemetry tracing,
CORS, request context middleware, global safe exception handling, and API routes.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError
from starlette.requests import Request
from starlette.responses import JSONResponse

from acp_core.common.context import get_request_context_or_none
from acp_core.common.errors import KolangError
from acp_core.common.redaction import redact_data, redact_exception, redact_text
from acp_core.common.settings import get_settings
from acp_core.db import close_db, init_db, ping_db
from acp_core.telemetry.setup import setup_telemetry
from apps.api.app.middleware.context import RequestContextMiddleware
from apps.api.app.routers import health, servers, workspaces

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    settings = get_settings()

    # ── Startup ──────────────────────────────────────────────────────────
    setup_telemetry(settings)
    logger.info(
        "kolang.startup",
        event_name="kolang.startup",
        component="lifecycle",
        app_name=settings.app_name,
        environment=settings.env,
        debug=settings.app_debug,
        log_level=settings.log_level,
        request_timeout_seconds=settings.request_timeout_seconds,
        max_request_body_bytes=settings.max_request_body_bytes,
        allowed_upstream_hosts=settings.allowed_upstream_hosts,
    )

    await init_db(settings)
    db_healthy = await ping_db()
    if db_healthy:
        logger.info(
            "database.connected",
            event_name="database.connected",
            component="database",
        )
    else:
        logger.warning(
            "database.unreachable",
            event_name="database.unreachable",
            component="database",
            message="Database ping failed during application startup.",
        )

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    await close_db()
    logger.info(
        "kolang.shutdown",
        event_name="kolang.shutdown",
        component="lifecycle",
    )


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title="Kolang",
        description=(
            "Open-source Agent Control Plane and MCP Gateway for secure, "
            "governed access to AI tool infrastructure."
        ),
        version="0.1.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # ── Middleware (order matters: outermost first) ───────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    # ── Safe Exception Handlers ──────────────────────────────────────────
    @app.exception_handler(KolangError)
    async def handle_kolang_error(request: Request, exc: KolangError) -> JSONResponse:
        ctx = get_request_context_or_none()
        req_id = ctx.request_id if ctx else (exc.request_id or "")
        corr_id = ctx.correlation_id if ctx else req_id

        safe_message = redact_text(exc.message)
        safe_details = redact_data(exc.details)

        logger.error(
            "request.error",
            event_name="request.error",
            component="api",
            error_code=exc.code,
            status_code=exc.status_code,
            message=safe_message,
        )

        headers: dict[str, str] = {}
        if req_id:
            headers["X-Request-ID"] = req_id
        if corr_id:
            headers["X-Correlation-ID"] = corr_id

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.code,
                "message": safe_message,
                "details": safe_details,
                "request_id": req_id or None,
            },
            headers=headers,
        )

    @app.exception_handler(SQLAlchemyError)
    async def handle_sqlalchemy_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        ctx = get_request_context_or_none()
        req_id = ctx.request_id if ctx else ""
        corr_id = ctx.correlation_id if ctx else req_id

        safe_err_str = redact_exception(exc)

        logger.error(
            "request.database_error",
            event_name="request.database_error",
            component="database",
            error_code="DATABASE_ERROR",
            status_code=500,
            error=safe_err_str,
        )

        headers: dict[str, str] = {}
        if req_id:
            headers["X-Request-ID"] = req_id
        if corr_id:
            headers["X-Correlation-ID"] = corr_id

        return JSONResponse(
            status_code=500,
            content={
                "error": "DATABASE_ERROR",
                "message": "A database error occurred.",
                "details": {},
                "request_id": req_id or None,
            },
            headers=headers,
        )

    @app.exception_handler(Exception)
    async def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
        ctx = get_request_context_or_none()
        req_id = ctx.request_id if ctx else ""
        corr_id = ctx.correlation_id if ctx else req_id

        safe_err_str = redact_exception(exc)

        logger.error(
            "request.unhandled_exception",
            event_name="request.unhandled_exception",
            component="api",
            error_code="INTERNAL_ERROR",
            status_code=500,
            error=safe_err_str,
        )

        headers: dict[str, str] = {}
        if req_id:
            headers["X-Request-ID"] = req_id
        if corr_id:
            headers["X-Correlation-ID"] = corr_id

        return JSONResponse(
            status_code=500,
            content={
                "error": "INTERNAL_ERROR",
                "message": "An internal server error occurred.",
                "details": {},
                "request_id": req_id or None,
            },
            headers=headers,
        )

    # ── Routes ───────────────────────────────────────────────────────────
    app.include_router(health.router, tags=["Health"])
    app.include_router(workspaces.router)
    app.include_router(servers.router)

    @app.get("/", tags=["Root"])
    async def root() -> dict[str, str]:
        return {
            "name": "Kolang",
            "version": "0.1.0",
            "description": "Agent Control Plane & MCP Gateway",
            "docs": "/api/docs",
        }

    return app


app = create_app()
