from __future__ import annotations

from acp_core.approvals.models import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalTransition,
    can_transition,
)
from acp_core.audit.models import AuditEvent, AuditEventType
from acp_core.common.types import (
    ApprovalId,
    CorrelationId,
    PrincipalId,
    PrincipalKind,
    RequestId,
    ServerId,
)
from acp_core.identity.models import AuthContext, Principal, TokenClaims
from acp_core.protocol.models import (
    HealthStatus,
    ServerDescriptor,
    ToolCallRequest,
    ToolCallResponse,
    ToolDescriptor,
    TransportType,
)


def test_protocol_models() -> None:
    req = ToolCallRequest(
        request_id="req-1",
        correlation_id="corr-1",
        principal_id="p-1",
        server_id="srv-1",
        tool_name="test_tool",
        arguments={"x": 10},
    )
    assert req.tool_name == "test_tool"
    assert req.arguments["x"] == 10

    resp = ToolCallResponse(
        request_id="req-1",
        correlation_id="corr-1",
        result={"status": "ok"},
        duration_ms=12.5,
    )
    assert resp.result == {"status": "ok"}
    assert resp.duration_ms == 12.5

    tool_desc = ToolDescriptor(
        tool_id="t-1",
        server_id="srv-1",
        name="test_tool",
        description="Demo tool",
    )
    assert tool_desc.name == "test_tool"

    srv_desc = ServerDescriptor(
        server_id="srv-1",
        name="Server 1",
        endpoint="http://localhost:9000",
        transport=TransportType.STREAMABLE_HTTP,
        health_status=HealthStatus.HEALTHY,
        tools=[tool_desc],
    )
    assert srv_desc.health_status == HealthStatus.HEALTHY
    assert len(srv_desc.tools) == 1


def test_identity_models() -> None:
    principal = Principal(
        id=PrincipalId("usr-alice"),
        kind=PrincipalKind.USER,
        name="Alice",
        roles=["developer", "admin"],
    )
    assert principal.name == "Alice"
    assert "admin" in principal.roles

    claims = TokenClaims(
        sub="usr-alice",
        iss="https://auth.kolang.dev",
        aud=["kolang-api"],
        exp=1800000000,
        iat=1700000000,
        roles=["admin"],
    )
    assert claims.sub == "usr-alice"

    auth_ctx = AuthContext(
        principal=principal,
        token_claims=claims,
    )
    assert auth_ctx.auth_method == "oidc"
    assert auth_ctx.principal.id == "usr-alice"


def test_approval_state_machine() -> None:
    assert can_transition(ApprovalStatus.PENDING, ApprovalStatus.APPROVED) is True
    assert can_transition(ApprovalStatus.PENDING, ApprovalStatus.REJECTED) is True
    assert can_transition(ApprovalStatus.PENDING, ApprovalStatus.EXPIRED) is True
    assert can_transition(ApprovalStatus.PENDING, ApprovalStatus.CANCELLED) is True
    assert can_transition(ApprovalStatus.APPROVED, ApprovalStatus.PENDING) is False
    assert can_transition(ApprovalStatus.REJECTED, ApprovalStatus.APPROVED) is False

    req = ApprovalRequest(
        id=ApprovalId("appr-1"),
        request_id=RequestId("req-1"),
        correlation_id=CorrelationId("corr-1"),
        principal_id=PrincipalId("p-1"),
        server_id=ServerId("srv-1"),
        tool_name="delete_database",
        required_approvers=["lead-admin"],
    )
    assert req.status == ApprovalStatus.PENDING

    transition = ApprovalTransition(
        from_status=ApprovalStatus.PENDING,
        to_status=ApprovalStatus.APPROVED,
        actor=PrincipalId("lead-admin"),
        reason="Approved after review",
    )
    assert transition.to_status == ApprovalStatus.APPROVED


def test_audit_models() -> None:
    event = AuditEvent(
        event_type=AuditEventType.TOOL_CALL_ALLOWED,
        request_id="req-1",
        correlation_id="corr-1",
        principal_id="p-1",
        server_id="srv-1",
        tool_name="query",
        outcome="success",
    )
    assert event.event_type == AuditEventType.TOOL_CALL_ALLOWED
    assert event.outcome == "success"
    assert event.id is not None
