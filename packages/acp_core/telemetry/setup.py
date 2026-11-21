"""
Telemetry initialization for Kolang.

Configures structured JSON logging (structlog) with request correlation,
centralized redaction, standardized metadata fields, and OpenTelemetry tracing.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import structlog
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from structlog.types import EventDict, Processor, WrappedLogger

from acp_core.common.context import get_request_context_or_none
from acp_core.common.redaction import redact_data

if TYPE_CHECKING:
    from acp_core.common.settings import Settings

_tracer: trace.Tracer | None = None


def create_metadata_enricher(
    service: str,
    environment: str,
) -> Processor:
    """
    Return a structlog processor that injects standardized Kolang metadata.

    Guarantees presence of: service, environment, component, event_name,
    request_id, correlation_id, workspace_id (when authenticated), and error_code.
    """

    def processor(
        logger: WrappedLogger,
        method_name: str,
        event_dict: EventDict,
    ) -> EventDict:
        # Service and environment identifiers
        event_dict.setdefault("service", service)
        event_dict.setdefault("environment", environment)

        # Context-bound identifiers
        ctx = get_request_context_or_none()
        if ctx is not None:
            event_dict.setdefault("request_id", ctx.request_id)
            event_dict.setdefault("correlation_id", ctx.correlation_id)
            if ctx.workspace_id:
                event_dict.setdefault("workspace_id", ctx.workspace_id)

        # Component identifier (defaults to logger name or 'gateway')
        if "component" not in event_dict:
            logger_name = event_dict.get("logger")
            event_dict["component"] = logger_name if logger_name else "gateway"

        # Standardized event_name
        if "event_name" not in event_dict:
            raw_event = event_dict.get("event")
            if raw_event:
                event_dict["event_name"] = str(raw_event)
            else:
                event_dict["event_name"] = method_name

        # Extract error_code if an exception is attached
        if "error_code" not in event_dict:
            exc = event_dict.get("exception") or event_dict.get("exc_info")
            if isinstance(exc, tuple) and len(exc) > 1 and exc[1]:
                exc = exc[1]
            if exc and hasattr(exc, "code"):
                event_dict["error_code"] = str(exc.code)

        return event_dict

    return processor


def redaction_processor(
    logger: WrappedLogger,
    method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """
    Structlog processor that redacts sensitive credentials, tokens, and payloads.

    Fails safe: never raises an unhandled exception or aborts log processing.
    """
    try:
        sanitized: Any = redact_data(dict(event_dict))
        if isinstance(sanitized, dict):
            event_dict.clear()
            event_dict.update(sanitized)
            return event_dict
        return event_dict
    except Exception:
        # Emergency fallback to ensure logger never crashes the application
        return {
            "level": method_name,
            "event_name": "log_redaction_failure",
            "service": str(event_dict.get("service", "kolang")),
            "environment": str(event_dict.get("environment", "unknown")),
            "request_id": str(event_dict.get("request_id", "")),
            "correlation_id": str(event_dict.get("correlation_id", "")),
            "component": "telemetry",
            "message": "[LOG_SANITIZATION_FAILED]",
        }


def setup_structlog(
    log_level: str = "info",
    service: str = "kolang",
    environment: str = "development",
) -> None:
    """
    Configure structlog for JSON structured logging with redaction and correlation.
    """
    enricher = create_metadata_enricher(service, environment)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
            enricher,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            redaction_processor,
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
        force=True,
    )


def setup_telemetry(settings: Settings) -> trace.Tracer:
    """Initialize OpenTelemetry tracing and structured logging."""
    global _tracer

    # ── Structured logging ───────────────────────────────────────────────
    setup_structlog(
        log_level=settings.log_level,
        service=settings.app_name,
        environment=settings.env,
    )

    # ── OpenTelemetry ────────────────────────────────────────────────────
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.env,
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
            logger.warning(
                "otlp_exporter_unavailable",
                event_name="otlp.exporter_unavailable",
                component="telemetry",
                msg="OTLP exporter not installed",
            )

    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer("kolang", "0.1.0")

    return _tracer


def get_tracer() -> trace.Tracer:
    """Return the configured tracer, or a no-op tracer if not initialized."""
    if _tracer is None:
        return trace.get_tracer("kolang", "0.1.0")
    return _tracer
