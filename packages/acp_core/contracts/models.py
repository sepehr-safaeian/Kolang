"""
Internal Gateway Request, Resource, and Decision Contracts for Kolang.

IMPORTANT: These models define the canonical internal domain contracts
for the Agent Control Plane (ACP) Gateway. They are strictly decoupled from
wire-level MCP transport details, JSON-RPC envelopes, and FastAPI/Starlette
request objects. Protocol adapters translate external wire messages into
these internal contracts.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from acp_core.common.types import (
    ClientId,
    CorrelationId,
    DecisionEffect,
    PolicyId,
    PrincipalId,
    PrincipalKind,
    RequestId,
    ServerId,
    ToolId,
    WorkspaceId,
)
from acp_core.protocol.models import TransportType

# ── Security & Sensitive Key Guards ──────────────────────────────────────────

PROHIBITED_SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "access_token",
        "refresh_token",
        "token",
        "secret",
        "client_secret",
        "password",
        "api_key",
        "apikey",
        "private_key",
        "credential",
        "authorization",
    }
)


def _assert_no_raw_secrets(data: dict[str, Any], field_name: str) -> dict[str, Any]:
    """Validate that a dictionary does not contain sensitive credential keys."""
    for key in data:
        normalized = key.lower().replace("-", "_").strip()
        if any(secret_term in normalized for secret_term in PROHIBITED_SENSITIVE_KEYS):
            msg = (
                f"Raw credential/secret detected in '{field_name}' under key '{key}'. "
                "Tokens and secrets must never be placed in public domain models."
            )
            raise ValueError(msg)
    return data


def _validate_non_empty(value: str, field_name: str) -> str:
    """Validate that an identifier string is non-empty and non-whitespace."""
    if not isinstance(value, str):
        msg = f"'{field_name}' must be a string."
        raise TypeError(msg)
    cleaned = value.strip()
    if not cleaned:
        msg = f"'{field_name}' cannot be empty or whitespace only."
        raise ValueError(msg)
    return cleaned


def _ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime object is timezone-aware and set to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


# ── 1. Principal ─────────────────────────────────────────────────────────────


class Principal(BaseModel):
    """
    Verified identity making a request within a workspace.

    Represents authenticated users, autonomous agents, or internal services.
    Organization tenancy is enforced via mandatory workspace_id.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: PrincipalId
    kind: PrincipalKind
    workspace_id: WorkspaceId
    roles: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    name: str = ""
    email: str | None = None
    groups: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("id", mode="before")
    @classmethod
    def _validate_id(cls, v: Any) -> PrincipalId:
        return PrincipalId(_validate_non_empty(str(v), "id"))

    @field_validator("workspace_id", mode="before")
    @classmethod
    def _validate_workspace_id(cls, v: Any) -> WorkspaceId:
        return WorkspaceId(_validate_non_empty(str(v), "workspace_id"))

    @field_validator("attributes", "metadata", mode="after")
    @classmethod
    def _check_secrets(cls, v: dict[str, Any], info: Any) -> dict[str, Any]:
        return _assert_no_raw_secrets(v, info.field_name or "attributes")

    @field_validator("created_at", "updated_at", mode="after")
    @classmethod
    def _check_utc(cls, v: datetime) -> datetime:
        return _ensure_utc(v)


# ── 2. RequestContext ────────────────────────────────────────────────────────


class RequestContext(BaseModel):
    """
    Metadata describing the incoming invocation request.

    Carries correlation identifiers, client attributes, and network transport
    independent of any web framework or JSON-RPC envelope.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: RequestId = Field(default_factory=lambda: RequestId(str(uuid.uuid4())))
    correlation_id: CorrelationId = Field(default_factory=lambda: CorrelationId(str(uuid.uuid4())))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    client_id: ClientId | None = None
    transport: TransportType = TransportType.STREAMABLE_HTTP
    workspace_id: WorkspaceId | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("request_id", mode="before")
    @classmethod
    def _validate_request_id(cls, v: Any) -> RequestId:
        return RequestId(_validate_non_empty(str(v), "request_id"))

    @field_validator("correlation_id", mode="before")
    @classmethod
    def _validate_correlation_id(cls, v: Any) -> CorrelationId:
        return CorrelationId(_validate_non_empty(str(v), "correlation_id"))

    @field_validator("client_id", mode="before")
    @classmethod
    def _validate_client_id(cls, v: Any) -> ClientId | None:
        if v is None:
            return None
        return ClientId(_validate_non_empty(str(v), "client_id"))

    @field_validator("workspace_id", mode="before")
    @classmethod
    def _validate_workspace_id(cls, v: Any) -> WorkspaceId | None:
        if v is None:
            return None
        return WorkspaceId(_validate_non_empty(str(v), "workspace_id"))

    @field_validator("metadata", mode="after")
    @classmethod
    def _check_secrets(cls, v: dict[str, Any], info: Any) -> dict[str, Any]:
        return _assert_no_raw_secrets(v, info.field_name or "metadata")

    @field_validator("timestamp", mode="after")
    @classmethod
    def _check_utc(cls, v: datetime) -> datetime:
        return _ensure_utc(v)


# ── 3. ToolResource ──────────────────────────────────────────────────────────


class ToolResource(BaseModel):
    """
    Internal catalog representation of an MCP tool resource.

    Identifies the tool, owning server, and deterministic schema fingerprint
    within a tenant workspace.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    workspace_id: WorkspaceId
    server_id: ServerId
    tool_id: ToolId
    tool_name: str
    fingerprint: str
    description: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("workspace_id", mode="before")
    @classmethod
    def _validate_workspace_id(cls, v: Any) -> WorkspaceId:
        return WorkspaceId(_validate_non_empty(str(v), "workspace_id"))

    @field_validator("server_id", mode="before")
    @classmethod
    def _validate_server_id(cls, v: Any) -> ServerId:
        return ServerId(_validate_non_empty(str(v), "server_id"))

    @field_validator("tool_id", mode="before")
    @classmethod
    def _validate_tool_id(cls, v: Any) -> ToolId:
        return ToolId(_validate_non_empty(str(v), "tool_id"))

    @field_validator("tool_name", "fingerprint", mode="before")
    @classmethod
    def _validate_strings(cls, v: Any, info: Any) -> str:
        return _validate_non_empty(str(v), info.field_name or "field")

    @field_validator("metadata", mode="after")
    @classmethod
    def _check_secrets(cls, v: dict[str, Any], info: Any) -> dict[str, Any]:
        return _assert_no_raw_secrets(v, info.field_name or "metadata")


# ── 4. ToolInvocation ────────────────────────────────────────────────────────


class ToolInvocation(BaseModel):
    """
    Executable parameters for a tool invocation targeted at an upstream server.

    Captures arguments and destination independent of protocol wire envelopes.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    workspace_id: WorkspaceId
    tool_name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    upstream_destination: str
    tool_id: ToolId | None = None
    fingerprint: str | None = None
    timeout_seconds: float = Field(default=30.0, ge=0.1, le=600.0)

    @field_validator("workspace_id", mode="before")
    @classmethod
    def _validate_workspace_id(cls, v: Any) -> WorkspaceId:
        return WorkspaceId(_validate_non_empty(str(v), "workspace_id"))

    @field_validator("tool_name", "upstream_destination", mode="before")
    @classmethod
    def _validate_strings(cls, v: Any, info: Any) -> str:
        return _validate_non_empty(str(v), info.field_name or "field")

    @field_validator("tool_id", mode="before")
    @classmethod
    def _validate_tool_id(cls, v: Any) -> ToolId | None:
        if v is None:
            return None
        return ToolId(_validate_non_empty(str(v), "tool_id"))

    @property
    def server_id(self) -> str:
        """Alias for upstream_destination matching server identification patterns."""
        return self.upstream_destination


# ── 5. PolicyInput ───────────────────────────────────────────────────────────


class PolicyInput(BaseModel):
    """
    Standardized payload provided to the authorization policy engine (e.g. OPA).

    Aggregates identity, requested action, target resource, and request context.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    principal: Principal
    action: str
    resource: ToolResource
    context: RequestContext
    invocation: ToolInvocation | None = None

    @field_validator("action", mode="before")
    @classmethod
    def _validate_action(cls, v: Any) -> str:
        return _validate_non_empty(str(v), "action")

    def to_opa_input(self) -> dict[str, Any]:
        """Convert policy input into a clean dictionary for OPA Rego evaluation."""
        return {
            "workspace_id": str(self.principal.workspace_id),
            "action": self.action,
            "principal": {
                "id": str(self.principal.id),
                "kind": str(self.principal.kind.value),
                "roles": list(self.principal.roles),
                "attributes": dict(self.principal.attributes),
                "groups": list(self.principal.groups),
            },
            "resource": {
                "workspace_id": str(self.resource.workspace_id),
                "server_id": str(self.resource.server_id),
                "tool_id": str(self.resource.tool_id),
                "tool_name": self.resource.tool_name,
                "fingerprint": self.resource.fingerprint,
                "metadata": dict(self.resource.metadata),
            },
            "context": {
                "request_id": str(self.context.request_id),
                "correlation_id": str(self.context.correlation_id),
                "timestamp": self.context.timestamp.isoformat(),
                "client_id": str(self.context.client_id) if self.context.client_id else None,
                "transport": str(self.context.transport.value),
            },
        }


# ── 6. PolicyDecision ────────────────────────────────────────────────────────


class PolicyObligation(BaseModel):
    """Post-decision obligation or side-effect condition enforced by the gateway."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    name: str = Field(alias="type")
    params: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: Any) -> str:
        return _validate_non_empty(str(v), "name")

    @property
    def type(self) -> str:
        """Compatibility property returning the obligation name as condition type."""
        return self.name


class PolicyDecision(BaseModel):
    """
    Explicit authorization outcome produced by the policy engine.

    Guarantees strict separation between machine reason codes and human explanations.
    Supports allow, deny, and require_approval decisions.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    decision: DecisionEffect = Field(alias="effect")
    reason_code: str
    reason_message: str = Field(default="", alias="reason")
    policy_id: PolicyId | None = None
    version: str | None = None
    obligations: list[PolicyObligation] = Field(default_factory=list, alias="conditions")
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    evaluation_duration_ms: float = 0.0

    @field_validator("reason_code", mode="before")
    @classmethod
    def _validate_reason_code(cls, v: Any) -> str:
        return _validate_non_empty(str(v), "reason_code")

    @field_validator("policy_id", mode="before")
    @classmethod
    def _validate_policy_id(cls, v: Any) -> PolicyId | None:
        if v is None:
            return None
        return PolicyId(_validate_non_empty(str(v), "policy_id"))

    @field_validator("evaluated_at", mode="after")
    @classmethod
    def _check_utc(cls, v: datetime) -> datetime:
        return _ensure_utc(v)

    @model_validator(mode="before")
    @classmethod
    def _normalize_compatibility_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Default reason_code if only reason string was provided
            if "reason_code" not in data:
                decision_val = data.get("decision") or data.get("effect")
                if decision_val in (DecisionEffect.ALLOW, "allow"):
                    data["reason_code"] = "AUTHZ_ALLOW"
                elif decision_val in (
                    DecisionEffect.REQUIRE_APPROVAL,
                    "require_approval",
                    DecisionEffect.CONDITIONAL,
                    "conditional",
                ):
                    data["reason_code"] = "AUTHZ_REQUIRE_APPROVAL"
                else:
                    data["reason_code"] = "AUTHZ_DENIED"
            # Map legacy conditions to obligations
            if "conditions" in data and "obligations" not in data:
                raw_conds = data.pop("conditions", [])
                obligations = []
                for c in raw_conds:
                    if isinstance(c, dict):
                        c_name = c.get("name") or c.get("type", "conditional")
                        c_params = c.get("params", {})
                        obligations.append({"name": c_name, "params": c_params})
                    elif hasattr(c, "type") or hasattr(c, "name"):
                        c_name = getattr(c, "name", None) or getattr(c, "type", "conditional")
                        c_params = getattr(c, "params", {})
                        obligations.append({"name": c_name, "params": c_params})
                data["obligations"] = obligations
        return data

    @property
    def effect(self) -> str:
        """Compatibility property returning the decision effect as a string."""
        return str(self.decision.value)

    @property
    def reason(self) -> str:
        """Compatibility property returning human-readable explanation."""
        return self.reason_message

    @property
    def conditions(self) -> list[PolicyObligation]:
        """Compatibility property returning obligations as conditions."""
        return self.obligations

    def is_allowed(self) -> bool:
        """Check if policy decision allows execution."""
        return bool(self.decision == DecisionEffect.ALLOW)

    def is_denied(self) -> bool:
        """Check if policy decision denies execution."""
        return bool(self.decision == DecisionEffect.DENY)

    def requires_approval(self) -> bool:
        """Check if policy decision mandates human-in-the-loop approval."""
        return bool(self.decision in (DecisionEffect.REQUIRE_APPROVAL, DecisionEffect.CONDITIONAL))


# ── 7. GatewayResult ─────────────────────────────────────────────────────────


class GatewayErrorPayload(BaseModel):
    """Standardized error contract for gateway or upstream execution failures."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False

    @field_validator("code", "message", mode="before")
    @classmethod
    def _validate_strings(cls, v: Any, info: Any) -> str:
        return _validate_non_empty(str(v), info.field_name or "field")


class GatewayResult(BaseModel):
    """
    Standardized outcome of an upstream MCP tool execution or security rejection.

    Provides a uniform payload to callers regardless of upstream transport or failures.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: RequestId
    correlation_id: CorrelationId
    success: bool
    result: Any | None = None
    error: GatewayErrorPayload | None = None
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("request_id", mode="before")
    @classmethod
    def _validate_request_id(cls, v: Any) -> RequestId:
        return RequestId(_validate_non_empty(str(v), "request_id"))

    @field_validator("correlation_id", mode="before")
    @classmethod
    def _validate_correlation_id(cls, v: Any) -> CorrelationId:
        return CorrelationId(_validate_non_empty(str(v), "correlation_id"))

    @field_validator("timestamp", mode="after")
    @classmethod
    def _check_utc(cls, v: datetime) -> datetime:
        return _ensure_utc(v)

    @field_validator("metadata", mode="after")
    @classmethod
    def _check_secrets(cls, v: dict[str, Any], info: Any) -> dict[str, Any]:
        return _assert_no_raw_secrets(v, info.field_name or "metadata")

    @classmethod
    def ok(
        cls,
        *,
        request_id: RequestId | str,
        correlation_id: CorrelationId | str,
        result: Any,
        duration_ms: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> GatewayResult:
        """Create a successful GatewayResult payload."""
        return cls(
            request_id=RequestId(str(request_id)),
            correlation_id=CorrelationId(str(correlation_id)),
            success=True,
            result=result,
            error=None,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )

    @classmethod
    def fail(
        cls,
        *,
        request_id: RequestId | str,
        correlation_id: CorrelationId | str,
        code: str,
        message: str,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
        duration_ms: float = 0.0,
        metadata: dict[str, Any] | None = None,
    ) -> GatewayResult:
        """Create a failed GatewayResult with a standardized error payload."""
        return cls(
            request_id=RequestId(str(request_id)),
            correlation_id=CorrelationId(str(correlation_id)),
            success=False,
            result=None,
            error=GatewayErrorPayload(
                code=code,
                message=message,
                details=details or {},
                retryable=retryable,
            ),
            duration_ms=duration_ms,
            metadata=metadata or {},
        )
