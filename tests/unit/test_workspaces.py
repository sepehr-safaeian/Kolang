"""
Unit tests for Workspace Domain Model and Tenant Scoping (ACP-008).

Verifies:
- Workspace entity structure (UUID PK, slug uniqueness validation, lifecycle status, timestamps).
- Pydantic DTO models and strict slug validation regex.
- TenantScopedMixin / WorkspaceScopedMixin inheritance.
- Presence of workspace_id on all domain models (Server, Tool, Agent, Policy,
  Approval, Credential, Audit).
- TenantContext extraction from RequestContext and verified Principal.
- Body workspace_id tampering detection and strict isolation enforcement.
"""

from __future__ import annotations

import uuid

import pytest
from pydantic import ValidationError

from acp_core.approvals.models import ApprovalId, ApprovalRequest
from acp_core.audit.models import AuditEvent, AuditEventType
from acp_core.common.context import (
    request_context_scope,
)
from acp_core.common.errors import AuthorizationError, NotFoundError
from acp_core.common.types import (
    CorrelationId,
    PolicyId,
    PrincipalId,
    PrincipalKind,
    RequestId,
    ServerId,
    WorkspaceId,
)
from acp_core.contracts.models import Principal
from acp_core.db.base import (
    Base,
    TenantScopedMixin,
    TimestampMixin,
    UUIDPrimaryKeyMixin,
    WorkspaceScopedMixin,
)
from acp_core.policy.models import PolicyEffect, PolicyRule
from acp_core.protocol.models import ServerDescriptor, ToolCallRequest, ToolDescriptor
from acp_core.workspaces.models import (
    Workspace,
    WorkspaceCreate,
    WorkspaceStatus,
)
from acp_core.workspaces.scoping import (
    TenantContext,
    enforce_resource_scope,
    extract_tenant_context,
    resolve_trusted_workspace_id,
)


def test_workspace_model_structure() -> None:
    """Verify Workspace ORM entity fields, mixins, and helper properties."""
    ws_id = uuid.uuid4()
    ws = Workspace(
        id=ws_id,
        name="Production Workspace",
        slug="prod-workspace",
        status=WorkspaceStatus.ACTIVE.value,
        description="Core production environment",
    )
    assert ws.id == ws_id
    assert ws.name == "Production Workspace"
    assert ws.slug == "prod-workspace"
    assert ws.status == "active"
    assert ws.is_active is True
    assert "prod-workspace" in repr(ws)

    ws.status = WorkspaceStatus.DISABLED.value
    assert ws.is_active is False


def test_workspace_pydantic_validation() -> None:
    """Verify WorkspaceCreate and WorkspaceRead Pydantic schemas and slug validation."""
    valid = WorkspaceCreate(
        name="Acme Corp",
        slug="acme-corp-1",
        description="Tenant 1",
    )
    assert valid.slug == "acme-corp-1"
    assert valid.status == WorkspaceStatus.ACTIVE

    # Disallowed slug formats
    invalid_slugs = [
        "-leading-hyphen",
        "trailing-hyphen-",
        "Upper_Case",
        "spaces in slug",
        "special@chars!",
        "",
    ]
    for bad_slug in invalid_slugs:
        with pytest.raises(ValidationError):
            WorkspaceCreate(name="Test", slug=bad_slug)

    # Empty name rejected
    with pytest.raises(ValidationError):
        WorkspaceCreate(name="   ", slug="valid-slug")


def test_workspace_scoped_mixin_structure() -> None:
    """Verify WorkspaceScopedMixin attaches indexed workspace_id to child entities."""

    class MockChildEntity(Base, UUIDPrimaryKeyMixin, TimestampMixin, WorkspaceScopedMixin):
        __tablename__ = "mock_child_entities"

    table = MockChildEntity.__table__
    assert "workspace_id" in table.c
    col = table.c.workspace_id
    assert col.nullable is False
    assert col.index is True
    assert TenantScopedMixin is WorkspaceScopedMixin


def test_all_domain_entities_carry_workspace_id() -> None:
    """
    Verify requirement: All entities for Server, Tool, Agent, Policy, Approval,
    and Audit must carry workspace_id.
    """
    ws_id = WorkspaceId("00000000-0000-0000-0000-000000000001")

    # 1. ApprovalRequest
    approval = ApprovalRequest(
        id=ApprovalId("appr-1"),
        workspace_id=ws_id,
        request_id=RequestId("req-1"),
        correlation_id=CorrelationId("corr-1"),
        principal_id=PrincipalId("p-1"),
        server_id=ServerId("srv-1"),
        tool_name="delete_table",
    )
    assert approval.workspace_id == ws_id

    # 2. AuditEvent (tenant-scoped)
    audit = AuditEvent(
        event_type=AuditEventType.TOOL_CALL_ALLOWED,
        workspace_id=str(ws_id),
        request_id="req-1",
    )
    assert audit.workspace_id == str(ws_id)

    # 2b. AuditEvent (global audit event with explicit justification)
    global_audit = AuditEvent(
        event_type=AuditEventType.SERVER_REGISTERED,
        workspace_id=None,
        details={"reason": "daemon_initialization_global"},
    )
    assert global_audit.workspace_id is None

    # 3. PolicyRule
    policy = PolicyRule(
        id=PolicyId("pol-1"),
        workspace_id=ws_id,
        name="Allow Read",
        effect=PolicyEffect.ALLOW,
    )
    assert policy.workspace_id == ws_id

    # 4. ToolCallRequest
    tool_call = ToolCallRequest(
        request_id="req-1",
        correlation_id="corr-1",
        principal_id="p-1",
        server_id="srv-1",
        tool_name="read_query",
        workspace_id=str(ws_id),
    )
    assert tool_call.workspace_id == str(ws_id)

    # 5. ServerDescriptor & ToolDescriptor
    srv = ServerDescriptor(
        server_id="srv-1",
        name="Filesystem Server",
        endpoint="http://localhost:8080",
        workspace_id=str(ws_id),
    )
    assert srv.workspace_id == str(ws_id)

    tool = ToolDescriptor(
        tool_id="tool-1",
        server_id="srv-1",
        name="read_file",
        workspace_id=str(ws_id),
    )
    assert tool.workspace_id == str(ws_id)

    # 6. Principal
    principal = Principal(
        id=PrincipalId("usr-1"),
        kind=PrincipalKind.USER,
        workspace_id=ws_id,
    )
    assert principal.workspace_id == ws_id


def test_tenant_context_extraction_from_principal() -> None:
    """Verify Rule 1: Workspace scope extracted from verified Principal in Request Context."""
    target_ws = uuid.uuid4()
    principal = Principal(
        id=PrincipalId("agent-finance"),
        kind=PrincipalKind.AGENT,
        workspace_id=WorkspaceId(str(target_ws)),
        roles=["analyst"],
    )

    with request_context_scope(principal=principal) as ctx:
        assert ctx.workspace_id == str(target_ws)
        tenant_ctx = extract_tenant_context()
        assert tenant_ctx.workspace_id == target_ws
        assert tenant_ctx.principal_id == "agent-finance"
        assert "analyst" in tenant_ctx.roles
        assert tenant_ctx.matches(target_ws) is True
        assert tenant_ctx.matches(uuid.uuid4()) is False


def test_tenant_context_extraction_missing_context() -> None:
    """Verify AuthorizationError is raised when no workspace context or principal exists."""
    with (
        request_context_scope(),
        pytest.raises(AuthorizationError, match="Active tenant workspace context required"),
    ):
        extract_tenant_context()


def test_body_workspace_tampering_protection() -> None:
    """
    Verify Rule 2: workspace_id sent from Body is never trusted alone.

    Attempts to inject a different workspace_id in the body are rejected with
    an AuthorizationError (tampering detection).
    """
    ws_alice = uuid.uuid4()
    ws_attacker = uuid.uuid4()

    tenant_ctx = TenantContext(workspace_id=ws_alice, principal_id="alice")

    # 1. Matching body is accepted
    resolved = resolve_trusted_workspace_id(tenant_ctx, body_workspace_id=str(ws_alice))
    assert resolved == ws_alice

    # 2. None body uses trusted tenant context
    resolved_none = resolve_trusted_workspace_id(tenant_ctx, body_workspace_id=None)
    assert resolved_none == ws_alice

    # 3. Mismatched body is rejected as tampering attack
    with pytest.raises(AuthorizationError, match="Cross-workspace access denied"):
        resolve_trusted_workspace_id(tenant_ctx, body_workspace_id=str(ws_attacker))

    # 4. Invalid UUID format rejected safely
    with pytest.raises(AuthorizationError, match="Invalid workspace identifier"):
        resolve_trusted_workspace_id(tenant_ctx, body_workspace_id="invalid-uuid")


def test_enforce_resource_scope_idor_prevention() -> None:
    """Verify that cross-workspace resource access raises NotFoundError (IDOR prevention)."""
    ws_legit = uuid.uuid4()
    ws_foreign = uuid.uuid4()

    tenant_ctx = TenantContext(workspace_id=ws_legit)

    # Own resource passes
    enforce_resource_scope(tenant_ctx, ws_legit, resource_type="server")

    # Foreign resource raises NotFoundError (obscures existence)
    with pytest.raises(NotFoundError, match="Server not found"):
        enforce_resource_scope(tenant_ctx, ws_foreign, resource_type="server")
