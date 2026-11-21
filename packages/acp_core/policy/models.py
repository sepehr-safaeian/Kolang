"""
Policy domain models for Kolang.

IMPORTANT: These models are purely internal and have NO dependency on
JSON-RPC, MCP wire format, or any transport protocol. They define the
vocabulary for expressing and evaluating access control policies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from acp_core.common.types import PolicyId, PrincipalKind
from acp_core.contracts.models import (
    PolicyDecision,
    PolicyInput,
    PolicyObligation,
)


class PolicyCondition(BaseModel):
    """A condition attached to a CONDITIONAL policy decision."""

    type: str = Field(description="Condition type, e.g. 'approval', 'mfa', 'time_window'")
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Condition parameters, e.g. {'approvers': ['admin']}",
    )


__all__ = [
    "PolicyCondition",
    "PolicyDecision",
    "PolicyEffect",
    "PolicyEvaluationInput",
    "PolicyInput",
    "PolicyObligation",
    "PolicyRule",
]


class PolicyEffect(StrEnum):
    """The effect of a policy evaluation."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"
    CONDITIONAL = "conditional"  # Requires approval or additional verification


class PolicyRule(BaseModel):
    """A declarative access control rule."""

    id: PolicyId
    name: str
    description: str = ""
    effect: PolicyEffect
    principals: list[str] = Field(
        default_factory=list,
        description="Principal patterns (glob), e.g. ['user:*', 'agent:builder-*']",
    )
    servers: list[str] = Field(
        default_factory=list,
        description="Server ID patterns (glob), e.g. ['prod-*']",
    )
    tools: list[str] = Field(
        default_factory=list,
        description="Tool name patterns (glob), e.g. ['read_*', 'query']",
    )
    conditions: list[PolicyCondition] = Field(default_factory=list)
    priority: int = Field(default=0, description="Higher priority rules are evaluated first")
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PolicyEvaluationInput(BaseModel):
    """Input data sent to the policy engine for evaluation."""

    principal_id: str
    principal_kind: PrincipalKind
    principal_roles: list[str] = Field(default_factory=list)
    principal_groups: list[str] = Field(default_factory=list)
    server_id: str
    tool_name: str
    arguments_hash: str = Field(
        default="",
        description="SHA-256 hash of the tool arguments (for audit, not content)",
    )
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    request_metadata: dict[str, Any] = Field(default_factory=dict)
