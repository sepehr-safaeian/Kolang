"""
Unit tests for IdentityService domain logic, claim resolution, and security enforcement (ACP-011).

Verifies:
1. Acceptance Criteria 1: Human User and Agent are distinct identity kinds.
2. Acceptance Criteria 2: Inactive Agent cannot execute new requests.
3. Acceptance Criteria 3: Unregistered or unknown Client is rejected with AuthenticationError.
4. Acceptance Criteria 4: No identity is accepted from untrusted headers (X-Agent-ID).
5. Agent workload CRUD operations and slug uniqueness.
6. MCP client registration and mapping to Agent workloads.
7. Workspace membership management for human users.
8. Demo mapping: Keycloak service account (kolang-api) and user client (kolang-web).
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from acp_core.common.errors import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
)
from acp_core.common.types import PrincipalKind
from acp_core.identity.models import (
    Agent,
    AgentCreate,
    AgentStatus,
    ClientStatus,
    McpClientRegistration,
    MembershipStatus,
    TokenClaims,
    WorkspaceMembership,
    WorkspaceRole,
)
from acp_core.identity.service import IdentityService


@pytest.mark.asyncio
async def test_create_agent_duplicate_slug_conflict() -> None:
    """Verify ConflictError when creating an agent with an existing slug in the workspace."""
    service = IdentityService()
    session = AsyncMock()

    ws_id = uuid.uuid4()
    existing_agent = Agent(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        name="Existing Agent",
        slug="duplicate-agent",
        description="",
        status=AgentStatus.ACTIVE.value,
        metadata_={},
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_agent
    session.execute.return_value = mock_result

    payload = AgentCreate(
        name="New Agent",
        slug="duplicate-agent",
        description="Duplicate slug test",
    )

    with pytest.raises(ConflictError, match="already exists"):
        await service.create_agent(session=session, workspace_id=ws_id, data=payload)


@pytest.mark.asyncio
async def test_get_agent_not_found() -> None:
    """Verify NotFoundError when retrieving a non-existent agent."""
    service = IdentityService()
    session = AsyncMock()

    ws_id = uuid.uuid4()
    agent_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    with pytest.raises(NotFoundError, match="not found"):
        await service.get_agent(session=session, workspace_id=ws_id, agent_id=agent_id)


@pytest.mark.asyncio
async def test_resolve_principal_context_rejects_missing_client_id() -> None:
    """Verify AuthenticationError when token lacks both azp and client_id claims."""
    service = IdentityService()
    session = AsyncMock()
    ws_id = uuid.uuid4()

    claims = TokenClaims(
        sub="usr-anonymous",
        iss="https://auth.kolang.dev",
        exp=1800000000,
        iat=1700000000,
        azp=None,
        client_id=None,
    )

    with pytest.raises(AuthenticationError, match="missing authorized client identifier"):
        await service.resolve_principal_context(session=session, claims=claims, workspace_id=ws_id)


@pytest.mark.asyncio
async def test_acceptance_criteria_3_unregistered_client_rejected() -> None:
    """
    Acceptance Criteria 3:
    Client ثبت‌نشده یا ناشناخته رد می‌شود.
    Verify that an unregistered or unknown client ID is rejected with AuthenticationError.
    """
    service = IdentityService()
    session = AsyncMock()
    ws_id = uuid.uuid4()

    claims = TokenClaims(
        sub="service-account-rogue",
        iss="https://auth.kolang.dev",
        exp=1800000000,
        iat=1700000000,
        azp="rogue-unknown-client",
    )

    # Database returns None for client lookup
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    with pytest.raises(AuthenticationError) as exc_info:
        await service.resolve_principal_context(session=session, claims=claims, workspace_id=ws_id)

    assert "unregistered or unrecognized" in str(exc_info.value).lower()
    assert "rogue-unknown-client" in str(exc_info.value)


@pytest.mark.asyncio
async def test_inactive_client_rejected() -> None:
    """Verify that an inactive/revoked client is rejected with AuthorizationError."""
    service = IdentityService()
    session = AsyncMock()
    ws_id = uuid.uuid4()

    claims = TokenClaims(
        sub="service-account-revoked",
        iss="https://auth.kolang.dev",
        exp=1800000000,
        iat=1700000000,
        azp="revoked-client",
    )

    client_record = McpClientRegistration(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        client_id="revoked-client",
        name="Revoked Client",
        description="",
        status=ClientStatus.REVOKED.value,
        client_type="agent",
        metadata_={},
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = client_record
    session.execute.return_value = mock_result

    with pytest.raises(AuthorizationError) as exc_info:
        await service.resolve_principal_context(session=session, claims=claims, workspace_id=ws_id)

    assert "revoked" in str(exc_info.value).lower()
    assert "cannot execute requests" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_acceptance_criteria_2_inactive_agent_cannot_execute() -> None:
    """
    Acceptance Criteria 2:
    Agent غیرفعال نمی‌تواند درخواست جدید اجرا کند.
    Verify that an inactive Agent workload mapped to a valid client is rejected.
    """
    service = IdentityService()
    session = AsyncMock()
    ws_id = uuid.uuid4()
    agent_id = uuid.uuid4()

    claims = TokenClaims(
        sub="service-account-kolang-api",
        iss="https://auth.kolang.dev",
        exp=1800000000,
        iat=1700000000,
        azp="kolang-api",
    )

    client_record = McpClientRegistration(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        client_id="kolang-api",
        name="Kolang API Client",
        description="",
        status=ClientStatus.ACTIVE.value,
        agent_id=agent_id,
        client_type="agent",
        metadata_={},
    )

    inactive_agent = Agent(
        id=agent_id,
        workspace_id=ws_id,
        name="Disabled Agent",
        slug="disabled-agent",
        description="",
        status=AgentStatus.INACTIVE.value,
        metadata_={},
    )

    # 1st execute: client lookup; 2nd execute: agent lookup
    mock_client_res = MagicMock()
    mock_client_res.scalar_one_or_none.return_value = client_record

    mock_agent_res = MagicMock()
    mock_agent_res.scalar_one_or_none.return_value = inactive_agent

    session.execute.side_effect = [mock_client_res, mock_agent_res]

    with pytest.raises(AuthorizationError) as exc_info:
        await service.resolve_principal_context(session=session, claims=claims, workspace_id=ws_id)

    assert "inactive" in str(exc_info.value).lower()
    assert "cannot execute new requests" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_acceptance_criteria_1_and_demo_mapping_agent() -> None:
    """
    Acceptance Criteria 1:
    Human User و Agent دو نوع هویت مجزا دارند.
    Verify mapping Keycloak service account (kolang-api) to an AGENT PrincipalContext.
    """
    service = IdentityService()
    session = AsyncMock()
    ws_id = uuid.uuid4()
    agent_id = uuid.uuid4()

    claims = TokenClaims(
        sub="service-account-kolang-api",
        iss="https://auth.kolang.dev",
        exp=1800000000,
        iat=1700000000,
        azp="kolang-api",
        roles=["operator"],
    )

    client_record = McpClientRegistration(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        client_id="kolang-api",
        name="Kolang API Client",
        description="",
        status=ClientStatus.ACTIVE.value,
        agent_id=agent_id,
        client_type="agent",
        metadata_={},
    )

    active_agent = Agent(
        id=agent_id,
        workspace_id=ws_id,
        name="Demo Code Reviewer",
        slug="demo-agent-reviewer",
        description="",
        status=AgentStatus.ACTIVE.value,
        metadata_={},
    )

    mock_client_res = MagicMock()
    mock_client_res.scalar_one_or_none.return_value = client_record

    mock_agent_res = MagicMock()
    mock_agent_res.scalar_one_or_none.return_value = active_agent

    session.execute.side_effect = [mock_client_res, mock_agent_res]

    principal_ctx = await service.resolve_principal_context(
        session=session,
        claims=claims,
        workspace_id=ws_id,
    )

    assert principal_ctx.kind == PrincipalKind.AGENT
    assert principal_ctx.is_agent is True
    assert principal_ctx.is_user is False
    assert principal_ctx.principal_id == str(agent_id)
    assert principal_ctx.agent_id == agent_id
    assert principal_ctx.agent is not None
    assert principal_ctx.agent.name == "Demo Code Reviewer"
    # Should be able to execute without error
    principal_ctx.check_can_execute()


@pytest.mark.asyncio
async def test_acceptance_criteria_1_and_demo_mapping_human_user() -> None:
    """
    Acceptance Criteria 1:
    Human User و Agent دو نوع هویت مجزا دارند.
    Verify mapping Keycloak web client (kolang-web) and user token to a USER PrincipalContext.
    """
    service = IdentityService()
    session = AsyncMock()
    ws_id = uuid.uuid4()

    claims = TokenClaims(
        sub="usr-alice",
        iss="https://auth.kolang.dev",
        exp=1800000000,
        iat=1700000000,
        azp="kolang-web",
        roles=["developer"],
        email="alice@kolang.dev",
        preferred_username="alice",
    )

    web_client_record = McpClientRegistration(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        client_id="kolang-web",
        name="Kolang Web Client",
        description="",
        status=ClientStatus.ACTIVE.value,
        agent_id=None,
        client_type="user_interface",
        metadata_={},
    )

    membership_record = WorkspaceMembership(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        user_id="usr-alice",
        role=WorkspaceRole.ADMIN.value,
        status=MembershipStatus.ACTIVE.value,
        email="alice@kolang.dev",
        metadata_={},
    )

    mock_client_res = MagicMock()
    mock_client_res.scalar_one_or_none.return_value = web_client_record

    mock_membership_res = MagicMock()
    mock_membership_res.scalar_one_or_none.return_value = membership_record

    session.execute.side_effect = [mock_client_res, mock_membership_res]

    principal_ctx = await service.resolve_principal_context(
        session=session,
        claims=claims,
        workspace_id=ws_id,
    )

    assert principal_ctx.kind == PrincipalKind.USER
    assert principal_ctx.is_user is True
    assert principal_ctx.is_agent is False
    assert principal_ctx.user_id == "usr-alice"
    assert principal_ctx.agent_id is None
    assert principal_ctx.agent is None
    assert principal_ctx.membership is not None
    assert principal_ctx.membership.role == WorkspaceRole.ADMIN
    assert "admin" in principal_ctx.roles
    principal_ctx.check_can_execute()


@pytest.mark.asyncio
async def test_acceptance_criteria_4_no_identity_from_header() -> None:
    """
    Acceptance Criteria 4:
    هیچ هویت صرفاً از نام ارسالی در Header پذیرفته نمی‌شود.
    Verify that untrusted headers (e.g. X-Agent-ID, X-User-ID) cannot spoof identity.
    Identity is strictly derived from the validated cryptographic token claims.
    """
    service = IdentityService()
    session = AsyncMock()
    ws_id = uuid.uuid4()
    real_agent_id = uuid.uuid4()
    spoofed_agent_id = uuid.uuid4()

    claims = TokenClaims(
        sub="service-account-kolang-api",
        iss="https://auth.kolang.dev",
        exp=1800000000,
        iat=1700000000,
        azp="kolang-api",
    )

    client_record = McpClientRegistration(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        client_id="kolang-api",
        name="Kolang API Client",
        description="",
        status=ClientStatus.ACTIVE.value,
        agent_id=real_agent_id,
        client_type="agent",
        metadata_={},
    )

    active_agent = Agent(
        id=real_agent_id,
        workspace_id=ws_id,
        name="Legitimate Agent",
        slug="legitimate-agent",
        description="",
        status=AgentStatus.ACTIVE.value,
        metadata_={},
    )

    mock_client_res = MagicMock()
    mock_client_res.scalar_one_or_none.return_value = client_record

    mock_agent_res = MagicMock()
    mock_agent_res.scalar_one_or_none.return_value = active_agent

    session.execute.side_effect = [mock_client_res, mock_agent_res]

    # Attacker passes spoofed header
    untrusted_headers = {
        "X-Agent-ID": str(spoofed_agent_id),
        "X-Agent-Name": "Spoofed-Super-Admin",
        "X-User-ID": "admin",
    }

    principal_ctx = await service.resolve_principal_context(
        session=session,
        claims=claims,
        workspace_id=ws_id,
        request_headers=untrusted_headers,
    )

    # Principal context MUST match the token claims and DB record, NOT the spoofed header!
    assert principal_ctx.agent_id == real_agent_id
    assert principal_ctx.principal_id == str(real_agent_id)
    assert principal_ctx.agent is not None
    assert principal_ctx.agent.name == "Legitimate Agent"
    assert principal_ctx.agent_id != spoofed_agent_id
    assert principal_ctx.user_id != "admin"
