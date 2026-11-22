"""
Tenant Scoping and Isolation Enforcement for Kolang.

Implements the core security boundary separating organizational tenants:
- Extracts trusted workspace scope from the authenticated Principal / Request Context.
- Disallows trusting unverified body payloads (preventing tenant spoofing & IDOR).
- Provides Service-Layer enforcement primitives to ensure queries and mutations
  are strictly bounded by tenant ownership.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import structlog

from acp_core.common.context import get_request_context_or_none
from acp_core.common.errors import AuthorizationError, NotFoundError

logger = structlog.get_logger(__name__)


def _to_uuid(val: str | uuid.UUID) -> uuid.UUID:
    """Safely coerce a string or UUID into a standard UUID instance."""
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except (ValueError, AttributeError) as exc:
        msg = f"Invalid workspace UUID format: '{val}'"
        raise AuthorizationError(msg) from exc


@dataclass(frozen=True, slots=True)
class TenantContext:
    """
    Verified tenant context governing the execution of the current request.

    Derived exclusively from an authenticated and verified Principal or secured
    middleware context. Never constructed directly from untrusted client inputs.
    """

    workspace_id: uuid.UUID
    principal_id: str | None = None
    workspace_slug: str | None = None
    roles: tuple[str, ...] = field(default_factory=tuple)

    @property
    def workspace_id_str(self) -> str:
        """String representation of the tenant workspace UUID."""
        return str(self.workspace_id)

    def matches(self, other_workspace_id: str | uuid.UUID | None) -> bool:
        """Check if another workspace ID matches this tenant context."""
        if other_workspace_id is None:
            return False
        try:
            return self.workspace_id == _to_uuid(other_workspace_id)
        except AuthorizationError:
            return False


def extract_tenant_context() -> TenantContext:
    """
    Extract verified tenant context from the active RequestContext.

    Prioritizes the authenticated Principal in the Request Context. If neither a
    Principal nor a valid workspace_id is bound, an AuthorizationError is raised.

    Returns:
        Verified TenantContext instance.

    Raises:
        AuthorizationError: If request context is missing or lacks tenant identity.
    """
    ctx = get_request_context_or_none()
    if ctx is None:
        logger.error("tenant.missing_request_context")
        raise AuthorizationError(
            "Request execution halted: missing request context. "
            "Ensure request passed through authentication and context middleware."
        )

    # 1. Derive from verified Principal if attached
    if ctx.principal is not None:
        p = ctx.principal
        raw_ws = getattr(p, "workspace_id", None)
        if raw_ws:
            ws_uuid = _to_uuid(str(raw_ws))
            p_id = str(getattr(p, "id", "")) or None
            p_roles = tuple(getattr(p, "roles", []))
            return TenantContext(
                workspace_id=ws_uuid,
                principal_id=p_id,
                roles=p_roles,
            )

    # 2. Fall back to context workspace_id if established by middleware / scope
    if ctx.workspace_id:
        ws_uuid = _to_uuid(ctx.workspace_id)
        return TenantContext(workspace_id=ws_uuid)

    logger.warning("tenant.missing_workspace_scope", request_id=ctx.request_id)
    raise AuthorizationError(
        "Active tenant workspace context required. "
        "Operation cannot be performed without an established workspace boundary."
    )


def resolve_trusted_workspace_id(
    tenant_ctx: TenantContext,
    body_workspace_id: str | uuid.UUID | None = None,
) -> uuid.UUID:
    """
    Enforce Rule 2: Never trust workspace_id sent in the request body alone.

    If a client sends an explicit workspace_id in the body, it must strictly match
    the authenticated TenantContext. If there is a mismatch, execution is aborted
    with an AuthorizationError to prevent cross-workspace tampering or IDOR attacks.

    Args:
        tenant_ctx: Authenticated tenant context.
        body_workspace_id: Optional workspace_id supplied in JSON body.

    Returns:
        The trusted workspace UUID from tenant_ctx.

    Raises:
        AuthorizationError: If body_workspace_id does not match tenant_ctx.
    """
    if body_workspace_id is None:
        return tenant_ctx.workspace_id

    try:
        body_uuid = _to_uuid(body_workspace_id)
    except AuthorizationError as exc:
        logger.warning(
            "tenant.invalid_body_workspace_format",
            attempted=str(body_workspace_id),
            expected=tenant_ctx.workspace_id_str,
        )
        raise AuthorizationError(
            "Invalid workspace identifier format in request payload."
        ) from exc

    if body_uuid != tenant_ctx.workspace_id:
        logger.security_warning(
            "tenant.cross_workspace_tampering_detected",
            principal_id=tenant_ctx.principal_id,
            context_workspace=tenant_ctx.workspace_id_str,
            payload_workspace=str(body_uuid),
        ) if hasattr(logger, "security_warning") else logger.warning(
            "tenant.cross_workspace_tampering_detected",
            principal_id=tenant_ctx.principal_id,
            context_workspace=tenant_ctx.workspace_id_str,
            payload_workspace=str(body_uuid),
        )
        raise AuthorizationError(
            "Cross-workspace access denied: payload workspace does not match "
            "active authenticated tenant context."
        )

    return tenant_ctx.workspace_id


def enforce_resource_scope(
    tenant_ctx: TenantContext,
    resource_workspace_id: str | uuid.UUID,
    resource_type: str = "resource",
) -> None:
    """
    Verify that an existing resource belongs to the current tenant scope.

    For security and IDOR prevention, cross-tenant attempts raise NotFoundError
    rather than leaking resource existence or permissions.

    Args:
        tenant_ctx: Authenticated tenant context.
        resource_workspace_id: The workspace_id stored on the target entity.
        resource_type: Human-readable noun for the resource type.

    Raises:
        NotFoundError: If resource belongs to a different workspace.
    """
    if not tenant_ctx.matches(resource_workspace_id):
        logger.warning(
            "tenant.cross_workspace_access_blocked",
            resource_type=resource_type,
            caller_workspace=tenant_ctx.workspace_id_str,
            target_workspace=str(resource_workspace_id),
            principal_id=tenant_ctx.principal_id,
        )
        # Return 404 to avoid leaking existence of another tenant's resource
        raise NotFoundError(f"{resource_type.capitalize()} not found.")
