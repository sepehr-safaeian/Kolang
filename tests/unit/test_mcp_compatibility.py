"""
Tests for MCP SDK verification, protocol versions, and transport compatibility.

Verifies task ACP-002:
- MCP SDK version and core exports
- Specification protocol versions (2026-07-28 and backwards compatibility)
- Streamable HTTP transport constants and Accept-header handling
- Lifecycle and tool call message models (MVP scope)
- Protocol error code constants
- Transport security settings (Origin and DNS rebinding protection)
- Mapping compatibility with Kolang internal domain protocol models
"""

from __future__ import annotations

import importlib.metadata
from typing import Any

import mcp
import mcp.server.streamable_http as server_http
import mcp.types as mcp_types
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import DEFAULT_NEGOTIATED_VERSION
from mcp_types.version import (
    HANDSHAKE_PROTOCOL_VERSIONS,
    KNOWN_PROTOCOL_VERSIONS,
    LATEST_HANDSHAKE_VERSION,
    LATEST_MODERN_VERSION,
    LATEST_PROTOCOL_VERSION,
    MODERN_PROTOCOL_VERSIONS,
    OLDEST_SUPPORTED_VERSION,
    SUPPORTED_PROTOCOL_VERSIONS,
    is_version_at_least,
)
from starlette.datastructures import Headers
from starlette.requests import Request

from acp_core.protocol.models import (
    HealthStatus,
    ServerDescriptor,
    ToolCallRequest,
    ToolCallResponse,
    ToolDescriptor,
    TransportType,
)


def test_mcp_sdk_version_and_exports() -> None:
    """Verify that official MCP SDK is installed at pinned version 2.3.0."""
    installed_version = importlib.metadata.version("mcp")
    assert installed_version == "2.3.0"
    assert hasattr(mcp, "Client")
    assert hasattr(mcp, "CallToolRequest")
    assert hasattr(mcp, "ListToolsResult")


def test_protocol_version_constants() -> None:
    """Verify official MCP specification protocol version strings and hierarchy."""
    assert LATEST_PROTOCOL_VERSION == "2026-07-28"
    assert LATEST_MODERN_VERSION == "2026-07-28"
    assert LATEST_HANDSHAKE_VERSION == "2025-11-25"
    assert OLDEST_SUPPORTED_VERSION == "2024-11-05"
    assert DEFAULT_NEGOTIATED_VERSION == "2025-03-26"
    assert mcp_types.JSONRPC_VERSION == "2.0"
    assert mcp_types.PROTOCOL_VERSION_META_KEY == "io.modelcontextprotocol/protocolVersion"

    expected_revisions = (
        "2024-11-05",
        "2025-03-26",
        "2025-06-18",
        "2025-11-25",
        "2026-07-28",
    )
    assert expected_revisions == KNOWN_PROTOCOL_VERSIONS
    assert expected_revisions[:4] == HANDSHAKE_PROTOCOL_VERSIONS
    assert MODERN_PROTOCOL_VERSIONS == ("2026-07-28",)
    assert set(SUPPORTED_PROTOCOL_VERSIONS) == set(expected_revisions)

    # Verification helper
    assert is_version_at_least("2026-07-28", "2024-11-05") is True
    assert is_version_at_least("2025-03-26", "2025-11-25") is False
    assert is_version_at_least("unknown-future-version", "2026-07-28") is False


def test_streamable_http_transport_constants() -> None:
    """Verify HTTP constants, headers, and media-type negotiation helpers."""
    assert server_http.CONTENT_TYPE_JSON == "application/json"
    assert server_http.CONTENT_TYPE_SSE == "text/event-stream"
    assert server_http.MCP_PROTOCOL_VERSION_HEADER == "mcp-protocol-version"
    assert server_http.MCP_SESSION_ID_HEADER == "mcp-session-id"
    assert server_http.LAST_EVENT_ID_HEADER == "last-event-id"

    # Test check_accept_headers with JSON accept header
    def make_request(accept: str) -> Request:
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/mcp",
            "headers": Headers({"accept": accept}).raw,
        }
        return Request(scope)

    has_json, has_sse = server_http.check_accept_headers(make_request("application/json"))
    assert has_json is True
    assert has_sse is False

    has_json, has_sse = server_http.check_accept_headers(make_request("text/event-stream"))
    assert has_json is False
    assert has_sse is True

    has_json, has_sse = server_http.check_accept_headers(make_request("*/*"))
    assert has_json is True
    assert has_sse is True

    has_json, has_sse = server_http.check_accept_headers(
        make_request("application/json, text/event-stream")
    )
    assert has_json is True
    assert has_sse is True


def test_lifecycle_and_tool_call_models() -> None:
    """Verify tool discovery, invocation, and lifecycle models required for MVP."""
    # Lifecycle: Initialize and Ping
    init_req = mcp_types.InitializeRequest(
        params=mcp_types.InitializeRequestParams(
            protocol_version="2025-11-25",
            capabilities=mcp_types.ClientCapabilities(),
            client_info=mcp_types.Implementation(name="test-agent", version="1.0.0"),
        )
    )
    assert init_req.method == "initialize"
    assert init_req.params.protocol_version == "2025-11-25"

    ping_req = mcp_types.PingRequest()
    assert ping_req.method == "ping"

    # Tool discovery with pagination
    tool1 = mcp_types.Tool(
        name="execute_query",
        description="Run query",
        input_schema={"type": "object", "properties": {"q": {"type": "string"}}},
    )
    list_tools_result = mcp_types.ListToolsResult(
        tools=[tool1],
        next_cursor="page-token-abc",
    )
    assert len(list_tools_result.tools) == 1
    assert list_tools_result.tools[0].name == "execute_query"
    assert list_tools_result.next_cursor == "page-token-abc"

    # Tool call success
    call_req = mcp_types.CallToolRequest(
        params=mcp_types.CallToolRequestParams(
            name="execute_query",
            arguments={"q": "SELECT 1"},
        )
    )
    assert call_req.method == "tools/call"
    assert call_req.params.name == "execute_query"

    success_result = mcp_types.CallToolResult(
        content=[mcp_types.TextContent(type="text", text="1 row returned")],
        is_error=False,
    )
    assert success_result.is_error is False
    assert success_result.content[0].type == "text"

    # Tool execution failure (application-level error inside MCP result)
    error_result = mcp_types.CallToolResult(
        content=[mcp_types.TextContent(type="text", text="Syntax error near SELECT")],
        is_error=True,
    )
    assert error_result.is_error is True
    assert "Syntax error" in error_result.content[0].text  # type: ignore[union-attr]


def test_error_code_constants() -> None:
    """Verify JSON-RPC 2.0 and MCP protocol error constants."""
    # Standard JSON-RPC 2.0 errors
    assert mcp_types.PARSE_ERROR == -32700
    assert mcp_types.INVALID_REQUEST == -32600
    assert mcp_types.METHOD_NOT_FOUND == -32601
    assert mcp_types.INVALID_PARAMS == -32602
    assert mcp_types.INTERNAL_ERROR == -32603

    # MCP-specific errors
    assert mcp_types.CONNECTION_CLOSED == -32000
    assert mcp_types.REQUEST_TIMEOUT == -32001
    assert mcp_types.HEADER_MISMATCH == -32020
    assert mcp_types.MISSING_REQUIRED_CLIENT_CAPABILITY == -32021
    assert mcp_types.UNSUPPORTED_PROTOCOL_VERSION == -32022
    assert mcp_types.URL_ELICITATION_REQUIRED == -32042


def test_transport_security_configuration() -> None:
    """Verify Origin and Host validation configuration settings."""
    settings = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["localhost", "gateway.kolang.internal"],
        allowed_origins=["https://controlplane.kolang.internal"],
    )
    assert settings.enable_dns_rebinding_protection is True
    assert "localhost" in settings.allowed_hosts
    assert "https://controlplane.kolang.internal" in settings.allowed_origins


def test_kolang_internal_protocol_models_interop() -> None:
    """Verify interoperability between Kolang internal protocol models and MCP concepts."""
    # Internal Kolang TransportType includes STREAMABLE_HTTP
    assert TransportType.STREAMABLE_HTTP == "streamable_http"
    assert TransportType.STDIO == "stdio"
    assert TransportType.SSE == "sse"

    # Internal ToolCallRequest can be constructed with MCP tool payload
    mcp_tool_args: dict[str, Any] = {"cluster_id": "cls-001", "action": "restart"}
    internal_req = ToolCallRequest(
        request_id="req-test-1",
        correlation_id="corr-test-1",
        principal_id="prn-user-1",
        server_id="srv-k8s",
        tool_name="manage_cluster",
        arguments=mcp_tool_args,
    )
    assert internal_req.tool_name == "manage_cluster"
    assert internal_req.arguments["cluster_id"] == "cls-001"

    # Internal ToolDescriptor maps to MCP Tool
    internal_desc = ToolDescriptor(
        tool_id="tool-123",
        server_id="srv-k8s",
        name="manage_cluster",
        description="Restart or scale Kubernetes clusters",
        input_schema={"type": "object", "properties": {"cluster_id": {"type": "string"}}},
    )
    mcp_tool = mcp_types.Tool(
        name=internal_desc.name,
        description=internal_desc.description,
        input_schema=internal_desc.input_schema,
    )
    assert mcp_tool.name == internal_desc.name
    assert mcp_tool.description == internal_desc.description

    # Internal ServerDescriptor maps to healthy MCP server
    server_desc = ServerDescriptor(
        server_id="srv-k8s",
        name="Kubernetes MCP Provider",
        endpoint="https://k8s-mcp.internal/mcp",
        transport=TransportType.STREAMABLE_HTTP,
        health_status=HealthStatus.HEALTHY,
        tools=[internal_desc],
    )
    assert server_desc.transport == TransportType.STREAMABLE_HTTP
    assert server_desc.health_status == HealthStatus.HEALTHY
    assert len(server_desc.tools) == 1

    # Internal ToolCallResponse maps tool success
    internal_res = ToolCallResponse(
        request_id="req-test-1",
        correlation_id="corr-test-1",
        result={"status": "completed"},
        duration_ms=42.5,
    )
    assert internal_res.result["status"] == "completed"
    assert internal_res.error is None
