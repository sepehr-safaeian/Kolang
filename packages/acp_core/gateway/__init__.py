"""
Request routing and policy enforcement gateway.

The gateway is the main data-plane path: it receives tool call requests,
enforces policies, manages approvals, and routes to upstream MCP servers.
"""
