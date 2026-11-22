"""
Unit tests for PolicyService domain logic, draft/publish lifecycle, and scoping (ACP-012).

Verifies:
1. Policy Draft creation with status=DRAFT and active_version_id=None.
2. Prevention of duplicate policy slugs within the same workspace (ConflictError).
3. Updating draft Rego source without modifying published versions.
4. Version publishing: sequential version numbering, checksum computation, and status=ACTIVE.
5. Previous version retention: historical versions remain after publishing new versions.
6. Gateway enforcement: Draft policies return None for PDP evaluation (Rule 3).
7. Cross-workspace IDOR protection: foreign workspace queries raise NotFoundError (Rule 4).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from acp_core.common.errors import ConflictError, NotFoundError, ValidationError
from acp_core.policy.models import (
    Policy,
    PolicyCreate,
    PolicyDraftUpdate,
    PolicyPublishRequest,
    PolicyStatus,
    PolicyVersion,
    PolicyVersionStatus,
    compute_policy_checksum,
)
from acp_core.policy.service import PolicyService


@pytest.mark.asyncio
async def test_create_policy_draft_success() -> None:
    """Verify creating a policy draft initializes with status=DRAFT and no active version."""
    service = PolicyService()
    session = AsyncMock()
    session.add = MagicMock()

    ws_id = uuid.uuid4()
    payload = PolicyCreate(
        name="MCP Access Rule",
        slug="mcp-access-rule",
        description="Controls access to upstream tools",
        draft_rego="package kolang.authz\ndefault allow := false",
        created_by="admin@kolang.local",
    )

    # 1. ws check: exists
    mock_ws_result = MagicMock()
    mock_ws_result.scalar_one_or_none.return_value = ws_id

    # 2. slug check: none
    mock_slug_result = MagicMock()
    mock_slug_result.scalar_one_or_none.return_value = None

    session.execute.side_effect = [mock_ws_result, mock_slug_result]

    result = await service.create_policy_draft(
        workspace_id=ws_id,
        payload=payload,
        session=session,
    )

    assert result.name == "MCP Access Rule"
    assert result.slug == "mcp-access-rule"
    assert result.status == PolicyStatus.DRAFT
    assert result.is_draft is True
    assert result.is_active is False
    assert result.active_version_id is None
    assert result.active_version_number is None
    assert result.draft_rego == "package kolang.authz\ndefault allow := false"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_policy_draft_workspace_not_found() -> None:
    """Verify NotFoundError when workspace does not exist."""
    service = PolicyService()
    session = AsyncMock()

    ws_id = uuid.uuid4()
    payload = PolicyCreate(
        name="MCP Access Rule",
        slug="mcp-access-rule",
        created_by="admin@kolang.local",
    )

    mock_ws_result = MagicMock()
    mock_ws_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_ws_result

    with pytest.raises(NotFoundError, match=r"Workspace .* not found"):
        await service.create_policy_draft(
            workspace_id=ws_id,
            payload=payload,
            session=session,
        )


@pytest.mark.asyncio
async def test_create_policy_draft_duplicate_slug_conflict() -> None:
    """Verify ConflictError when slug already exists within the workspace."""
    service = PolicyService()
    session = AsyncMock()

    ws_id = uuid.uuid4()
    payload = PolicyCreate(
        name="MCP Access Rule",
        slug="duplicate-slug",
        created_by="admin@kolang.local",
    )

    mock_ws_result = MagicMock()
    mock_ws_result.scalar_one_or_none.return_value = ws_id

    mock_slug_result = MagicMock()
    mock_slug_result.scalar_one_or_none.return_value = uuid.uuid4()

    session.execute.side_effect = [mock_ws_result, mock_slug_result]

    with pytest.raises(ConflictError, match="Policy with slug 'duplicate-slug' already exists"):
        await service.create_policy_draft(
            workspace_id=ws_id,
            payload=payload,
            session=session,
        )


@pytest.mark.asyncio
async def test_update_policy_draft_success() -> None:
    """Verify updating draft Rego does not alter published version pointer."""
    service = PolicyService()
    session = AsyncMock()

    ws_id = uuid.uuid4()
    pol_id = uuid.uuid4()
    now = datetime.now(UTC)
    existing_policy = Policy(
        id=pol_id,
        workspace_id=ws_id,
        name="Old Name",
        slug="test-policy",
        description="Old description",
        status=PolicyStatus.DRAFT.value,
        draft_rego="package kolang.authz\ndefault allow := false",
        active_version_id=None,
        created_by="admin@kolang.local",
        created_at=now,
        updated_at=now,
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = existing_policy
    session.execute.return_value = mock_res

    update_payload = PolicyDraftUpdate(
        name="Updated Name",
        draft_rego="package kolang.authz\ndefault allow := true\nallow if true",
    )

    result = await service.update_policy_draft(
        workspace_id=ws_id,
        policy_id=pol_id,
        payload=update_payload,
        updated_by="editor@kolang.local",
        session=session,
    )

    assert result.name == "Updated Name"
    assert "default allow := true" in result.draft_rego
    assert result.updated_by == "editor@kolang.local"
    assert existing_policy.active_version_id is None


@pytest.mark.asyncio
async def test_publish_policy_version_and_checksum_stored() -> None:
    """
    AC: Publishing a new version computes checksum, sets sequential v1,
    and transitions to ACTIVE status.
    """
    service = PolicyService()
    session = AsyncMock()
    session.add = MagicMock()

    ws_id = uuid.uuid4()
    pol_id = uuid.uuid4()
    rego_code = "package kolang.authz\nallow if true"

    existing_policy = Policy(
        id=pol_id,
        workspace_id=ws_id,
        name="Test Policy",
        slug="test-policy",
        description="Test",
        status=PolicyStatus.DRAFT.value,
        draft_rego=rego_code,
        active_version_id=None,
        active_version_number=None,
        created_by="admin@kolang.local",
    )

    mock_policy_res = MagicMock()
    mock_policy_res.scalar_one_or_none.return_value = existing_policy

    # Version count check returns 0 (first version)
    mock_v_res = MagicMock()
    mock_v_res.scalar_one.return_value = 0

    session.execute.side_effect = [mock_policy_res, mock_v_res]

    publish_payload = PolicyPublishRequest(description="Initial release v1")

    result = await service.publish_policy_version(
        workspace_id=ws_id,
        policy_id=pol_id,
        payload=publish_payload,
        published_by="releaser@kolang.local",
        session=session,
    )

    assert result.version == 1
    assert result.rego_source == rego_code
    assert result.checksum == compute_policy_checksum(rego_code)
    assert result.status == PolicyVersionStatus.PUBLISHED
    assert result.published_by == "releaser@kolang.local"

    # Policy itself transitioned to ACTIVE
    assert existing_policy.status == PolicyStatus.ACTIVE.value
    assert existing_policy.active_version_number == 1
    assert existing_policy.active_version_id == result.id


@pytest.mark.asyncio
async def test_subsequent_publish_increments_version_and_retains_previous() -> None:
    """AC: Previous version remains intact in history when version 2 is published."""
    service = PolicyService()
    session = AsyncMock()
    session.add = MagicMock()

    ws_id = uuid.uuid4()
    pol_id = uuid.uuid4()
    v1_id = uuid.uuid4()

    existing_policy = Policy(
        id=pol_id,
        workspace_id=ws_id,
        name="Test Policy",
        slug="test-policy",
        description="Test",
        status=PolicyStatus.ACTIVE.value,
        draft_rego="package kolang.authz\nv2 := true",
        active_version_id=v1_id,
        active_version_number=1,
        created_by="admin@kolang.local",
    )

    v1_record = PolicyVersion(
        id=v1_id,
        policy_id=pol_id,
        workspace_id=ws_id,
        version=1,
        rego_source="package kolang.authz\nv1 := true",
        checksum=compute_policy_checksum("package kolang.authz\nv1 := true"),
        status=PolicyVersionStatus.PUBLISHED.value,
        published_by="admin@kolang.local",
    )

    mock_policy_res = MagicMock()
    mock_policy_res.scalar_one_or_none.return_value = existing_policy

    mock_v_res = MagicMock()
    mock_v_res.scalar_one.return_value = 1  # max version is 1

    mock_prev_res = MagicMock()
    mock_prev_res.scalars.return_value.all.return_value = [v1_record]

    session.execute.side_effect = [mock_policy_res, mock_v_res, mock_prev_res]

    publish_payload = PolicyPublishRequest(
        rego_source="package kolang.authz\nv2 := true",
        description="Release v2",
    )

    result = await service.publish_policy_version(
        workspace_id=ws_id,
        policy_id=pol_id,
        payload=publish_payload,
        published_by="admin@kolang.local",
        session=session,
    )

    assert result.version == 2
    assert v1_record.status == PolicyVersionStatus.SUPERSEDED.value
    assert existing_policy.active_version_number == 2
    assert existing_policy.active_version_id == result.id


@pytest.mark.asyncio
async def test_publish_without_rego_fails() -> None:
    """Verify ValidationError when publishing a policy with no rego source."""
    service = PolicyService()
    session = AsyncMock()

    ws_id = uuid.uuid4()
    pol_id = uuid.uuid4()
    existing_policy = Policy(
        id=pol_id,
        workspace_id=ws_id,
        name="Empty Policy",
        slug="empty-policy",
        draft_rego="",
        created_by="admin@kolang.local",
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = existing_policy
    session.execute.return_value = mock_res

    with pytest.raises(ValidationError, match="Cannot publish policy version without rego_source"):
        await service.publish_policy_version(
            workspace_id=ws_id,
            policy_id=pol_id,
            payload=PolicyPublishRequest(),
            published_by="admin@kolang.local",
            session=session,
        )


@pytest.mark.asyncio
async def test_get_active_version_for_evaluation_draft_returns_none() -> None:
    """Enforces ACP-012 Rule 3: Policy Drafts must NOT be applied to Gateway evaluation."""
    service = PolicyService()
    session = AsyncMock()

    ws_id = uuid.uuid4()
    pol_id = uuid.uuid4()

    # Draft policy
    draft_policy = Policy(
        id=pol_id,
        workspace_id=ws_id,
        name="Draft Policy",
        slug="draft-policy",
        status=PolicyStatus.DRAFT.value,
        active_version_id=None,
        created_by="admin@kolang.local",
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = draft_policy
    session.execute.return_value = mock_res

    result = await service.get_active_version_for_evaluation(
        workspace_id=ws_id,
        policy_id=pol_id,
        session=session,
    )

    assert result is None  # DRAFT IS NEVER EVALUATED ON GATEWAY


@pytest.mark.asyncio
async def test_get_active_version_for_evaluation_active_returns_version() -> None:
    """When policy is ACTIVE and published, gateway retrieves active PolicyVersion."""
    service = PolicyService()
    session = AsyncMock()

    ws_id = uuid.uuid4()
    pol_id = uuid.uuid4()
    ver_id = uuid.uuid4()

    now = datetime.now(UTC)
    active_policy = Policy(
        id=pol_id,
        workspace_id=ws_id,
        name="Active Policy",
        slug="active-policy",
        status=PolicyStatus.ACTIVE.value,
        active_version_id=ver_id,
        active_version_number=1,
        created_by="admin@kolang.local",
        created_at=now,
        updated_at=now,
    )

    version_record = PolicyVersion(
        id=ver_id,
        policy_id=pol_id,
        workspace_id=ws_id,
        version=1,
        rego_source="package kolang.authz\nallow := true",
        checksum=compute_policy_checksum("package kolang.authz\nallow := true"),
        description="Version 1 release",
        status=PolicyVersionStatus.PUBLISHED.value,
        published_at=now,
        published_by="admin@kolang.local",
        created_at=now,
    )

    mock_policy_res = MagicMock()
    mock_policy_res.scalar_one_or_none.return_value = active_policy

    mock_ver_res = MagicMock()
    mock_ver_res.scalar_one_or_none.return_value = version_record

    session.execute.side_effect = [mock_policy_res, mock_ver_res]

    result = await service.get_active_version_for_evaluation(
        workspace_id=ws_id,
        policy_id=pol_id,
        session=session,
    )

    assert result is not None
    assert result.id == ver_id
    assert result.version == 1
    assert result.status == PolicyVersionStatus.PUBLISHED


@pytest.mark.asyncio
async def test_cross_workspace_idor_protection() -> None:
    """AC: Accessing another workspace's policy raises NotFoundError (anti-IDOR)."""
    service = PolicyService()
    session = AsyncMock()

    ws_b = uuid.uuid4()
    pol_a_id = uuid.uuid4()

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None  # Not found under ws_b query
    session.execute.return_value = mock_res

    with pytest.raises(NotFoundError, match=f"Policy '{pol_a_id}' not found"):
        await service.get_policy(
            workspace_id=ws_b,
            policy_id=pol_a_id,
            session=session,
        )
