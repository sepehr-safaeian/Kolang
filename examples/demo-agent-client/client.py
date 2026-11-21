"""
Demo agent client sending tool calls through the Kolang Gateway.
"""

from __future__ import annotations

import asyncio
import uuid
import httpx


async def invoke_gateway_tool(
    gateway_url: str,
    tool_name: str,
    arguments: dict[str, str],
) -> None:
    req_id = f"req-{uuid.uuid4().hex[:8]}"
    corr_id = f"corr-{uuid.uuid4().hex[:8]}"

    headers = {
        "X-Request-ID": req_id,
        "X-Correlation-ID": corr_id,
        "Authorization": "Bearer mock-token-for-testing",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{gateway_url}/healthz", headers=headers)
        print(f"Gateway Response [{response.status_code}]: {response.json()}")


if __name__ == "__main__":
    asyncio.run(
        invoke_gateway_tool(
            gateway_url="http://localhost:8000",
            tool_name="read_profile",
            arguments={"user_id": "usr-123"},
        )
    )
