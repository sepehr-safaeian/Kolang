"""
Shared request context for Kolang.

Provides request-scoped context (request_id, correlation_id, workspace_id)
accessible anywhere in the call stack via contextvars and structlog.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

# Safe identifier pattern: alphanumeric, hyphen, underscore, dot (1-128 chars)
ID_SAFE_PATTERN = re.compile(r"^[a-zA-Z0-9_\-\.]{1,128}$")


def sanitize_request_id(id_val: str | None) -> str:
    """
    Validate and return an incoming request ID, or generate a fresh UUID4.

    Rejects empty strings, strings exceeding 128 characters, or strings
    containing invalid control characters / newlines to prevent header and
    log injection attacks.
    """
    if id_val and isinstance(id_val, str):
        cleaned = id_val.strip()
        if ID_SAFE_PATTERN.match(cleaned):
            return cleaned
    return str(uuid.uuid4())


def sanitize_correlation_id(id_val: str | None, *, fallback: str | None = None) -> str:
    """
    Validate and return an incoming correlation ID, or fall back to request ID / fresh UUID4.
    """
    if id_val and isinstance(id_val, str):
        cleaned = id_val.strip()
        if ID_SAFE_PATTERN.match(cleaned):
            return cleaned
    return fallback or str(uuid.uuid4())


@dataclass(frozen=True, slots=True)
class RequestContext:
    """Immutable context attached to every request."""

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    workspace_id: str | None = None
    client_id: str | None = None
    principal: Any | None = None

    def __post_init__(self) -> None:
        if not self.correlation_id:
            object.__setattr__(self, "correlation_id", self.request_id)
        if self.principal is not None and not self.workspace_id:
            # Automatically derive tenant workspace scope from the verified Principal
            p_ws = getattr(self.principal, "workspace_id", None)
            if p_ws:
                object.__setattr__(self, "workspace_id", str(p_ws))


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


def get_request_principal_or_none() -> Any | None:
    """Return the current verified principal attached to request context, or None."""
    ctx = _request_context.get()
    return ctx.principal if ctx is not None else None


def set_request_context(ctx: RequestContext) -> None:
    """Set the current request context and bind identifiers to structlog."""
    _request_context.set(ctx)
    bind_kwargs: dict[str, str] = {
        "request_id": ctx.request_id,
        "correlation_id": ctx.correlation_id,
    }
    if ctx.workspace_id:
        bind_kwargs["workspace_id"] = ctx.workspace_id
    if ctx.principal is not None:
        p_id = getattr(ctx.principal, "id", None)
        if p_id:
            bind_kwargs["principal_id"] = str(p_id)
    structlog.contextvars.bind_contextvars(**bind_kwargs)


def set_request_principal(principal: Any) -> None:
    """
    Bind a verified Principal to the active request context.

    Automatically extracts and binds the tenant workspace_id from the Principal,
    enforcing that the RequestContext workspace scope always aligns with identity.
    """
    current = get_request_context_or_none()
    derived_workspace_id = str(getattr(principal, "workspace_id", "")) or None
    principal_id = str(getattr(principal, "id", "")) or None

    if current is not None:
        new_ctx = RequestContext(
            request_id=current.request_id,
            correlation_id=current.correlation_id,
            timestamp=current.timestamp,
            workspace_id=derived_workspace_id or current.workspace_id,
            client_id=current.client_id,
            principal=principal,
        )
        _request_context.set(new_ctx)
    else:
        new_ctx = RequestContext(
            workspace_id=derived_workspace_id,
            principal=principal,
        )
        _request_context.set(new_ctx)

    bind_kwargs: dict[str, str] = {}
    if derived_workspace_id:
        bind_kwargs["workspace_id"] = derived_workspace_id
    if principal_id:
        bind_kwargs["principal_id"] = principal_id
    if bind_kwargs:
        structlog.contextvars.bind_contextvars(**bind_kwargs)


def set_request_workspace_id(workspace_id: str | None) -> None:
    """
    Update the workspace_id on the active request context and bind to structlog.
    """
    current = get_request_context_or_none()
    if current is not None:
        new_ctx = RequestContext(
            request_id=current.request_id,
            correlation_id=current.correlation_id,
            timestamp=current.timestamp,
            workspace_id=workspace_id,
            client_id=current.client_id,
            principal=current.principal,
        )
        _request_context.set(new_ctx)

    if workspace_id:
        structlog.contextvars.bind_contextvars(workspace_id=workspace_id)
    else:
        structlog.contextvars.unbind_contextvars("workspace_id")


@contextmanager
def request_context_scope(
    request_id: str | None = None,
    correlation_id: str | None = None,
    workspace_id: str | None = None,
    client_id: str | None = None,
    principal: Any | None = None,
) -> Generator[RequestContext, None, None]:
    """Context manager that sets and clears request context."""
    req_id = sanitize_request_id(request_id)
    corr_id = sanitize_correlation_id(correlation_id, fallback=req_id)
    derived_ws = workspace_id
    if principal is not None and not derived_ws:
        p_ws = getattr(principal, "workspace_id", None)
        if p_ws:
            derived_ws = str(p_ws)

    ctx = RequestContext(
        request_id=req_id,
        correlation_id=corr_id,
        workspace_id=derived_ws,
        client_id=client_id,
        principal=principal,
    )
    token = _request_context.set(ctx)
    bind_kwargs: dict[str, str] = {
        "request_id": req_id,
        "correlation_id": corr_id,
    }
    if derived_ws:
        bind_kwargs["workspace_id"] = derived_ws
    if principal is not None:
        p_id = getattr(principal, "id", None)
        if p_id:
            bind_kwargs["principal_id"] = str(p_id)
    structlog.contextvars.bind_contextvars(**bind_kwargs)
    try:
        yield ctx
    finally:
        _request_context.reset(token)
        structlog.contextvars.unbind_contextvars(
            "request_id",
            "correlation_id",
            "workspace_id",
            "principal_id",
        )
