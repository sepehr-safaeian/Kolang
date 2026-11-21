"""
Health check endpoints for Kolang.

Provides liveness (/healthz) and readiness (/readyz) probes
for orchestrator health monitoring.
"""

from __future__ import annotations

from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = structlog.get_logger()

router = APIRouter()


class HealthResponse(BaseModel):
    status: str


class ReadinessCheck(BaseModel):
    database: str
    timestamp: str


class ReadinessResponse(BaseModel):
    status: str
    checks: ReadinessCheck


@router.get(
    "/healthz",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns 200 if the service is alive.",
)
async def liveness() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get(
    "/readyz",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Returns 200 if the service is ready to accept traffic.",
)
async def readiness() -> JSONResponse:
    checks: dict[str, str] = {}
    all_ok = True

    # ── Database check ───────────────────────────────────────────────────
    try:
        # TODO: Replace with actual async database ping when DB is configured
        checks["database"] = "ok"
    except Exception:
        logger.warning("readiness.database_check_failed", exc_info=True)
        checks["database"] = "unavailable"
        all_ok = False

    checks["timestamp"] = datetime.now(UTC).isoformat()

    if all_ok:
        return JSONResponse(
            content={"status": "ready", "checks": checks},
            status_code=status.HTTP_200_OK,
        )
    return JSONResponse(
        content={"status": "degraded", "checks": checks},
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    )
