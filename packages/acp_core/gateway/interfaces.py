"""
Gateway interfaces for Kolang.

Defines Protocol classes for the gateway's dependencies, enabling
loose coupling between the data plane and its backing services.
Upstream and downstream connections use separate interfaces.
"""

from __future__ import annotations

from typing import Any, Protocol

from acp_core.common.types import ApprovalId, ServerId
from acp_core.identity.models import Principal
from acp_core.policy.models import PolicyDecision
from acp_core.protocol.models import ToolCallRequest, ToolCallResponse, ToolDescriptor


class DownstreamHandler(Protocol):
    """Handles incoming tool call requests from agents / clients."""

    async def handle_tool_call(self, request: ToolCallRequest) -> ToolCallResponse: ...


class UpstreamConnector(Protocol):
    """Connects to upstream MCP servers to invoke tools."""

    async def invoke_tool(
        self,
        server_id: ServerId,
        tool_name: str,
        arguments: dict[str, Any],
        *,
        timeout: float = 30.0,
    ) -> Any: ...

    async def list_tools(self, server_id: ServerId) -> list[ToolDescriptor]: ...

    async def health_check(self, server_id: ServerId) -> bool: ...


class PolicyEnforcer(Protocol):
    """Evaluates access control policies for tool call requests."""

    async def evaluate(self, request: ToolCallRequest, principal: Principal) -> PolicyDecision: ...


class ApprovalManager(Protocol):
    """Manages human-in-the-loop approval workflows."""

    async def request_approval(
        self,
        request: ToolCallRequest,
        policy_decision: PolicyDecision,
    ) -> ApprovalId: ...

    async def check_approval(self, approval_id: ApprovalId) -> str: ...
