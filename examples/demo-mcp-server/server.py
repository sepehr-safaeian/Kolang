"""
Minimal demo MCP server providing mock tools for testing Kolang.
"""

from __future__ import annotations

import asyncio
from typing import Any


class MockMcpServer:
    def __init__(self, name: str = "demo-server") -> None:
        self.name = name
        self.tools = {
            "read_profile": {"description": "Fetch user profile by ID"},
            "query_metrics": {"description": "Query service latency metrics"},
            "delete_record": {"description": "Delete a record (requires approval)"},
        }

    async def list_tools(self) -> dict[str, Any]:
        return self.tools

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if tool_name not in self.tools:
            return {"error": f"Tool '{tool_name}' not found."}
        return {"status": "success", "tool": tool_name, "output": f"Mock result for {arguments}"}


async def main() -> None:
    server = MockMcpServer()
    tools = await server.list_tools()
    print(f"Server started with tools: {list(tools.keys())}")


if __name__ == "__main__":
    asyncio.run(main())
