"""
Identity Domain Service for Kolang ACP (ACP-011).

Provides:
- Workspace-scoped CRUD for Agent Workloads
- Registration and lifecycle management for MCP Clients (IdP integration)
- Workspace Membership management for Human Users
- Cryptographic Token Claim resolution into runtime PrincipalContext
- Strict identity enforcement:
  * Separation of Human User and Agent identities
  * Rejection of unregistered or unknown MCP Clients
  * Inactive Agent execution prevention
  * Complete rejection of header-spoofed identities (e.g. X-Agent-ID)
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    AgentRead,
    AgentStatus,
    AgentUpdate,
    ClientStatus,
    McpClientRegistration,
    McpClientRegistrationCreate,
    McpClientRegistrationRead,
    McpClientRegistrationUpdate,
    MembershipStatus,
    PrincipalContext,
    TokenClaims,
    WorkspaceMembership,
    WorkspaceMembershipCreate,
    WorkspaceMembershipRead,
    WorkspaceMembershipUpdate,
    WorkspaceRole,
)

logger = structlog.get_logger(__name__)

# Header names strictly prohibited from asserting caller identity
UNTRUSTED_IDENTITY_HEADERS: frozenset[str] = frozenset(
    {
        "x-agent-id",
        "x-agent-name",
        "x-user-id",
        "x-user-name",
        "x-principal-id",
        "x-client-id",
    }
)


class IdentityService:
    """
    Domain service for Agent, Client Registration, and Workspace Identity management.

    Enforces workspace isolation, identity type separation, and execution integrity.
    Follows the repository standard pattern: methods receive an active AsyncSession.
    """

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._default_session = session

    def _get_session(self, session: AsyncSession | None) -> AsyncSession:
        active = session or self._default_session
        if active is None:
            msg = "An active database session is required for identity operations."
            raise ValueError(msg)
        return active

    # ── 1. Agent Workload Management ─────────────────────────────────────────

    async def create_agent(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        data: AgentCreate,
    ) -> AgentRead:
        """
        Register a new Agent workload within an organizational workspace.

        Raises:
            ConflictError: If an agent with the same slug already exists in this workspace.
        """
        existing = await self.get_agent_by_slug(session, workspace_id, data.slug)
        if existing is not None:
            msg = f"Agent with slug '{data.slug}' already exists in workspace '{workspace_id}'."
            logger.warning("agent.create_conflict", workspace_id=str(workspace_id), slug=data.slug)
            raise ConflictError(
                msg, details={"workspace_id": str(workspace_id), "slug": data.slug}
            )

        agent = Agent(
            workspace_id=workspace_id,
            name=data.name,
            slug=data.slug,
            description=data.description,
            status=data.status.value,
            owner_id=data.owner_id,
            team=data.team,
            metadata_=data.metadata,
        )
        session.add(agent)
        await session.flush()
        await session.refresh(agent)

        logger.info(
            "agent.created",
            agent_id=str(agent.id),
            workspace_id=str(workspace_id),
            name=agent.name,
            slug=agent.slug,
            status=agent.status,
        )
        return AgentRead.model_validate(agent)

    async def get_agent(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        agent_id: uuid.UUID,
    ) -> AgentRead:
        """
        Retrieve an Agent workload by ID within a workspace.

        Raises:
            NotFoundError: If the agent does not exist or belongs to another workspace.
        """
        stmt = select(Agent).where(Agent.workspace_id == workspace_id, Agent.id == agent_id)
        result = await session.execute(stmt)
        agent = result.scalar_one_or_none()
        if agent is None:
            msg = f"Agent with ID '{agent_id}' not found in workspace '{workspace_id}'."
            raise NotFoundError(
                msg, details={"agent_id": str(agent_id), "workspace_id": str(workspace_id)}
            )
        return AgentRead.model_validate(agent)

    async def get_agent_by_slug(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        slug: str,
    ) -> AgentRead | None:
        """Retrieve an Agent workload by its unique slug within a workspace."""
        stmt = select(Agent).where(Agent.workspace_id == workspace_id, Agent.slug == slug)
        result = await session.execute(stmt)
        agent = result.scalar_one_or_none()
        if agent is None:
            return None
        return AgentRead.model_validate(agent)

    async def list_agents(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> list[AgentRead]:
        """List all Agent workloads registered within a workspace."""
        stmt = select(Agent).where(Agent.workspace_id == workspace_id).order_by(Agent.name)
        result = await session.execute(stmt)
        agents = result.scalars().all()
        return [AgentRead.model_validate(a) for a in agents]

    async def update_agent(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        agent_id: uuid.UUID,
        data: AgentUpdate,
    ) -> AgentRead:
        """
        Update mutable fields of an Agent workload.

        Raises:
            NotFoundError: If the agent is not found.
        """
        stmt = select(Agent).where(Agent.workspace_id == workspace_id, Agent.id == agent_id)
        result = await session.execute(stmt)
        agent = result.scalar_one_or_none()
        if agent is None:
            msg = f"Agent with ID '{agent_id}' not found in workspace '{workspace_id}'."
            raise NotFoundError(msg)

        if data.name is not None:
            agent.name = data.name
        if data.description is not None:
            agent.description = data.description
        if data.status is not None:
            agent.status = data.status.value
        if data.owner_id is not None:
            agent.owner_id = data.owner_id
        if data.team is not None:
            agent.team = data.team
        if data.metadata is not None:
            agent.metadata_ = data.metadata

        await session.flush()
        await session.refresh(agent)
        logger.info("agent.updated", agent_id=str(agent_id), status=agent.status)
        return AgentRead.model_validate(agent)

    async def disable_agent(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        agent_id: uuid.UUID,
    ) -> AgentRead:
        """
        Transition an agent to INACTIVE status, immediately blocking future executions.

        Raises:
            NotFoundError: If agent is not found.
        """
        return await self.update_agent(
            session,
            workspace_id,
            agent_id,
            AgentUpdate(status=AgentStatus.INACTIVE),
        )

    # ── 2. MCP Client Registration Management ────────────────────────────────

    async def register_client(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        data: McpClientRegistrationCreate,
    ) -> McpClientRegistrationRead:
        """
        Register an authorized MCP client ID from the Identity Provider.

        Raises:
            ConflictError: If client_id is already registered in this workspace.
            NotFoundError: If referenced agent_id does not exist in this workspace.
        """
        existing = await self.get_client_by_client_id(session, workspace_id, data.client_id)
        if existing is not None:
            msg = (
                f"Client ID '{data.client_id}' is already registered in "
                f"workspace '{workspace_id}'."
            )
            raise ConflictError(
                msg, details={"client_id": data.client_id, "workspace_id": str(workspace_id)}
            )

        if data.agent_id is not None:
            # Validate agent exists within same workspace
            await self.get_agent(session, workspace_id, data.agent_id)

        client = McpClientRegistration(
            workspace_id=workspace_id,
            client_id=data.client_id,
            name=data.name,
            status=data.status.value,
            agent_id=data.agent_id,
            client_type=data.client_type,
            description=data.description,
            metadata_=data.metadata,
        )
        session.add(client)
        await session.flush()
        await session.refresh(client)

        logger.info(
            "mcp_client.registered",
            client_id=client.client_id,
            workspace_id=str(workspace_id),
            client_type=client.client_type,
            status=client.status,
        )
        return McpClientRegistrationRead.model_validate(client)

    async def get_client_by_client_id(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        client_id: str,
    ) -> McpClientRegistrationRead | None:
        """Retrieve an MCP client registration by its client_id within a workspace."""
        stmt = select(McpClientRegistration).where(
            McpClientRegistration.workspace_id == workspace_id,
            McpClientRegistration.client_id == client_id,
        )
        result = await session.execute(stmt)
        client = result.scalar_one_or_none()
        if client is None:
            return None
        return McpClientRegistrationRead.model_validate(client)

    async def list_clients(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> list[McpClientRegistrationRead]:
        """List all MCP client registrations in a workspace."""
        stmt = (
            select(McpClientRegistration)
            .where(McpClientRegistration.workspace_id == workspace_id)
            .order_by(McpClientRegistration.name)
        )
        result = await session.execute(stmt)
        clients = result.scalars().all()
        return [McpClientRegistrationRead.model_validate(c) for c in clients]

    async def update_client(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        client_id: str,
        data: McpClientRegistrationUpdate,
    ) -> McpClientRegistrationRead:
        """
        Update an MCP client registration.

        Raises:
            NotFoundError: If client is not found.
        """
        stmt = select(McpClientRegistration).where(
            McpClientRegistration.workspace_id == workspace_id,
            McpClientRegistration.client_id == client_id,
        )
        result = await session.execute(stmt)
        client = result.scalar_one_or_none()
        if client is None:
            msg = f"Client registration '{client_id}' not found in workspace '{workspace_id}'."
            raise NotFoundError(msg)

        if data.name is not None:
            client.name = data.name
        if data.status is not None:
            client.status = data.status.value
        if data.agent_id is not None:
            await self.get_agent(session, workspace_id, data.agent_id)
            client.agent_id = data.agent_id
        if data.client_type is not None:
            client.client_type = data.client_type
        if data.description is not None:
            client.description = data.description
        if data.metadata is not None:
            client.metadata_ = data.metadata

        await session.flush()
        await session.refresh(client)
        logger.info("mcp_client.updated", client_id=client.client_id, status=client.status)
        return McpClientRegistrationRead.model_validate(client)

    async def disable_client(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        client_id: str,
    ) -> McpClientRegistrationRead:
        """Disable an MCP client registration."""
        return await self.update_client(
            session,
            workspace_id,
            client_id,
            McpClientRegistrationUpdate(status=ClientStatus.INACTIVE),
        )

    # ── 3. Workspace Membership Management ───────────────────────────────────

    async def create_membership(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        data: WorkspaceMembershipCreate,
    ) -> WorkspaceMembershipRead:
        """
        Associate a human user with a workspace and assign an operational role.

        Raises:
            ConflictError: If user is already a member of this workspace.
        """
        existing = await self.get_membership(session, workspace_id, data.user_id)
        if existing is not None:
            msg = f"User '{data.user_id}' already has a membership in workspace '{workspace_id}'."
            raise ConflictError(msg)

        membership = WorkspaceMembership(
            workspace_id=workspace_id,
            user_id=data.user_id,
            role=data.role.value,
            status=data.status.value,
            email=data.email,
            metadata_=data.metadata,
        )
        session.add(membership)
        await session.flush()
        await session.refresh(membership)

        logger.info(
            "membership.created",
            workspace_id=str(workspace_id),
            user_id=membership.user_id,
            role=membership.role,
        )
        return WorkspaceMembershipRead.model_validate(membership)

    async def get_membership(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: str,
    ) -> WorkspaceMembershipRead | None:
        """Retrieve a user's membership within a workspace."""
        stmt = select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
        result = await session.execute(stmt)
        membership = result.scalar_one_or_none()
        if membership is None:
            return None
        return WorkspaceMembershipRead.model_validate(membership)

    async def list_memberships(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> list[WorkspaceMembershipRead]:
        """List all memberships in a workspace."""
        stmt = (
            select(WorkspaceMembership)
            .where(WorkspaceMembership.workspace_id == workspace_id)
            .order_by(WorkspaceMembership.user_id)
        )
        result = await session.execute(stmt)
        memberships = result.scalars().all()
        return [WorkspaceMembershipRead.model_validate(m) for m in memberships]

    async def update_membership(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
        user_id: str,
        data: WorkspaceMembershipUpdate,
    ) -> WorkspaceMembershipRead:
        """Update a user's role or status in a workspace."""
        stmt = select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == user_id,
        )
        result = await session.execute(stmt)
        membership = result.scalar_one_or_none()
        if membership is None:
            msg = f"Membership for user '{user_id}' not found in workspace '{workspace_id}'."
            raise NotFoundError(msg)

        if data.role is not None:
            membership.role = data.role.value
        if data.status is not None:
            membership.status = data.status.value
        if data.email is not None:
            membership.email = data.email
        if data.metadata is not None:
            membership.metadata_ = data.metadata

        await session.flush()
        await session.refresh(membership)
        return WorkspaceMembershipRead.model_validate(membership)

    # ── 4. Core Runtime Claim Resolution & Identity Enforcement ──────────────

    async def resolve_principal_context(
        self,
        session: AsyncSession,
        claims: TokenClaims,
        workspace_id: uuid.UUID,
        *,
        request_headers: dict[str, str] | None = None,
    ) -> PrincipalContext:
        """
        Translate decoded OIDC token claims into a verified runtime PrincipalContext.

        Enforcement Guarantees:
        1. Complete rejection of header-spoofed identity (e.g. X-Agent-ID, X-User-ID).
           Identity MUST originate from cryptographic token claims.
        2. Strict validation of registered MCP Client ID (azp or client_id claim).
           Unregistered or unknown clients are rejected with AuthenticationError.
        3. Strict discrimination between Human User (USER) and Agent Workload (AGENT).
        4. Inactive or revoked clients or agents are rejected.

        Raises:
            AuthenticationError: If client is unregistered, unknown, or token lacks claims.
            AuthorizationError: If client or agent is inactive/revoked.
        """
        # ── Defensive Check: Reject header spoofing attempts ─────────────────
        if request_headers:
            for header_key in request_headers:
                normalized_key = header_key.lower().strip()
                if normalized_key in UNTRUSTED_IDENTITY_HEADERS:
                    logger.warning(
                        "identity.header_spoofing_attempt_blocked",
                        header=header_key,
                        value=request_headers[header_key],
                        workspace_id=str(workspace_id),
                    )
                    # Strictly never trust identity headers; identity derives solely from claims
                    continue

        # ── 1. Resolve Effective Client ID from Claims ───────────────────────
        client_id = claims.effective_client_id
        if not client_id:
            logger.error("identity.missing_client_id_claim", sub=claims.sub, iss=claims.iss)
            raise AuthenticationError(
                "OIDC token is missing authorized client identifier (azp or client_id claim)."
            )

        # ── 2. Validate MCP Client Registration in Workspace ─────────────────
        client_reg = await self.get_client_by_client_id(session, workspace_id, client_id)
        if client_reg is None:
            logger.warning(
                "identity.unregistered_client_rejected",
                client_id=client_id,
                workspace_id=str(workspace_id),
            )
            msg = (
                f"Client '{client_id}' is unregistered or unrecognized in "
                f"workspace '{workspace_id}'."
            )
            raise AuthenticationError(msg)

        if not client_reg.is_active:
            logger.warning(
                "identity.inactive_client_rejected",
                client_id=client_id,
                status=client_reg.status,
                workspace_id=str(workspace_id),
            )
            raise AuthorizationError(
                f"MCP Client '{client_id}' is {client_reg.status} and cannot execute requests."
            )

        # ── 3. Distinguish Identity Kind (Agent vs Human User) ────────────────
        is_service_account = claims.sub.startswith("service-account-")
        is_agent_client = client_reg.client_type == "agent" or client_reg.agent_id is not None

        if is_agent_client or is_service_account:
            # ── AGENT WORKLOAD IDENTITY ──────────────────────────────────────
            agent: AgentRead | None = None
            if client_reg.agent_id is not None:
                agent = await self.get_agent(session, workspace_id, client_reg.agent_id)
            else:
                # Fallback mapping: try looking up agent by client_id slug
                agent = await self.get_agent_by_slug(session, workspace_id, client_id)

            if agent is None:
                logger.error(
                    "identity.agent_mapping_not_found",
                    client_id=client_id,
                    workspace_id=str(workspace_id),
                )
                raise AuthenticationError(
                    f"Agent workload mapped to client '{client_id}' does not exist in workspace."
                )

            # Check if agent is active
            if not agent.is_active:
                logger.warning(
                    "identity.inactive_agent_rejected",
                    agent_id=str(agent.id),
                    slug=agent.slug,
                    status=agent.status,
                )
                err_msg = (
                    f"Agent '{agent.name}' (id={agent.id}) is {agent.status} and "
                    "cannot execute new requests."
                )
                raise AuthorizationError(err_msg)

            roles = list(claims.roles) if claims.roles else ["agent"]
            principal_ctx = PrincipalContext(
                principal_id=str(agent.id),
                kind=PrincipalKind.AGENT,
                workspace_id=workspace_id,
                roles=roles,
                client_id=client_id,
                agent_id=agent.id,
                agent=agent,
                client=client_reg,
                token_claims=claims,
            )
            logger.info(
                "identity.agent_resolved",
                agent_id=str(agent.id),
                slug=agent.slug,
                client_id=client_id,
                workspace_id=str(workspace_id),
            )
            return principal_ctx

        # ── HUMAN USER IDENTITY ──────────────────────────────────────────────
        user_id = claims.sub
        membership = await self.get_membership(session, workspace_id, user_id)
        if membership is not None and not membership.is_active:
            m_msg = (
                f"User membership for '{user_id}' in workspace '{workspace_id}' is "
                f"{membership.status}."
            )
            raise AuthorizationError(m_msg)

        roles = list(claims.roles)
        if membership is not None and membership.role not in roles:
            roles.append(membership.role)

        principal_ctx = PrincipalContext(
            principal_id=user_id,
            kind=PrincipalKind.USER,
            workspace_id=workspace_id,
            roles=roles,
            client_id=client_id,
            user_id=user_id,
            membership=membership,
            client=client_reg,
            token_claims=claims,
        )
        logger.info(
            "identity.user_resolved",
            user_id=user_id,
            client_id=client_id,
            workspace_id=str(workspace_id),
            roles=roles,
        )
        return principal_ctx

    # ── 5. Demo Seed Helper ──────────────────────────────────────────────────

    async def seed_demo_identities(
        self,
        session: AsyncSession,
        workspace_id: uuid.UUID,
    ) -> dict[str, Any]:
        """
        Seed reference Keycloak client registrations, demo agents, and memberships.

        Maps:
        - Keycloak confidential client 'kolang-api' -> Demo Assistant Agent
        - Keycloak public client 'kolang-web' -> Human User Interface Client
        - Human users 'admin' and 'developer' -> Workspace Memberships
        """
        # 1. Seed Demo Agent
        demo_agent = await self.get_agent_by_slug(session, workspace_id, "demo-agent-reviewer")
        if demo_agent is None:
            demo_agent = await self.create_agent(
                session,
                workspace_id,
                AgentCreate(
                    name="Demo Code Reviewer",
                    slug="demo-agent-reviewer",
                    description="Autonomous code review and security audit agent",
                    status=AgentStatus.ACTIVE,
                    team="platform-engineering",
                ),
            )

        # 2. Seed 'kolang-api' Client Registration (Keycloak Service Account -> Demo Agent)
        api_client = await self.get_client_by_client_id(session, workspace_id, "kolang-api")
        if api_client is None:
            api_client = await self.register_client(
                session,
                workspace_id,
                McpClientRegistrationCreate(
                    client_id="kolang-api",
                    name="Kolang API Service Account Client",
                    status=ClientStatus.ACTIVE,
                    agent_id=demo_agent.id,
                    client_type="agent",
                    description="Keycloak service account client mapped to Demo Agent",
                ),
            )

        # 3. Seed 'kolang-web' Client Registration (Keycloak User Interface Client)
        web_client = await self.get_client_by_client_id(session, workspace_id, "kolang-web")
        if web_client is None:
            web_client = await self.register_client(
                session,
                workspace_id,
                McpClientRegistrationCreate(
                    client_id="kolang-web",
                    name="Kolang Web Admin Dashboard",
                    status=ClientStatus.ACTIVE,
                    client_type="user_interface",
                    description="Keycloak public OIDC client for human users",
                ),
            )

        # 4. Seed Human User Memberships (admin, developer)
        admin_membership = await self.get_membership(session, workspace_id, "admin")
        if admin_membership is None:
            admin_membership = await self.create_membership(
                session,
                workspace_id,
                WorkspaceMembershipCreate(
                    user_id="admin",
                    role=WorkspaceRole.ADMIN,
                    status=MembershipStatus.ACTIVE,
                    email="admin@kolang.dev",
                ),
            )

        dev_membership = await self.get_membership(session, workspace_id, "developer")
        if dev_membership is None:
            dev_membership = await self.create_membership(
                session,
                workspace_id,
                WorkspaceMembershipCreate(
                    user_id="developer",
                    role=WorkspaceRole.DEVELOPER,
                    status=MembershipStatus.ACTIVE,
                    email="dev@kolang.dev",
                ),
            )

        return {
            "demo_agent": demo_agent,
            "api_client": api_client,
            "web_client": web_client,
            "admin_membership": admin_membership,
            "dev_membership": dev_membership,
        }
