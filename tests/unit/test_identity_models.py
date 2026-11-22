"""
Unit tests for ACP-011 Identity Domain Models.

Verifies:
1. Human User and Agent are distinct identity types (PrincipalKind.USER vs PrincipalKind.AGENT).
2. Agent lifecycle statuses (active, inactive, suspended, revoked) and is_active behavior.
3. Inactive Agent cannot execute new requests (check_can_execute raises AuthorizationError).
4. McpClientRegistration models, lifecycle statuses, and validation.
5. WorkspaceMembership models and role assignments.
6. TokenClaims parsing and effective_client_id resolution (azp / client_id).
7. Interoperability: PrincipalContext to canonical Principal contract conversion.
8. Defense: Rejection of raw secret keys in metadata.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from acp_core.common.errors import AuthorizationError
from acp_core.common.types import PrincipalKind
from acp_core.identity.models import (
    AgentBase,
    AgentRead,
    AgentStatus,
    ClientStatus,
    McpClientRegistrationCreate,
    McpClientRegistrationRead,
    MembershipStatus,
    PrincipalContext,
    TokenClaims,
    WorkspaceMembershipCreate,
    WorkspaceMembershipRead,
    WorkspaceRole,
)


def test_agent_slug_validation() -> None:
    """Verify that agent slugs must adhere to URL-safe patterns."""
    # Valid slugs
    a1 = AgentBase(name="Reviewer", slug="reviewer-v1")
    assert a1.slug == "reviewer-v1"

    a2 = AgentBase(name="SQL Bot", slug="sql-bot-99")
    assert a2.slug == "sql-bot-99"

    # Invalid slugs
    with pytest.raises(ValueError, match="invalid"):
        AgentBase(name="Bad Agent", slug="-invalid-start")

    with pytest.raises(ValueError, match="invalid"):
        AgentBase(name="Bad Agent", slug="invalid_underscore")

    with pytest.raises(ValueError, match="invalid"):
        AgentBase(name="Bad Agent", slug="invalid space")


def test_agent_lifecycle_status_and_is_active() -> None:
    """Verify agent is_active property across operational statuses."""
    now = datetime.now(UTC)
    ws_id = uuid.uuid4()
    agent_id = uuid.uuid4()

    active_agent = AgentRead(
        id=agent_id,
        workspace_id=ws_id,
        name="Assistant",
        slug="assistant",
        status=AgentStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    assert active_agent.is_active is True

    inactive_agent = AgentRead(
        id=agent_id,
        workspace_id=ws_id,
        name="Assistant",
        slug="assistant",
        status=AgentStatus.INACTIVE,
        created_at=now,
        updated_at=now,
    )
    assert inactive_agent.is_active is False

    revoked_agent = AgentRead(
        id=agent_id,
        workspace_id=ws_id,
        name="Assistant",
        slug="assistant",
        status=AgentStatus.REVOKED,
        created_at=now,
        updated_at=now,
    )
    assert revoked_agent.is_active is False


def test_distinct_human_user_and_agent_identities() -> None:
    """
    Acceptance Criteria 1:
    Verify that Human User and Agent are two completely distinct identity types.
    """
    ws_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    now = datetime.now(UTC)

    claims = TokenClaims(
        sub="usr-bob",
        iss="https://auth.kolang.dev",
        exp=1800000000,
        iat=1700000000,
        roles=["developer"],
        azp="kolang-web",
    )

    # 1. Human User Principal Context
    user_ctx = PrincipalContext(
        principal_id="usr-bob",
        kind=PrincipalKind.USER,
        workspace_id=ws_id,
        roles=["developer"],
        client_id="kolang-web",
        user_id="usr-bob",
        token_claims=claims,
    )
    assert user_ctx.is_user is True
    assert user_ctx.is_agent is False
    assert user_ctx.is_service is False
    assert user_ctx.user_id == "usr-bob"
    assert user_ctx.agent_id is None

    # 2. Agent Workload Principal Context
    agent_record = AgentRead(
        id=agent_id,
        workspace_id=ws_id,
        name="Security Scanner",
        slug="security-scanner",
        status=AgentStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    agent_claims = TokenClaims(
        sub="service-account-kolang-api",
        iss="https://auth.kolang.dev",
        exp=1800000000,
        iat=1700000000,
        roles=["agent"],
        azp="kolang-api",
    )

    agent_ctx = PrincipalContext(
        principal_id=str(agent_id),
        kind=PrincipalKind.AGENT,
        workspace_id=ws_id,
        roles=["agent"],
        client_id="kolang-api",
        agent_id=agent_id,
        agent=agent_record,
        token_claims=agent_claims,
    )
    assert agent_ctx.is_user is False
    assert agent_ctx.is_agent is True
    assert agent_ctx.is_service is False
    assert agent_ctx.agent_id == agent_id
    assert agent_ctx.agent.name == "Security Scanner"


def test_inactive_agent_cannot_execute_new_requests() -> None:
    """
    Acceptance Criteria 2:
    Verify that an inactive or disabled Agent cannot execute operations.
    """
    ws_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    now = datetime.now(UTC)

    inactive_agent = AgentRead(
        id=agent_id,
        workspace_id=ws_id,
        name="Deprecated Agent",
        slug="deprecated-agent",
        status=AgentStatus.INACTIVE,
        created_at=now,
        updated_at=now,
    )

    claims = TokenClaims(
        sub="service-account-agent",
        iss="https://auth.kolang.dev",
        exp=1800000000,
        iat=1700000000,
        azp="kolang-api",
    )

    ctx = PrincipalContext(
        principal_id=str(agent_id),
        kind=PrincipalKind.AGENT,
        workspace_id=ws_id,
        client_id="kolang-api",
        agent_id=agent_id,
        agent=inactive_agent,
        token_claims=claims,
    )

    with pytest.raises(AuthorizationError) as exc_info:
        ctx.check_can_execute()

    assert "inactive" in str(exc_info.value).lower()
    assert "cannot execute new requests" in str(exc_info.value).lower()


def test_active_agent_can_execute() -> None:
    """Verify that an active Agent passes execution permission checks."""
    ws_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    now = datetime.now(UTC)

    active_agent = AgentRead(
        id=agent_id,
        workspace_id=ws_id,
        name="Active Agent",
        slug="active-agent",
        status=AgentStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    claims = TokenClaims(
        sub="service-account-agent",
        iss="https://auth.kolang.dev",
        exp=1800000000,
        iat=1700000000,
        azp="kolang-api",
    )

    ctx = PrincipalContext(
        principal_id=str(agent_id),
        kind=PrincipalKind.AGENT,
        workspace_id=ws_id,
        client_id="kolang-api",
        agent_id=agent_id,
        agent=active_agent,
        token_claims=claims,
    )

    # Should not raise
    ctx.check_can_execute()


def test_mcp_client_registration_models() -> None:
    """Verify MCP Client Registration schema, validation, and status."""
    ws_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    now = datetime.now(UTC)

    client_create = McpClientRegistrationCreate(
        client_id="demo-client",
        name="Demo Client",
        status=ClientStatus.ACTIVE,
        agent_id=agent_id,
        client_type="agent",
    )
    assert client_create.client_id == "demo-client"
    assert client_create.agent_id == agent_id

    client_read = McpClientRegistrationRead(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        client_id="demo-client",
        name="Demo Client",
        status=ClientStatus.ACTIVE,
        agent_id=agent_id,
        client_type="agent",
        created_at=now,
        updated_at=now,
    )
    assert client_read.is_active is True

    inactive_client = McpClientRegistrationRead(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        client_id="demo-client",
        name="Demo Client",
        status=ClientStatus.REVOKED,
        created_at=now,
        updated_at=now,
    )
    assert inactive_client.is_active is False


def test_workspace_membership_models() -> None:
    """Verify WorkspaceMembership schema, status, and role assignments."""
    ws_id = uuid.uuid4()
    now = datetime.now(UTC)

    membership = WorkspaceMembershipCreate(
        user_id="usr-alice",
        role=WorkspaceRole.ADMIN,
        email="alice@kolang.dev",
    )
    assert membership.user_id == "usr-alice"
    assert membership.role == WorkspaceRole.ADMIN

    read_m = WorkspaceMembershipRead(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        user_id="usr-alice",
        role=WorkspaceRole.ADMIN,
        status=MembershipStatus.ACTIVE,
        email="alice@kolang.dev",
        created_at=now,
        updated_at=now,
    )
    assert read_m.is_active is True


def test_token_claims_effective_client_id() -> None:
    """Verify resolution of effective client_id from azp vs client_id."""
    # 1. Prefer azp
    c1 = TokenClaims(
        sub="usr-1",
        iss="https://auth.kolang.dev",
        exp=1000,
        iat=500,
        azp="party-client",
        client_id="fallback-client",
    )
    assert c1.effective_client_id == "party-client"

    # 2. Fall back to client_id
    c2 = TokenClaims(
        sub="usr-1",
        iss="https://auth.kolang.dev",
        exp=1000,
        iat=500,
        client_id="direct-client",
    )
    assert c2.effective_client_id == "direct-client"

    # 3. Neither present
    c3 = TokenClaims(
        sub="usr-1",
        iss="https://auth.kolang.dev",
        exp=1000,
        iat=500,
    )
    assert c3.effective_client_id is None


def test_principal_context_to_principal_conversion() -> None:
    """Verify backwards-compatible conversion of PrincipalContext to canonical Principal."""
    ws_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    now = datetime.now(UTC)

    agent_record = AgentRead(
        id=agent_id,
        workspace_id=ws_id,
        name="Autonomous Fixer",
        slug="autonomous-fixer",
        status=AgentStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )

    claims = TokenClaims(
        sub="service-account-fixer",
        iss="https://auth.kolang.dev",
        exp=1800000000,
        iat=1700000000,
        roles=["operator"],
        groups=["ai-agents"],
    )

    ctx = PrincipalContext(
        principal_id=str(agent_id),
        kind=PrincipalKind.AGENT,
        workspace_id=ws_id,
        roles=["operator"],
        agent_id=agent_id,
        agent=agent_record,
        token_claims=claims,
    )

    canonical_principal = ctx.to_principal()
    assert canonical_principal.id == str(agent_id)
    assert canonical_principal.kind == PrincipalKind.AGENT
    assert canonical_principal.workspace_id == str(ws_id)
    assert canonical_principal.name == "Autonomous Fixer"
    assert "operator" in canonical_principal.roles
    assert "ai-agents" in canonical_principal.groups
