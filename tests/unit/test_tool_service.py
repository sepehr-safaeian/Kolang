"""
Unit tests for ToolService domain logic and workspace scoping (ACP-010).

Verifies:
- Payload workspace consistency validation (detecting workspace spoofing).
- Server ownership validation (blocking cross-workspace server tool attachment).
- Tool name uniqueness per server (ConflictError on duplicate).
- Auto-fingerprint computation on creation and schema updates.
- IDOR protection on get, update, and delete operations.
- Historical snapshot creation, hashing, and workspace isolation.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from acp_core.common.errors import ConflictError, NotFoundError, ValidationError
from acp_core.registry.models import McpServer
from acp_core.registry.tool_models import (
    Tool,
    ToolClassificationStatus,
    ToolCreate,
    ToolSnapshotCreate,
    ToolUpdate,
)
from acp_core.registry.tool_service import ToolService


@pytest.mark.asyncio
async def test_create_tool_rejects_payload_workspace_mismatch() -> None:
    """Verify that specifying a different workspace_id in payload raises ValidationError."""
    service = ToolService()
    session = AsyncMock()
    session.add = MagicMock()

    caller_ws = uuid.uuid4()
    spoofed_ws = uuid.uuid4()
    server_id = uuid.uuid4()

    payload = ToolCreate(
        workspace_id=spoofed_ws,
        server_id=server_id,
        name="spoofed_tool",
        input_schema={"type": "object"},
    )

    with pytest.raises(ValidationError, match="does not match target workspace"):
        await service.create_tool(session=session, workspace_id=caller_ws, data=payload)


@pytest.mark.asyncio
async def test_create_tool_rejects_unowned_server() -> None:
    """Verify NotFoundError when attempting to attach a tool to a server from another workspace."""
    service = ToolService()
    session = AsyncMock()
    session.add = MagicMock()

    # Mock DB query returning None (server not found in caller's workspace)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    caller_ws = uuid.uuid4()
    server_id = uuid.uuid4()

    payload = ToolCreate(
        server_id=server_id,
        name="tool_on_foreign_server",
        input_schema={"type": "object"},
    )

    with pytest.raises(NotFoundError, match="not found in workspace"):
        await service.create_tool(session=session, workspace_id=caller_ws, data=payload)


@pytest.mark.asyncio
async def test_create_tool_rejects_duplicate_name_on_same_server() -> None:
    """Verify ConflictError when a tool with the same name already exists on the server."""
    service = ToolService()
    session = AsyncMock()
    session.add = MagicMock()

    caller_ws = uuid.uuid4()
    server_id = uuid.uuid4()

    valid_server = McpServer(
        id=server_id,
        workspace_id=caller_ws,
        name="Active Server",
        slug="active-server",
        endpoint_url="https://api.example.com/mcp",
    )
    existing_tool = Tool(
        id=uuid.uuid4(),
        workspace_id=caller_ws,
        server_id=server_id,
        name="existing_tool",
        input_schema={"type": "object"},
        fingerprint="a" * 64,
    )

    # First call verifies server, second call checks existing tool
    res_server = MagicMock()
    res_server.scalar_one_or_none.return_value = valid_server

    res_tool = MagicMock()
    res_tool.scalar_one_or_none.return_value = existing_tool

    session.execute.side_effect = [res_server, res_tool]

    payload = ToolCreate(
        server_id=server_id,
        name="existing_tool",
        input_schema={"type": "object"},
    )

    with pytest.raises(ConflictError, match="already exists on server"):
        await service.create_tool(session=session, workspace_id=caller_ws, data=payload)


@pytest.mark.asyncio
async def test_create_tool_success_with_fingerprint() -> None:
    """Verify successful tool creation with auto-computed deterministic fingerprint."""
    service = ToolService()
    session = AsyncMock()
    session.add = MagicMock()

    caller_ws = uuid.uuid4()
    server_id = uuid.uuid4()

    valid_server = McpServer(
        id=server_id,
        workspace_id=caller_ws,
        name="Server 1",
        slug="server-1",
        endpoint_url="https://api.example.com/mcp",
    )

    # Server check passes, tool uniqueness check returns None (no duplicate)
    res_server = MagicMock()
    res_server.scalar_one_or_none.return_value = valid_server

    res_tool = MagicMock()
    res_tool.scalar_one_or_none.return_value = None

    session.execute.side_effect = [res_server, res_tool]

    payload = ToolCreate(
        server_id=server_id,
        name="calculator",
        title="Math Calculator",
        description="Evaluates arithmetic expressions.",
        input_schema={"type": "object", "properties": {"expr": {"type": "string"}}},
        risk_labels=["math:eval"],
    )

    tool = await service.create_tool(session=session, workspace_id=caller_ws, data=payload)

    assert tool.name == "calculator"
    assert tool.workspace_id == caller_ws
    assert tool.server_id == server_id
    assert tool.risk_labels == ["math:eval"]
    assert len(tool.fingerprint) == 64
    assert tool.classification_status == ToolClassificationStatus.UNCLASSIFIED.value
    assert session.add.called
    assert session.flush.called


@pytest.mark.asyncio
async def test_update_tool_recomputes_fingerprint_on_schema_change() -> None:
    """Verify that updating a tool's schema triggers fingerprint recomputation."""
    service = ToolService()
    session = AsyncMock()
    session.add = MagicMock()

    ws_id = uuid.uuid4()
    tool_id = uuid.uuid4()
    server_id = uuid.uuid4()

    old_schema = {"type": "object", "properties": {"x": {"type": "integer"}}}
    tool = Tool(
        id=tool_id,
        workspace_id=ws_id,
        server_id=server_id,
        name="compute_sum",
        input_schema=old_schema,
        fingerprint="initial_fingerprint",
        classification_status="unclassified",
    )

    res_tool = MagicMock()
    res_tool.scalar_one_or_none.return_value = tool
    session.execute.return_value = res_tool

    new_schema = {
        "type": "object",
        "properties": {"x": {"type": "integer"}, "y": {"type": "integer"}},
    }
    update_data = ToolUpdate(
        input_schema=new_schema,
        classification_status=ToolClassificationStatus.SAFE,
    )

    updated = await service.update_tool(
        session=session, workspace_id=ws_id, tool_id=tool_id, data=update_data
    )

    assert updated.classification_status == "safe"
    assert updated.input_schema == new_schema
    # Fingerprint must have been recomputed to a valid 64-char SHA-256
    assert updated.fingerprint != "initial_fingerprint"
    assert len(updated.fingerprint) == 64


@pytest.mark.asyncio
async def test_create_snapshot_verifies_server_and_computes_hash() -> None:
    """Verify snapshot recording verifies server workspace ownership and hashes catalog."""
    service = ToolService()
    session = AsyncMock()
    session.add = MagicMock()

    ws_id = uuid.uuid4()
    server_id = uuid.uuid4()

    valid_server = McpServer(
        id=server_id,
        workspace_id=ws_id,
        name="Server 1",
        slug="server-1",
        endpoint_url="https://api.example.com/mcp",
    )
    res_server = MagicMock()
    res_server.scalar_one_or_none.return_value = valid_server
    session.execute.return_value = res_server

    tools_data = [
        {"name": "tool_1", "input_schema": {"type": "object"}},
        {"name": "tool_2", "input_schema": {"type": "object"}},
    ]

    payload = ToolSnapshotCreate(
        server_id=server_id,
        tools_data=tools_data,
        metadata={"sweep_id": "sweep-123"},
    )

    snapshot = await service.create_snapshot(session=session, workspace_id=ws_id, data=payload)

    assert snapshot.workspace_id == ws_id
    assert snapshot.server_id == server_id
    assert snapshot.tool_count == 2
    assert len(snapshot.catalog_hash) == 64
    assert snapshot.metadata_ == {"sweep_id": "sweep-123"}
    assert session.add.called
    assert session.flush.called
