"""
Unit tests for McpServerService domain logic and scoping (ACP-009).

Verifies:
- Payload workspace consistency validation (detecting workspace spoofing).
- Slug uniqueness check within workspace.
- Endpoint URL validation integration with SSRF protection.
- IDOR detection and NotFoundError on cross-workspace access.
- CRUD methods with session interaction.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from acp_core.common.errors import ConflictError, NotFoundError, ValidationError
from acp_core.registry.models import (
    McpServer,
    McpServerCreate,
    McpServerStatus,
    McpServerTransport,
    McpServerUpdate,
)
from acp_core.registry.service import McpServerService


@pytest.mark.asyncio
async def test_create_server_rejects_payload_workspace_mismatch() -> None:
    """Verify that specifying a different workspace_id in body payload raises ValidationError."""
    service = McpServerService()
    session = AsyncMock()

    caller_ws = uuid.uuid4()
    spoofed_ws = uuid.uuid4()

    payload = McpServerCreate(
        name="Spoofed Server",
        slug="spoofed-server",
        endpoint_url="https://api.example.com/mcp",
        workspace_id=spoofed_ws,
    )

    with pytest.raises(ValidationError, match="does not match target workspace"):
        await service.create_server(session=session, workspace_id=caller_ws, data=payload)


@pytest.mark.asyncio
async def test_create_server_rejects_duplicate_slug_in_same_workspace() -> None:
    """Verify ConflictError when a server with identical slug already exists in workspace."""
    service = McpServerService()
    session = AsyncMock()

    ws_id = uuid.uuid4()
    existing_server = McpServer(
        id=uuid.uuid4(),
        workspace_id=ws_id,
        name="Existing Server",
        slug="github-mcp",
        endpoint_url="https://api.github.com/mcp",
    )

    # Mock get_server_by_slug returning existing entity
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_server
    session.execute.return_value = mock_result

    payload = McpServerCreate(
        name="New Server",
        slug="github-mcp",
        endpoint_url="https://api.github.com/mcp",
    )

    with pytest.raises(ConflictError, match="already exists in workspace"):
        await service.create_server(session=session, workspace_id=ws_id, data=payload)


@pytest.mark.asyncio
async def test_create_server_validates_ssrf_endpoint() -> None:
    """Verify endpoint_url is validated through SSRF filters during creation."""
    service = McpServerService()
    session = AsyncMock()
    ws_id = uuid.uuid4()

    # Empty existing slug
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    # Payload with SSRF target (loopback IP)
    payload = McpServerCreate.model_construct(
        name="Internal Target",
        slug="internal-target",
        endpoint_url="http://127.0.0.1:8080/mcp",
        transport=McpServerTransport.STREAMABLE_HTTP,
        status=McpServerStatus.PENDING,
        description="",
        metadata={},
    )

    with pytest.raises(ValidationError):
        await service.create_server(session=session, workspace_id=ws_id, data=payload)


@pytest.mark.asyncio
async def test_get_server_or_raise_cross_workspace_idor_raises_not_found() -> None:
    """
    Verify that attempting to fetch a server belonging to another workspace
    raises NotFoundError.
    """
    service = McpServerService()
    session = AsyncMock()

    caller_ws = uuid.uuid4()
    foreign_ws = uuid.uuid4()
    target_server_id = uuid.uuid4()

    # First query (scoped to caller_ws) returns None
    first_result = MagicMock()
    first_result.scalar_one_or_none.return_value = None

    # Second check (exists elsewhere) returns foreign_ws
    second_result = MagicMock()
    second_result.scalar_one_or_none.return_value = foreign_ws

    session.execute.side_effect = [first_result, second_result]

    with pytest.raises(NotFoundError, match="not found in workspace"):
        await service.get_server_or_raise(
            session=session,
            workspace_id=caller_ws,
            server_id=target_server_id,
        )


@pytest.mark.asyncio
async def test_update_server_updates_fields_and_validates_url() -> None:
    """Verify update_server mutates fields and validates new endpoint URL."""
    service = McpServerService()
    session = AsyncMock()

    ws_id = uuid.uuid4()
    server_id = uuid.uuid4()

    existing = McpServer(
        id=server_id,
        workspace_id=ws_id,
        name="Old Name",
        slug="test-slug",
        endpoint_url="https://old.example.com/mcp",
        status=McpServerStatus.PENDING.value,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    session.execute.return_value = mock_result

    update_payload = McpServerUpdate(
        name="New Name",
        endpoint_url="https://new.example.com/mcp",
        status=McpServerStatus.CONNECTED,
    )

    updated = await service.update_server(
        session=session,
        workspace_id=ws_id,
        server_id=server_id,
        data=update_payload,
    )

    assert updated.name == "New Name"
    assert updated.endpoint_url == "https://new.example.com/mcp"
    assert updated.status == McpServerStatus.CONNECTED.value
    session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_delete_server_removes_from_session() -> None:
    """Verify delete_server removes entity from session."""
    service = McpServerService()
    session = AsyncMock()

    ws_id = uuid.uuid4()
    server_id = uuid.uuid4()

    existing = McpServer(
        id=server_id,
        workspace_id=ws_id,
        name="To Delete",
        slug="to-delete",
        endpoint_url="https://del.example.com/mcp",
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    session.execute.return_value = mock_result

    await service.delete_server(
        session=session,
        workspace_id=ws_id,
        server_id=server_id,
    )

    session.delete.assert_awaited_once_with(existing)
    session.flush.assert_awaited()
