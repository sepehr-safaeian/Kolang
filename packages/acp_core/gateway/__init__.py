"""
Request routing and policy enforcement gateway.

The gateway is the main data-plane path: it receives tool call requests,
enforces policies, manages approvals, and routes to upstream MCP servers.
"""

from __future__ import annotations

from acp_core.contracts.models import (
    GatewayErrorPayload,
    GatewayResult,
    PolicyDecision,
    PolicyInput,
    PolicyObligation,
    Principal,
    RequestContext,
    ToolInvocation,
    ToolResource,
)

__all__ = [
    "GatewayErrorPayload",
    "GatewayResult",
    "PolicyDecision",
    "PolicyInput",
    "PolicyObligation",
    "Principal",
    "RequestContext",
    "ToolInvocation",
    "ToolResource",
]
