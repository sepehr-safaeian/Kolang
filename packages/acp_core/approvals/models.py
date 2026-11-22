"""
Approval state machine models for Kolang.

Defines the approval lifecycle with valid state transitions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from acp_core.common.types import (
    ApprovalId,
    CorrelationId,
    PrincipalId,
    RequestId,
    ServerId,
    WorkspaceId,
)


class ApprovalStatus(StrEnum):
    """Lifecycle states of an approval request."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


# ── Valid State Transitions ──────────────────────────────────────────────────

_VALID_TRANSITIONS: dict[ApprovalStatus, set[ApprovalStatus]] = {
    ApprovalStatus.PENDING: {
        ApprovalStatus.APPROVED,
        ApprovalStatus.REJECTED,
        ApprovalStatus.EXPIRED,
        ApprovalStatus.CANCELLED,
    },
    ApprovalStatus.APPROVED: set(),
    ApprovalStatus.REJECTED: set(),
    ApprovalStatus.EXPIRED: set(),
    ApprovalStatus.CANCELLED: set(),
}


def can_transition(from_status: ApprovalStatus, to_status: ApprovalStatus) -> bool:
    """Check whether a state transition is valid."""
    return to_status in _VALID_TRANSITIONS.get(from_status, set())


# ── Models ───────────────────────────────────────────────────────────────────


class ApprovalRequest(BaseModel):
    """A request for human approval before a tool call proceeds."""

    id: ApprovalId
    workspace_id: WorkspaceId = Field(default=WorkspaceId("default"))
    request_id: RequestId
    correlation_id: CorrelationId
    principal_id: PrincipalId
    server_id: ServerId
    tool_name: str
    reason: str = ""
    required_approvers: list[str] = Field(default_factory=list)
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    decided_at: datetime | None = None
    decided_by: PrincipalId | None = None
    decision_reason: str | None = None


class ApprovalTransition(BaseModel):
    """Records a state transition in the approval lifecycle."""

    from_status: ApprovalStatus
    to_status: ApprovalStatus
    actor: PrincipalId
    reason: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
