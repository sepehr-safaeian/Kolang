"""
Principal identity, agent workload, and MCP client management for Kolang ACP (ACP-011).

Handles authentication of agents, users, and services through
OIDC token validation, principal resolution, and tenant-scoped identity management.
"""

from __future__ import annotations

from acp_core.identity.models import (
    Agent,
    AgentBase,
    AgentCreate,
    AgentRead,
    AgentStatus,
    AgentUpdate,
    AuthContext,
    ClientStatus,
    McpClientRegistration,
    McpClientRegistrationBase,
    McpClientRegistrationCreate,
    McpClientRegistrationRead,
    McpClientRegistrationUpdate,
    MembershipStatus,
    Principal,
    PrincipalContext,
    TokenClaims,
    WorkspaceMembership,
    WorkspaceMembershipBase,
    WorkspaceMembershipCreate,
    WorkspaceMembershipRead,
    WorkspaceMembershipUpdate,
    WorkspaceRole,
)
from acp_core.identity.service import (
    UNTRUSTED_IDENTITY_HEADERS,
    IdentityService,
)

__all__ = [
    "UNTRUSTED_IDENTITY_HEADERS",
    "Agent",
    "AgentBase",
    "AgentCreate",
    "AgentRead",
    "AgentStatus",
    "AgentUpdate",
    "AuthContext",
    "ClientStatus",
    "IdentityService",
    "McpClientRegistration",
    "McpClientRegistrationBase",
    "McpClientRegistrationCreate",
    "McpClientRegistrationRead",
    "McpClientRegistrationUpdate",
    "MembershipStatus",
    "Principal",
    "PrincipalContext",
    "TokenClaims",
    "WorkspaceMembership",
    "WorkspaceMembershipBase",
    "WorkspaceMembershipCreate",
    "WorkspaceMembershipRead",
    "WorkspaceMembershipUpdate",
    "WorkspaceRole",
]
