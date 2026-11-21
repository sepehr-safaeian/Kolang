"""
Shared request context for Kolang.

Provides request-scoped context (request_id, correlation_id) accessible
anywhere in the call stack via contextvars.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Immutable context attached to every request."""

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.correlation_id:
            object.__setattr__(self, "correlation_id", self.request_id)


_request_context: ContextVar[RequestContext | None] = ContextVar("request_context", default=None)


def get_request_context() -> RequestContext:
    """Return the current request context or raise if not set."""
    ctx = _request_context.get()
    if ctx is None:
        msg = "Request context is not set. Ensure middleware is configured."
        raise RuntimeError(msg)
    return ctx


def get_request_context_or_none() -> RequestContext | None:
    """Return the current request context, or None if not set."""
    return _request_context.get()


def set_request_context(ctx: RequestContext) -> None:
    """Set the current request context."""
    _request_context.set(ctx)


@contextmanager
def request_context_scope(
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> Generator[RequestContext, None, None]:
    """Context manager that sets and clears request context."""
    ctx = RequestContext(
        request_id=request_id or str(uuid.uuid4()),
        correlation_id=correlation_id or "",
    )
    token = _request_context.set(ctx)
    try:
        yield ctx
    finally:
        _request_context.reset(token)
