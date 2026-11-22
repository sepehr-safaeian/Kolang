"""
Service Layer Tenant Scoping for Server and Policy domains (ACP-008).

Enforces strict tenant isolation and IDOR protection in the backend Service Layer:
- Guarantees queries for servers and policies are scoped to the caller's TenantContext.
- Prevents cross-workspace reading, updating, or deleting of servers and policies.
- Detects and rejects body payload tampering (when a client attempts to supply
  a workspace_id differing from the authenticated TenantContext).
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from acp_core.common.errors import NotFoundError
from acp_core.common.types import PolicyId, WorkspaceId
from acp_core.policy.models import PolicyEffect, PolicyRule
from acp_core.protocol.models import HealthStatus, ServerDescriptor, TransportType
from acp_core.workspaces.scoping import (
    TenantContext,
    enforce_resource_scope,
    resolve_trusted_workspace_id,
)

logger = structlog.get_logger(__name__)


# ── Scoped Server Service ────────────────────────────────────────────────────


class ScopedServerService:
    """
    Service Layer manager for MCP Servers with strict tenant scoping.

    Maintains server records in an isolated, workspace-partitioned store.
    All read and mutation operations require a verified TenantContext.
    """

    def __init__(self) -> None:
        # In-memory store keyed by (workspace_id_str, server_id)
        self._servers: dict[tuple[str, str], ServerDescriptor] = {}

    def register_server(
        self,
        tenant_ctx: TenantContext,
        server_id: str,
        name: str,
        endpoint: str,
        transport: TransportType = TransportType.STREAMABLE_HTTP,
        body_workspace_id: str | uuid.UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ServerDescriptor:
        """
        Register an upstream MCP server scoped to the caller's workspace.

        Enforces that any body_workspace_id must match tenant_ctx (Rule 2).
        """
        trusted_ws_id = resolve_trusted_workspace_id(tenant_ctx, body_workspace_id)
        ws_str = str(trusted_ws_id)

        descriptor = ServerDescriptor(
            server_id=server_id,
            name=name,
            endpoint=endpoint,
            workspace_id=ws_str,
            transport=transport,
            health_status=HealthStatus.UNKNOWN,
            metadata=metadata or {},
        )
        self._servers[(ws_str, server_id)] = descriptor
        logger.info(
            "server.registered",
            workspace_id=ws_str,
            server_id=server_id,
        )
        return descriptor

    def get_server(
        self,
        tenant_ctx: TenantContext,
        server_id: str,
    ) -> ServerDescriptor:
        """
        Retrieve a server descriptor within the caller's workspace scope.

        Raises NotFoundError if the server does not exist in the caller's workspace,
        even if it exists in another workspace (preventing IDOR enumeration).
        """
        key = (tenant_ctx.workspace_id_str, server_id)
        server = self._servers.get(key)
        if server is None:
            # Check if it exists in another workspace for security logging
            exists_elsewhere = any(s_id == server_id for (_, s_id) in self._servers)
            if exists_elsewhere:
                logger.warning(
                    "security.idor_server_access_blocked",
                    caller_workspace=tenant_ctx.workspace_id_str,
                    attempted_server_id=server_id,
                    principal_id=tenant_ctx.principal_id,
                )
            raise NotFoundError(f"Server '{server_id}' not found.")

        enforce_resource_scope(tenant_ctx, server.workspace_id, resource_type="server")
        return server

    def list_servers(
        self,
        tenant_ctx: TenantContext,
    ) -> list[ServerDescriptor]:
        """
        List all servers belonging strictly to the caller's workspace.

        Guarantees zero cross-workspace information leakage.
        """
        return [
            s for (ws_str, _), s in self._servers.items() if ws_str == tenant_ctx.workspace_id_str
        ]

    def update_server(
        self,
        tenant_ctx: TenantContext,
        server_id: str,
        name: str | None = None,
        endpoint: str | None = None,
        body_workspace_id: str | uuid.UUID | None = None,
    ) -> ServerDescriptor:
        """Update an existing server within the caller's tenant boundary."""
        resolve_trusted_workspace_id(tenant_ctx, body_workspace_id)
        current = self.get_server(tenant_ctx, server_id)

        updated = ServerDescriptor(
            server_id=current.server_id,
            name=name if name is not None else current.name,
            endpoint=endpoint if endpoint is not None else current.endpoint,
            workspace_id=current.workspace_id,
            transport=current.transport,
            health_status=current.health_status,
            tools=current.tools,
            metadata=current.metadata,
        )
        self._servers[(tenant_ctx.workspace_id_str, server_id)] = updated
        return updated

    def delete_server(
        self,
        tenant_ctx: TenantContext,
        server_id: str,
    ) -> None:
        """Delete a server from the caller's workspace."""
        self.get_server(tenant_ctx, server_id)  # Enforces ownership / raises NotFoundError
        self._servers.pop((tenant_ctx.workspace_id_str, server_id), None)


# ── Scoped Policy Service ────────────────────────────────────────────────────


class ScopedPolicyService:
    """
    Service Layer manager for Access Control Policies with strict tenant scoping.

    Guarantees policies are authored, evaluated, and queried strictly within
    the organizational workspace boundary.
    """

    def __init__(self) -> None:
        # In-memory store keyed by (workspace_id_str, policy_id)
        self._policies: dict[tuple[str, str], PolicyRule] = {}

    def create_policy(
        self,
        tenant_ctx: TenantContext,
        policy_id: PolicyId | str,
        name: str,
        effect: PolicyEffect,
        tools: list[str] | None = None,
        servers: list[str] | None = None,
        principals: list[str] | None = None,
        body_workspace_id: str | uuid.UUID | None = None,
        description: str = "",
        priority: int = 0,
        enabled: bool = True,
    ) -> PolicyRule:
        """
        Create an access control policy scoped to the caller's workspace.

        Enforces that any body_workspace_id must match tenant_ctx (Rule 2).
        """
        trusted_ws_id = resolve_trusted_workspace_id(tenant_ctx, body_workspace_id)
        ws_str = str(trusted_ws_id)
        p_id = PolicyId(str(policy_id))

        rule = PolicyRule(
            id=p_id,
            workspace_id=WorkspaceId(ws_str),
            name=name,
            description=description,
            effect=effect,
            tools=tools or [],
            servers=servers or [],
            principals=principals or [],
            priority=priority,
            enabled=enabled,
        )
        self._policies[(ws_str, str(p_id))] = rule
        logger.info(
            "policy.created",
            workspace_id=ws_str,
            policy_id=str(p_id),
            effect=effect.value,
        )
        return rule

    def get_policy(
        self,
        tenant_ctx: TenantContext,
        policy_id: PolicyId | str,
    ) -> PolicyRule:
        """
        Retrieve a policy rule within the caller's workspace scope.

        Raises NotFoundError if the policy does not exist in caller's workspace
        (preventing IDOR enumeration across tenants).
        """
        pid_str = str(policy_id)
        key = (tenant_ctx.workspace_id_str, pid_str)
        policy = self._policies.get(key)
        if policy is None:
            # Check if it exists in another workspace for security logging
            exists_elsewhere = any(p_id == pid_str for (_, p_id) in self._policies)
            if exists_elsewhere:
                logger.warning(
                    "security.idor_policy_access_blocked",
                    caller_workspace=tenant_ctx.workspace_id_str,
                    attempted_policy_id=pid_str,
                    principal_id=tenant_ctx.principal_id,
                )
            raise NotFoundError(f"Policy '{pid_str}' not found.")

        enforce_resource_scope(tenant_ctx, policy.workspace_id, resource_type="policy")
        return policy

    def list_policies(
        self,
        tenant_ctx: TenantContext,
    ) -> list[PolicyRule]:
        """
        List all policies belonging strictly to the caller's workspace.
        """
        return [
            p for (ws_str, _), p in self._policies.items() if ws_str == tenant_ctx.workspace_id_str
        ]

    def update_policy(
        self,
        tenant_ctx: TenantContext,
        policy_id: PolicyId | str,
        name: str | None = None,
        enabled: bool | None = None,
        body_workspace_id: str | uuid.UUID | None = None,
    ) -> PolicyRule:
        """Update an existing policy within caller's workspace boundary."""
        resolve_trusted_workspace_id(tenant_ctx, body_workspace_id)
        current = self.get_policy(tenant_ctx, policy_id)

        updated = PolicyRule(
            id=current.id,
            workspace_id=current.workspace_id,
            name=name if name is not None else current.name,
            description=current.description,
            effect=current.effect,
            principals=current.principals,
            servers=current.servers,
            tools=current.tools,
            conditions=current.conditions,
            priority=current.priority,
            enabled=enabled if enabled is not None else current.enabled,
            created_at=current.created_at,
        )
        self._policies[(tenant_ctx.workspace_id_str, str(current.id))] = updated
        return updated

    def delete_policy(
        self,
        tenant_ctx: TenantContext,
        policy_id: PolicyId | str,
    ) -> None:
        """Delete a policy from caller's workspace."""
        self.get_policy(tenant_ctx, policy_id)  # Enforces ownership / raises NotFoundError
        self._policies.pop((tenant_ctx.workspace_id_str, str(policy_id)), None)
