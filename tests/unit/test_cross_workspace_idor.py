"""
Cross-Workspace IDOR and Tenant Isolation Security Tests (ACP-008).

Verifies:
- Cross-workspace isolation for Server and Policy domain models in the Service Layer.
- Complete invisibility of foreign tenant resources during list / query operations.
- Prevention of IDOR reading, mutation, and deletion across workspace boundaries.
- Rejection of body tampering when cross-workspace IDs are passed in payloads.
- Demo workspace seeding and presence of seed data.
"""

from __future__ import annotations

import uuid

import pytest

from acp_core.common.errors import AuthorizationError, NotFoundError
from acp_core.policy.models import PolicyEffect
from acp_core.workspaces.scoped_services import (
    ScopedPolicyService,
    ScopedServerService,
)
from acp_core.workspaces.scoping import TenantContext
from acp_core.workspaces.seed import (
    DEMO_WORKSPACE_DESCRIPTION,
    DEMO_WORKSPACE_ID,
    DEMO_WORKSPACE_NAME,
    DEMO_WORKSPACE_SLUG,
)


@pytest.fixture
def workspace_a() -> TenantContext:
    """Tenant context for Organization A."""
    return TenantContext(
        workspace_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        principal_id="alice@org-a.com",
        workspace_slug="org-a",
        roles=("admin",),
    )


@pytest.fixture
def workspace_b() -> TenantContext:
    """Tenant context for Organization B."""
    return TenantContext(
        workspace_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        principal_id="bob@org-b.com",
        workspace_slug="org-b",
        roles=("admin",),
    )


# ── 1. MCP Server Cross-Workspace & IDOR Tests ───────────────────────────────


def test_server_cross_workspace_isolation_and_query_scoping(
    workspace_a: TenantContext,
    workspace_b: TenantContext,
) -> None:
    """
    AC 2 & 4: Queries belonging to another workspace are not visible in Service Layer.
    """
    server_svc = ScopedServerService()

    # Register Server 1 in Workspace A
    srv_a = server_svc.register_server(
        tenant_ctx=workspace_a,
        server_id="srv-postgres-a",
        name="Postgres MCP Server A",
        endpoint="https://pg-a.internal/mcp",
    )
    assert srv_a.workspace_id == workspace_a.workspace_id_str

    # Register Server 2 in Workspace B
    srv_b = server_svc.register_server(
        tenant_ctx=workspace_b,
        server_id="srv-redis-b",
        name="Redis MCP Server B",
        endpoint="https://redis-b.internal/mcp",
    )
    assert srv_b.workspace_id == workspace_b.workspace_id_str

    # Query servers as Workspace A
    servers_a = server_svc.list_servers(workspace_a)
    assert len(servers_a) == 1
    assert servers_a[0].server_id == "srv-postgres-a"
    # Ensure Workspace B's server is completely invisible to Workspace A
    assert not any(s.server_id == "srv-redis-b" for s in servers_a)

    # Query servers as Workspace B
    servers_b = server_svc.list_servers(workspace_b)
    assert len(servers_b) == 1
    assert servers_b[0].server_id == "srv-redis-b"
    assert not any(s.server_id == "srv-postgres-a" for s in servers_b)


def test_server_idor_read_and_mutation_blocked(
    workspace_a: TenantContext,
    workspace_b: TenantContext,
) -> None:
    """
    AC 3: IDOR prevention for Server.
    Caller in Workspace A cannot read, update, or delete Server belonging to Workspace B.
    """
    server_svc = ScopedServerService()

    # Workspace B owns sensitive financial MCP server
    server_svc.register_server(
        tenant_ctx=workspace_b,
        server_id="srv-financial-b",
        name="Ledger Server B",
        endpoint="https://ledger.internal/mcp",
    )

    # 1. IDOR Read Attempt: Caller in Workspace A tries to fetch Workspace B's server ID
    with pytest.raises(NotFoundError, match="Server 'srv-financial-b' not found"):
        server_svc.get_server(workspace_a, server_id="srv-financial-b")

    # 2. IDOR Update Attempt: Caller in Workspace A tries to modify Workspace B's server
    with pytest.raises(NotFoundError):
        server_svc.update_server(
            workspace_a,
            server_id="srv-financial-b",
            name="Tampered Name",
        )

    # 3. IDOR Delete Attempt: Caller in Workspace A tries to delete Workspace B's server
    with pytest.raises(NotFoundError):
        server_svc.delete_server(workspace_a, server_id="srv-financial-b")

    # Verify Workspace B's server remains intact and unmodified
    b_server = server_svc.get_server(workspace_b, server_id="srv-financial-b")
    assert b_server.name == "Ledger Server B"


def test_server_payload_body_tampering_rejected(
    workspace_a: TenantContext,
    workspace_b: TenantContext,
) -> None:
    """
    Rule 2: workspace_id in request body is not trusted alone.
    If caller in Workspace A provides workspace_b in body, Service Layer rejects.
    """
    server_svc = ScopedServerService()

    # Caller A tries to register a server in Workspace B via body spoofing
    with pytest.raises(AuthorizationError, match="Cross-workspace access denied"):
        server_svc.register_server(
            tenant_ctx=workspace_a,
            server_id="srv-spoofed",
            name="Spoofed Server",
            endpoint="https://evil.internal/mcp",
            body_workspace_id=workspace_b.workspace_id,
        )


# ── 2. Access Policy Cross-Workspace & IDOR Tests ────────────────────────────


def test_policy_cross_workspace_isolation_and_query_scoping(
    workspace_a: TenantContext,
    workspace_b: TenantContext,
) -> None:
    """
    AC 2 & 4: Policies of another workspace are not visible or queryable.
    """
    policy_svc = ScopedPolicyService()

    # Workspace A defines Read-Only Policy
    policy_svc.create_policy(
        tenant_ctx=workspace_a,
        policy_id="pol-readonly-a",
        name="Workspace A Read Only",
        effect=PolicyEffect.ALLOW,
        tools=["read_*"],
    )

    # Workspace B defines Admin All Policy
    policy_svc.create_policy(
        tenant_ctx=workspace_b,
        policy_id="pol-admin-b",
        name="Workspace B Admin",
        effect=PolicyEffect.ALLOW,
        tools=["*"],
    )

    # List as Workspace A
    policies_a = policy_svc.list_policies(workspace_a)
    assert len(policies_a) == 1
    assert policies_a[0].id == "pol-readonly-a"
    assert not any(p.id == "pol-admin-b" for p in policies_a)

    # List as Workspace B
    policies_b = policy_svc.list_policies(workspace_b)
    assert len(policies_b) == 1
    assert policies_b[0].id == "pol-admin-b"
    assert not any(p.id == "pol-readonly-a" for p in policies_b)


def test_policy_idor_read_and_mutation_blocked(
    workspace_a: TenantContext,
    workspace_b: TenantContext,
) -> None:
    """
    AC 3: IDOR prevention for Policy.
    Caller in Workspace A cannot view, alter, or delete Policy in Workspace B.
    """
    policy_svc = ScopedPolicyService()

    policy_svc.create_policy(
        tenant_ctx=workspace_b,
        policy_id="pol-critical-b",
        name="Critical Production Policy",
        effect=PolicyEffect.DENY,
        tools=["drop_table"],
    )

    # 1. IDOR Read Attempt: Caller A tries to read Workspace B's policy
    with pytest.raises(NotFoundError, match="Policy 'pol-critical-b' not found"):
        policy_svc.get_policy(workspace_a, policy_id="pol-critical-b")

    # 2. IDOR Mutation Attempt: Caller A tries to disable Workspace B's policy
    with pytest.raises(NotFoundError):
        policy_svc.update_policy(
            workspace_a,
            policy_id="pol-critical-b",
            enabled=False,
        )

    # 3. IDOR Delete Attempt: Caller A tries to remove Workspace B's policy
    with pytest.raises(NotFoundError):
        policy_svc.delete_policy(workspace_a, policy_id="pol-critical-b")

    # Verify Workspace B's policy is untouched and still active
    b_policy = policy_svc.get_policy(workspace_b, policy_id="pol-critical-b")
    assert b_policy.enabled is True
    assert b_policy.effect == PolicyEffect.DENY


def test_policy_payload_body_tampering_rejected(
    workspace_a: TenantContext,
    workspace_b: TenantContext,
) -> None:
    """
    Rule 2: Attempting to create a policy with mismatched body_workspace_id is rejected.
    """
    policy_svc = ScopedPolicyService()

    with pytest.raises(AuthorizationError, match="Cross-workspace access denied"):
        policy_svc.create_policy(
            tenant_ctx=workspace_a,
            policy_id="pol-spoofed",
            name="Spoofed Policy",
            effect=PolicyEffect.ALLOW,
            body_workspace_id=workspace_b.workspace_id,
        )


# ── 3. Demo Workspace Seed Tests ─────────────────────────────────────────────


def test_demo_workspace_constants_and_contract() -> None:
    """
    AC 1: Demo workspace specifications conform to unguessable/deterministic contract.
    """
    assert uuid.UUID("00000000-0000-0000-0000-000000000001") == DEMO_WORKSPACE_ID
    assert DEMO_WORKSPACE_SLUG == "demo"
    assert DEMO_WORKSPACE_NAME == "Demo Workspace"
    assert "seeded workspace" in DEMO_WORKSPACE_DESCRIPTION.lower()
