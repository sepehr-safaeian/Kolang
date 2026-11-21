"""
Telemetry initialization for Kolang.

Configures structured logging (structlog) and OpenTelemetry tracing
with OTLP export.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import structlog
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

if TYPE_CHECKING:
    from acp_core.common.settings import Settings

_tracer: trace.Tracer | None = None


def setup_structlog(log_level: str = "info") -> None:
    """Configure structlog for JSON structured logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper(), logging.INFO),
    )


def setup_telemetry(settings: Settings) -> trace.Tracer:
    """Initialize OpenTelemetry tracing and structured logging."""
    global _tracer

    # ── Structured logging ───────────────────────────────────────────────
    setup_structlog(settings.app_log_level)

    # ── OpenTelemetry ────────────────────────────────────────────────────
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.app_env,
        }
    )

    provider = TracerProvider(resource=resource)

    if settings.otel_exporter_endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
        except ImportError:
            logger = structlog.get_logger()
            logger.warning("otlp_exporter_unavailable", msg="OTLP exporter not installed")

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("kolang", "0.1.0")

    return _tracer


def get_tracer() -> trace.Tracer:
    """Return the configured tracer, or a no-op tracer if not initialized."""
    if _tracer is None:
        return trace.get_tracer("kolang", "0.1.0")
    return _tracer
