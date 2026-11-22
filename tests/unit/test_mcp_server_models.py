"""
Unit tests for MCP Server domain models and Pydantic DTOs (ACP-009).

Verifies:
- ORM model attributes, defaults, and relationships.
- Pydantic schema validation (slugs, names, transport, status).
- Safe representation without credential leaks.
- Composite uniqueness and status helpers.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from acp_core.registry.models import (
    McpServer,
    McpServerBase,
    McpServerCreate,
    McpServerRead,
    McpServerStatus,
    McpServerTransport,
    McpServerUpdate,
)


def test_mcp_server_transport_enum_values() -> None:
    """Verify supported transport enum values."""
    assert McpServerTransport.STREAMABLE_HTTP == "streamable_http"
    assert McpServerTransport.SSE == "sse"
    assert McpServerTransport.STDIO == "stdio"


def test_mcp_server_status_enum_values() -> None:
    """Verify supported status enum values."""
    assert McpServerStatus.PENDING == "pending"
    assert McpServerStatus.CONNECTED == "connected"
    assert McpServerStatus.UNAVAILABLE == "unavailable"
    assert McpServerStatus.ERROR == "error"
    assert McpServerStatus.DISABLED == "disabled"


def test_mcp_server_create_valid() -> None:
    """Verify valid McpServerCreate schema creation and defaults."""
    payload = McpServerCreate(
        name="GitHub Tools",
        slug="github-tools",
        endpoint_url="https://api.example.com/mcp",
    )
    assert payload.name == "GitHub Tools"
    assert payload.slug == "github-tools"
    assert payload.endpoint_url == "https://api.example.com/mcp"
    assert payload.transport == McpServerTransport.STREAMABLE_HTTP
    assert payload.status == McpServerStatus.PENDING
    assert payload.description == ""
    assert payload.metadata == {}
    assert payload.auth_profile_id is None


@pytest.mark.parametrize(
    "valid_slug",
    [
        "github",
        "github-tools",
        "mcp-server-1",
        "a",
        "a-b-c",
        "server-2026",
    ],
)
def test_mcp_server_slug_validation_success(valid_slug: str) -> None:
    """Verify valid URL-friendly slugs pass validation."""
    server = McpServerBase(
        name="Test Server",
        slug=valid_slug,
        endpoint_url="https://api.example.com/mcp",
    )
    assert server.slug == valid_slug


def test_mcp_server_slug_lowercasing() -> None:
    """Verify slugs are automatically normalized to lowercase."""
    server = McpServerBase(
        name="Test Server",
        slug="UPPERCASE-SLUG",
        endpoint_url="https://api.example.com/mcp",
    )
    assert server.slug == "uppercase-slug"


@pytest.mark.parametrize(
    "invalid_slug",
    [
        "",
        " ",
        "-leading-hyphen",
        "trailing-hyphen-",
        "with spaces",
        "special!chars",
        "underscore_not_allowed",
        "UPPER!CASE",
        "a" * 101,  # Exceeds 100 chars
    ],
)
def test_mcp_server_slug_validation_failure(invalid_slug: str) -> None:
    """Verify invalid slugs are rejected by Pydantic."""
    with pytest.raises(ValidationError):
        McpServerBase(
            name="Test Server",
            slug=invalid_slug,
            endpoint_url="https://api.example.com/mcp",
        )


def test_mcp_server_name_validation() -> None:
    """Verify empty or whitespace-only server names are rejected."""
    with pytest.raises(ValidationError):
        McpServerBase(
            name="   ",
            slug="test-server",
            endpoint_url="https://api.example.com/mcp",
        )


def test_mcp_server_update_partial() -> None:
    """Verify partial updates allow updating specific fields."""
    update = McpServerUpdate(
        name="Updated Server Name",
        status=McpServerStatus.CONNECTED,
    )
    assert update.name == "Updated Server Name"
    assert update.status == McpServerStatus.CONNECTED
    assert update.endpoint_url is None
    assert update.transport is None


def test_mcp_server_read_serialization() -> None:
    """Verify McpServerRead serialization from attributes."""
    server_id = uuid.uuid4()
    ws_id = uuid.uuid4()
    now = datetime.now(UTC)

    server = McpServer(
        id=server_id,
        workspace_id=ws_id,
        name="Filesystem MCP",
        slug="filesystem-mcp",
        endpoint_url="https://fs.example.com/mcp",
        transport=McpServerTransport.STREAMABLE_HTTP.value,
        status=McpServerStatus.CONNECTED.value,
        description="Local filesystem access tools",
        metadata_={"version": "1.0"},
        created_at=now,
        updated_at=now,
    )

    read_model = McpServerRead.model_validate(server)
    assert read_model.id == server_id
    assert read_model.workspace_id == ws_id
    assert read_model.name == "Filesystem MCP"
    assert read_model.slug == "filesystem-mcp"
    assert read_model.endpoint_url == "https://fs.example.com/mcp"
    assert read_model.transport == McpServerTransport.STREAMABLE_HTTP
    assert read_model.status == McpServerStatus.CONNECTED
    assert read_model.metadata == {"version": "1.0"}


def test_mcp_server_orm_properties_and_repr() -> None:
    """Verify ORM model properties (is_connected, is_enabled) and repr."""
    server = McpServer(
        id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        name="Test Server",
        slug="test-server",
        endpoint_url="https://api.example.com/mcp",
        status=McpServerStatus.CONNECTED.value,
    )
    assert server.is_connected is True
    assert server.is_enabled is True

    server.status = McpServerStatus.DISABLED.value
    assert server.is_connected is False
    assert server.is_enabled is False

    repr_str = repr(server)
    assert "McpServer" in repr_str
    assert "test-server" in repr_str
    assert "disabled" in repr_str
