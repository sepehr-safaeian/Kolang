"""
Audit event models for Kolang.

Defines the audit event schema and sink protocol for compliance
and forensic logging of all security-relevant actions.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, Field


class AuditEventType(StrEnum):
    """Types of auditable events in Kolang."""

    TOOL_CALL_REQUESTED = "tool_call.requested"
    TOOL_CALL_ALLOWED = "tool_call.allowed"
    TOOL_CALL_DENIED = "tool_call.denied"
    TOOL_CALL_COMPLETED = "tool_call.completed"
    TOOL_CALL_FAILED = "tool_call.failed"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_REJECTED = "approval.rejected"
    PRINCIPAL_AUTHENTICATED = "principal.authenticated"
    PRINCIPAL_UNAUTHORIZED = "principal.unauthorized"
    POLICY_EVALUATED = "policy.evaluated"
    SERVER_REGISTERED = "server.registered"
    SERVER_DEREGISTERED = "server.deregistered"
    CREDENTIAL_ACCESSED = "credential.accessed"


class AuditEvent(BaseModel):
    """
    An immutable record of a security-relevant event.

    All tenant operations must attach a valid workspace_id. A null workspace_id
    is reserved strictly for global system events (such as daemon startup,
    unauthenticated edge probes, or system-wide maintenance) with explicit
    justification logged in details.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: AuditEventType
    workspace_id: str | None = Field(
        default=None,
        description="Tenant workspace ID. None is reserved strictly for global audit events.",
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_id: str = ""
    correlation_id: str = ""
    principal_id: str | None = None
    server_id: str | None = None
    tool_name: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    outcome: str = ""
    source_ip: str | None = None


class AuditSink(Protocol):
    """Interface for audit event consumers."""

    async def emit(self, event: AuditEvent) -> None:
        """Write a single audit event."""
        ...

    async def flush(self) -> None:
        """Flush any buffered events."""
        ...
