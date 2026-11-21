"""
Kolang — FastAPI application entrypoint.

Configures the application with structured logging, OpenTelemetry tracing,
CORS, request context middleware, and API routes.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from acp_core.common.settings import get_settings
from acp_core.telemetry.setup import setup_telemetry
from apps.api.app.middleware.context import RequestContextMiddleware
from apps.api.app.routers import health

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown hooks."""
    settings = get_settings()

    # ── Startup ──────────────────────────────────────────────────────────
    setup_telemetry(settings)
    logger.info(
        "kolang.startup",
        app_name=settings.app_name,
        environment=settings.app_env,
        debug=settings.app_debug,
    )

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    logger.info("kolang.shutdown")


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

    # ── Routes ───────────────────────────────────────────────────────────
    app.include_router(health.router, tags=["Health"])

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
