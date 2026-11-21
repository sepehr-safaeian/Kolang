"""
Unit tests for Kolang internal gateway request, resource, and decision contracts.

Verifies validation, serialization, decision outcomes, and security guards
mandated by task ACP-003.
"""

from __future__ import annotations

import json
from datetime import UTC

import pytest
from pydantic import ValidationError

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
from acp_core.contracts import (
    GatewayErrorPayload,
    GatewayResult,
    PolicyDecision,
    PolicyInput,
    PolicyObligation,
    Principal,
    RequestContext,
    ToolInvocation,
    ToolResource,
)
from acp_core.gateway import (
    GatewayResult as GatewayGatewayResult,
)
from acp_core.gateway import (
    Principal as GatewayPrincipal,
)
from acp_core.protocol.models import TransportType

# ── 1. Principal Contract Tests ──────────────────────────────────────────────


def test_principal_valid_instantiation() -> None:
    """Test valid instantiation and attribute mapping for Principal."""
    principal = Principal(
        id=PrincipalId("usr-dev-01"),
        kind=PrincipalKind.USER,
        workspace_id=WorkspaceId("ws-enterprise-corp"),
        roles=["developer", "ai-engineer"],
        attributes={"clearance": "level-2", "department": "Platform"},
        name="Developer One",
        email="dev1@corp.example",
        groups=["engineering"],
        metadata={"onboarding_version": "v1.2"},
    )
    assert principal.id == "usr-dev-01"
    assert principal.kind == PrincipalKind.USER
    assert principal.workspace_id == "ws-enterprise-corp"
    assert "developer" in principal.roles
    assert principal.attributes["clearance"] == "level-2"
    assert principal.created_at.tzinfo == UTC


def test_principal_requires_workspace_id() -> None:
    """Tenancy rule: Principal must have a valid workspace_id."""
    with pytest.raises(ValidationError) as exc_info:
        Principal(  # type: ignore[call-arg]
            id=PrincipalId("usr-01"),
            kind=PrincipalKind.USER,
            # missing workspace_id
        )
    assert "workspace_id" in str(exc_info.value)

    with pytest.raises(ValidationError):
        Principal(
            id=PrincipalId("usr-01"),
            kind=PrincipalKind.USER,
            workspace_id=WorkspaceId("   "),  # whitespace only
        )


def test_principal_rejects_empty_id() -> None:
    """Principal id cannot be empty or whitespace."""
    with pytest.raises(ValidationError):
        Principal(
            id=PrincipalId(""),
            kind=PrincipalKind.AGENT,
            workspace_id=WorkspaceId("ws-01"),
        )


def test_principal_security_guard_rejects_secrets() -> None:
    """Security rule: Raw credentials and tokens must never enter Principal attributes."""
    forbidden_keys = [
        "access_token",
        "refresh_token",
        "api_key",
        "secret",
        "password",
        "client_secret",
        "credential",
    ]
    for key in forbidden_keys:
        with pytest.raises(ValidationError) as exc:
            Principal(
                id=PrincipalId("usr-01"),
                kind=PrincipalKind.USER,
                workspace_id=WorkspaceId("ws-01"),
                attributes={key: "raw-secret-value-1234"},
            )
        assert "Raw credential/secret detected" in str(exc.value)

        with pytest.raises(ValidationError) as exc_meta:
            Principal(
                id=PrincipalId("usr-01"),
                kind=PrincipalKind.USER,
                workspace_id=WorkspaceId("ws-01"),
                metadata={f"user_{key}": "sensitive-data"},
            )
        assert "Raw credential/secret detected" in str(exc_meta.value)


# ── 2. RequestContext Contract Tests ─────────────────────────────────────────


def test_request_context_defaults_and_validation() -> None:
    """Test RequestContext automatic UUID generation and UTC timestamps."""
    ctx = RequestContext()
    assert ctx.request_id is not None
    assert ctx.correlation_id is not None
    assert ctx.timestamp.tzinfo == UTC
    assert ctx.transport == TransportType.STREAMABLE_HTTP

    # Explicit values
    custom_ctx = RequestContext(
        request_id=RequestId("req-999"),
        correlation_id=CorrelationId("corr-888"),
        client_id=ClientId("client-agent-smith"),
        transport=TransportType.STDIO,
        workspace_id=WorkspaceId("ws-01"),
        ip_address="192.168.1.50",
        user_agent="KolangAgent/1.0",
        metadata={"env": "staging"},
    )
    assert custom_ctx.request_id == "req-999"
    assert custom_ctx.correlation_id == "corr-888"
    assert custom_ctx.client_id == "client-agent-smith"
    assert custom_ctx.transport == TransportType.STDIO
    assert custom_ctx.workspace_id == "ws-01"


def test_request_context_rejects_empty_ids() -> None:
    """Request ID and Correlation ID must not be empty strings."""
    with pytest.raises(ValidationError):
        RequestContext(request_id=RequestId(""))

    with pytest.raises(ValidationError):
        RequestContext(correlation_id=CorrelationId("  "))


def test_request_context_security_guard() -> None:
    """Security rule: Context metadata cannot carry raw tokens or passwords."""
    with pytest.raises(ValidationError) as exc:
        RequestContext(metadata={"bearer_token": "eyJh..."})
    assert "Raw credential/secret detected" in str(exc.value)


# ── 3. ToolResource Contract Tests ───────────────────────────────────────────


def test_tool_resource_valid_instantiation() -> None:
    """Test valid ToolResource catalog representation."""
    resource = ToolResource(
        workspace_id=WorkspaceId("ws-prod-01"),
        server_id=ServerId("srv-sql-cluster"),
        tool_id=ToolId("tool-query-readonly"),
        tool_name="database_query",
        fingerprint="sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        description="Executes readonly SQL queries against production replica",
        metadata={"classification": "confidential", "read_only": True},
    )
    assert resource.workspace_id == "ws-prod-01"
    assert resource.server_id == "srv-sql-cluster"
    assert resource.tool_id == "tool-query-readonly"
    assert resource.tool_name == "database_query"
    assert resource.fingerprint.startswith("sha256:")
    assert resource.metadata["read_only"] is True


def test_tool_resource_mandatory_fields() -> None:
    """Test that workspace_id, server_id, and tool_name are strictly required."""
    valid_args = {
        "workspace_id": WorkspaceId("ws-01"),
        "server_id": ServerId("srv-01"),
        "tool_id": ToolId("tool-01"),
        "tool_name": "fetch",
        "fingerprint": "sha256:12345",
    }
    for field in valid_args:
        args = dict(valid_args)
        args[field] = ""
        with pytest.raises(ValidationError):
            ToolResource(**args)


# ── 4. ToolInvocation Contract Tests ─────────────────────────────────────────


def test_tool_invocation_valid_instantiation() -> None:
    """Test valid ToolInvocation parameter structure."""
    inv = ToolInvocation(
        workspace_id=WorkspaceId("ws-prod-01"),
        tool_name="database_query",
        arguments={"query": "SELECT count(*) FROM users;", "limit": 100},
        upstream_destination="srv-sql-cluster",
        tool_id=ToolId("tool-query-readonly"),
        fingerprint="sha256:123456",
        timeout_seconds=45.0,
    )
    assert inv.workspace_id == "ws-prod-01"
    assert inv.tool_name == "database_query"
    assert inv.arguments["limit"] == 100
    assert inv.upstream_destination == "srv-sql-cluster"
    assert inv.server_id == "srv-sql-cluster"
    assert inv.timeout_seconds == 45.0


def test_tool_invocation_validations() -> None:
    """Test validation constraints on timeout and required fields."""
    with pytest.raises(ValidationError):
        ToolInvocation(
            workspace_id=WorkspaceId(""),
            tool_name="test",
            upstream_destination="dest",
        )

    with pytest.raises(ValidationError):
        ToolInvocation(
            workspace_id=WorkspaceId("ws-01"),
            tool_name="test",
            upstream_destination="dest",
            timeout_seconds=0.05,  # Must be >= 0.1s
        )


# ── 5. PolicyInput Contract Tests ────────────────────────────────────────────


def test_policy_input_and_opa_formatting() -> None:
    """Test PolicyInput assembly and OPA dictionary generation."""
    principal = Principal(
        id=PrincipalId("usr-bob"),
        kind=PrincipalKind.USER,
        workspace_id=WorkspaceId("ws-sec-01"),
        roles=["security-analyst"],
        attributes={"clearance": "top-secret"},
    )
    resource = ToolResource(
        workspace_id=WorkspaceId("ws-sec-01"),
        server_id=ServerId("srv-audit-log"),
        tool_id=ToolId("tool-read-audit"),
        tool_name="read_audit_logs",
        fingerprint="sha256:abcdef",
    )
    ctx = RequestContext(
        request_id=RequestId("req-101"),
        correlation_id=CorrelationId("corr-101"),
        client_id=ClientId("client-web-ui"),
        transport=TransportType.STREAMABLE_HTTP,
    )
    invocation = ToolInvocation(
        workspace_id=WorkspaceId("ws-sec-01"),
        tool_name="read_audit_logs",
        arguments={"filter": "auth.failed"},
        upstream_destination="srv-audit-log",
    )
    policy_input = PolicyInput(
        principal=principal,
        action="tools/call",
        resource=resource,
        context=ctx,
        invocation=invocation,
    )
    assert policy_input.action == "tools/call"
    assert policy_input.principal.id == "usr-bob"

    opa_data = policy_input.to_opa_input()
    assert opa_data["workspace_id"] == "ws-sec-01"
    assert opa_data["action"] == "tools/call"
    assert opa_data["principal"]["id"] == "usr-bob"
    assert opa_data["principal"]["kind"] == "user"
    assert opa_data["resource"]["server_id"] == "srv-audit-log"
    assert opa_data["resource"]["tool_name"] == "read_audit_logs"
    assert opa_data["context"]["request_id"] == "req-101"
    assert opa_data["context"]["transport"] == "streamable_http"


# ── 6. PolicyDecision Contract Tests ─────────────────────────────────────────


def test_policy_decision_three_canonical_outcomes() -> None:
    """Acceptance Criteria: Verify allow, deny, and require_approval decisions."""
    # 1. ALLOW
    allow_decision = PolicyDecision(
        decision=DecisionEffect.ALLOW,
        reason_code="AUTHZ_ALLOW_ROLE_MATCH",
        reason_message="Principal role matches authorized tool execution policy",
        policy_id=PolicyId("pol-read-tools-v1"),
        version="1.0.0",
        evaluation_duration_ms=1.45,
    )
    assert allow_decision.decision == DecisionEffect.ALLOW
    assert allow_decision.is_allowed() is True
    assert allow_decision.is_denied() is False
    assert allow_decision.requires_approval() is False
    assert allow_decision.reason_code == "AUTHZ_ALLOW_ROLE_MATCH"
    expected_msg = "Principal role matches authorized tool execution policy"
    assert allow_decision.reason_message == expected_msg

    # 2. DENY
    deny_decision = PolicyDecision(
        decision=DecisionEffect.DENY,
        reason_code="AUTHZ_DENY_UNCLASSIFIED_TOOL",
        reason_message="Target tool lacks required security classification",
        policy_id=PolicyId("pol-default-deny"),
        version="2.1.0",
        evaluation_duration_ms=0.82,
    )
    assert deny_decision.decision == DecisionEffect.DENY
    assert deny_decision.is_allowed() is False
    assert deny_decision.is_denied() is True
    assert deny_decision.requires_approval() is False
    assert deny_decision.reason_code == "AUTHZ_DENY_UNCLASSIFIED_TOOL"

    # 3. REQUIRE_APPROVAL
    obligation = PolicyObligation(
        name="human_approval",
        params={"required_approvers": ["security-lead"], "timeout_seconds": 3600},
    )
    approval_decision = PolicyDecision(
        decision=DecisionEffect.REQUIRE_APPROVAL,
        reason_code="AUTHZ_REQUIRE_APPROVAL_HIGH_RISK",
        reason_message="Production database deletion requires approval from Security Lead",
        policy_id=PolicyId("pol-high-risk-v1"),
        version="1.0.0",
        obligations=[obligation],
        evaluation_duration_ms=2.10,
    )
    assert approval_decision.decision == DecisionEffect.REQUIRE_APPROVAL
    assert approval_decision.is_allowed() is False
    assert approval_decision.is_denied() is False
    assert approval_decision.requires_approval() is True
    assert approval_decision.reason_code == "AUTHZ_REQUIRE_APPROVAL_HIGH_RISK"
    assert len(approval_decision.obligations) == 1
    assert approval_decision.obligations[0].name == "human_approval"
    assert approval_decision.obligations[0].params["timeout_seconds"] == 3600


def test_policy_decision_machine_and_human_reason_separation() -> None:
    """Rule 5: Decision Reason must strictly separate machine code and human message."""
    decision = PolicyDecision(
        decision=DecisionEffect.DENY,
        reason_code="AUTHZ_TENANT_MISMATCH",
        reason_message="Principal workspace does not match requested resource workspace.",
    )
    assert decision.reason_code == "AUTHZ_TENANT_MISMATCH"
    assert "Principal workspace does not match" in decision.reason_message

    # Blank machine reason_code must be rejected
    with pytest.raises(ValidationError):
        PolicyDecision(
            decision=DecisionEffect.DENY,
            reason_code="",
            reason_message="Human message only",
        )


def test_policy_decision_backwards_compatibility_aliases() -> None:
    """Verify legacy effect/reason/conditions aliases work seamlessly."""
    decision = PolicyDecision(
        effect=DecisionEffect.ALLOW,  # legacy field alias
        reason="Legacy string message",  # legacy field alias
    )
    assert decision.decision == DecisionEffect.ALLOW
    assert decision.effect == "allow"
    assert decision.reason == "Legacy string message"
    assert decision.reason_code == "AUTHZ_ALLOW"


# ── 7. GatewayResult Contract Tests ──────────────────────────────────────────


def test_gateway_result_ok() -> None:
    """Test successful GatewayResult factory."""
    res = GatewayResult.ok(
        request_id=RequestId("req-500"),
        correlation_id=CorrelationId("corr-500"),
        result={"rows": [{"id": 1, "status": "active"}]},
        duration_ms=18.4,
        metadata={"cache_hit": False},
    )
    assert res.success is True
    assert res.request_id == "req-500"
    assert res.result == {"rows": [{"id": 1, "status": "active"}]}
    assert res.error is None
    assert res.duration_ms == 18.4
    assert res.timestamp.tzinfo == UTC


def test_gateway_result_fail() -> None:
    """Test failed GatewayResult factory with standardized error payload."""
    res = GatewayResult.fail(
        request_id=RequestId("req-501"),
        correlation_id=CorrelationId("corr-501"),
        code="UPSTREAM_TIMEOUT",
        message="Upstream MCP server timed out after 30 seconds",
        details={"server_id": "srv-sql", "timeout": 30.0},
        retryable=True,
        duration_ms=30005.2,
    )
    assert res.success is False
    assert res.result is None
    assert isinstance(res.error, GatewayErrorPayload)
    assert res.error.code == "UPSTREAM_TIMEOUT"
    assert res.error.message == "Upstream MCP server timed out after 30 seconds"
    assert res.error.retryable is True
    assert res.error.details["server_id"] == "srv-sql"


# ── 8. Serialization Roundtrip and Secret Sanitization Tests ─────────────────


def test_full_serialization_roundtrip() -> None:
    """Acceptance Criteria: Unit test for validation and JSON/dict serialization."""
    principal = Principal(
        id=PrincipalId("usr-agent-01"),
        kind=PrincipalKind.AGENT,
        workspace_id=WorkspaceId("ws-corp"),
        roles=["researcher"],
        attributes={"model": "gemini-flash"},
    )
    resource = ToolResource(
        workspace_id=WorkspaceId("ws-corp"),
        server_id=ServerId("srv-web-search"),
        tool_id=ToolId("tool-search"),
        tool_name="web_search",
        fingerprint="sha256:99887766",
        description="Searches the web index",
    )
    ctx = RequestContext(
        request_id=RequestId("req-ser-1"),
        correlation_id=CorrelationId("corr-ser-1"),
        client_id=ClientId("client-01"),
        transport=TransportType.STREAMABLE_HTTP,
        workspace_id=WorkspaceId("ws-corp"),
    )
    invocation = ToolInvocation(
        workspace_id=WorkspaceId("ws-corp"),
        tool_name="web_search",
        arguments={"q": "MCP protocol specs"},
        upstream_destination="srv-web-search",
    )
    policy_input = PolicyInput(
        principal=principal,
        action="tools/call",
        resource=resource,
        context=ctx,
        invocation=invocation,
    )

    # 1. Model Dump
    dumped_dict = policy_input.model_dump()
    assert dumped_dict["principal"]["id"] == "usr-agent-01"
    assert dumped_dict["action"] == "tools/call"
    assert dumped_dict["resource"]["tool_name"] == "web_search"
    assert dumped_dict["context"]["transport"] == "streamable_http"

    # 2. JSON Serialization
    json_str = policy_input.model_dump_json()
    parsed_json = json.loads(json_str)
    assert parsed_json["principal"]["workspace_id"] == "ws-corp"

    # 3. Model Validation from JSON
    restored = PolicyInput.model_validate_json(json_str)
    assert restored.principal.id == policy_input.principal.id
    assert restored.resource.fingerprint == policy_input.resource.fingerprint
    assert restored.context.request_id == policy_input.context.request_id


def test_no_raw_secrets_in_serialization() -> None:
    """Acceptance Criteria: No raw secret or token exists in serialized models."""
    principal = Principal(
        id=PrincipalId("usr-safe"),
        kind=PrincipalKind.USER,
        workspace_id=WorkspaceId("ws-safe"),
        roles=["viewer"],
        attributes={"team": "analytics", "badge_id": "B-4412"},
    )
    resource = ToolResource(
        workspace_id=WorkspaceId("ws-safe"),
        server_id=ServerId("srv-safe"),
        tool_id=ToolId("tool-safe"),
        tool_name="safe_action",
        fingerprint="sha256:fedcba",
    )
    ctx = RequestContext(
        request_id=RequestId("req-safe"),
        correlation_id=CorrelationId("corr-safe"),
        metadata={"audit_session": "sess-900"},
    )
    decision = PolicyDecision(
        decision=DecisionEffect.ALLOW,
        reason_code="AUTHZ_ALLOW",
        reason_message="Access granted cleanly",
    )
    result = GatewayResult.ok(
        request_id=ctx.request_id,
        correlation_id=ctx.correlation_id,
        result={"status": "clean"},
        metadata={"safe_meta": "verified"},
    )

    models_to_inspect = [
        principal.model_dump_json(),
        resource.model_dump_json(),
        ctx.model_dump_json(),
        decision.model_dump_json(),
        result.model_dump_json(),
    ]

    for model_json in models_to_inspect:
        raw_text = model_json.lower()
        for sensitive_term in ["access_token", "refresh_token", "password", "api_key", "secret"]:
            assert f'"{sensitive_term}"' not in raw_text


def test_gateway_reexports() -> None:
    """Verify that contracts are accessible directly from acp_core.gateway."""
    assert GatewayPrincipal is Principal
    assert GatewayGatewayResult is GatewayResult
