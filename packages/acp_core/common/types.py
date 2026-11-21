"""
Shared type definitions for Kolang.

Provides domain-specific NewTypes and enums used across all packages.
These types carry semantic meaning and enable static analysis.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, NewType

# ── Identifier Types ─────────────────────────────────────────────────────────

PrincipalId = NewType("PrincipalId", str)
ToolId = NewType("ToolId", str)
ServerId = NewType("ServerId", str)
PolicyId = NewType("PolicyId", str)
ApprovalId = NewType("ApprovalId", str)
RequestId = NewType("RequestId", str)
CorrelationId = NewType("CorrelationId", str)

# ── Type Aliases ─────────────────────────────────────────────────────────────

Timestamp = datetime
JSON = dict[str, Any]

# ── Enums ────────────────────────────────────────────────────────────────────


class PrincipalKind(StrEnum):
    """The type of principal making a request."""

    USER = "user"
    SERVICE = "service"
    AGENT = "agent"


class ToolCallResult(StrEnum):
    """Outcome of a tool call policy evaluation."""

    ALLOWED = "allowed"
    DENIED = "denied"
    PENDING_APPROVAL = "pending_approval"
    ERROR = "error"
