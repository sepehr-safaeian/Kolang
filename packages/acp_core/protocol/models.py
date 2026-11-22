"""
Internal message models for the Kolang protocol layer.

These models represent Kolang's internal contract for tool calls and
server descriptors. They are deliberately independent of the MCP
JSON-RPC wire format — translation happens at the protocol adapter boundary.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class TransportType(StrEnum):
    """Supported MCP server transport types."""

    STDIO = "stdio"
    SSE = "sse"
    STREAMABLE_HTTP = "streamable_http"


class HealthStatus(StrEnum):
    """Health status of a registered MCP server."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


# ── Tool Call Messages ───────────────────────────────────────────────────────


class ToolCallRequest(BaseModel):
    """Internal representation of a tool call request."""

    request_id: str
    correlation_id: str
    principal_id: str
    server_id: str
    tool_name: str
    workspace_id: str = "default"
    arguments: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolCallResponse(BaseModel):
    """Internal representation of a tool call response."""

    request_id: str
    correlation_id: str
    result: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ── Descriptors ──────────────────────────────────────────────────────────────


class ToolDescriptor(BaseModel):
    """Describes a tool exposed by an MCP server."""

    tool_id: str
    server_id: str
    name: str
    workspace_id: str = "default"
    description: str = ""
    input_schema: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ServerDescriptor(BaseModel):
    """Describes a registered MCP server and its capabilities."""

    server_id: str
    name: str
    endpoint: str
    workspace_id: str = "default"
    transport: TransportType = TransportType.STREAMABLE_HTTP
    health_status: HealthStatus = HealthStatus.UNKNOWN
    tools: list[ToolDescriptor] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
