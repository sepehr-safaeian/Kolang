"""
Kolang Workspaces Package.

Provides the organizational multi-tenancy boundary, Workspace domain entity,
SQLAlchemy ORM models, Service Layer, Demo Seeding, and Tenant Scoping enforcement.
"""

from __future__ import annotations

from acp_core.workspaces.models import (
    Workspace,
    WorkspaceBase,
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceStatus,
    WorkspaceUpdate,
)
from acp_core.workspaces.scoped_services import (
    ScopedPolicyService,
    ScopedServerService,
)
from acp_core.workspaces.scoping import (
    TenantContext,
    enforce_resource_scope,
    extract_tenant_context,
    resolve_trusted_workspace_id,
)
from acp_core.workspaces.seed import (
    DEMO_WORKSPACE_DESCRIPTION,
    DEMO_WORKSPACE_ID,
    DEMO_WORKSPACE_NAME,
    DEMO_WORKSPACE_SLUG,
    seed_demo_workspace,
)
from acp_core.workspaces.service import WorkspaceService

__all__ = [
    "DEMO_WORKSPACE_DESCRIPTION",
    "DEMO_WORKSPACE_ID",
    "DEMO_WORKSPACE_NAME",
    "DEMO_WORKSPACE_SLUG",
    "ScopedPolicyService",
    "ScopedServerService",
    "TenantContext",
    "Workspace",
    "WorkspaceBase",
    "WorkspaceCreate",
    "WorkspaceRead",
    "WorkspaceService",
    "WorkspaceStatus",
    "WorkspaceUpdate",
    "enforce_resource_scope",
    "extract_tenant_context",
    "resolve_trusted_workspace_id",
    "seed_demo_workspace",
]
