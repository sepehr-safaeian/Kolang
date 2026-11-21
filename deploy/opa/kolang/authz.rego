# ═══════════════════════════════════════════════════════════════════════════════
# Kolang Authorization Policy
# ═══════════════════════════════════════════════════════════════════════════════
#
# This Rego policy implements the authorization logic for the Kolang ACP.
# It evaluates whether a principal is allowed to invoke a specific tool
# on a specific MCP server.
#
# Input schema:
#   {
#     "principal_id":    "user:alice",
#     "principal_kind":  "user",
#     "principal_roles": ["developer"],
#     "principal_groups": ["engineering"],
#     "server_id":       "prod-database",
#     "tool_name":       "query",
#     "request_metadata": {}
#   }
# ═══════════════════════════════════════════════════════════════════════════════

package kolang.authz

import rego.v1

# ── Default Decision ─────────────────────────────────────────────────────────
# Deny by default — every access must be explicitly granted.
default allow := false
default require_approval := false

# ── Allow Rules ──────────────────────────────────────────────────────────────

# Rule 1: Admins can access all tools on all servers.
allow if {
    is_admin
}

# Rule 2: Principals with the "operator" role can access monitoring tools.
allow if {
    has_role("operator")
    is_monitoring_tool
}

# Rule 3: Developers can access read-only tools.
allow if {
    has_role("developer")
    is_read_only_tool
}

# ── Conditional Rules (Require Approval) ─────────────────────────────────────

# Rule 4: Write operations on production servers require approval.
require_approval if {
    not is_admin
    is_write_tool
    is_production_server
}

# ── Deny Rules ───────────────────────────────────────────────────────────────

# Rule 5: Explicitly blocked tools are always denied.
deny if {
    is_blocked_tool
}

# Override allow if deny is true.
allow if {
    not deny
}

# ── Helper Rules ─────────────────────────────────────────────────────────────

is_admin if {
    has_role("admin")
}

has_role(role) if {
    some r in input.principal_roles
    r == role
}

has_group(group) if {
    some g in input.principal_groups
    g == group
}

# ── Tool Classification ─────────────────────────────────────────────────────

read_only_tools := {"query", "list", "describe", "get", "search", "read"}

write_tools := {"create", "update", "delete", "execute", "write", "modify"}

monitoring_tools := {"health_check", "status", "metrics", "logs"}

blocked_tools := {"drop_database", "rm_rf", "format_disk"}

is_read_only_tool if {
    input.tool_name in read_only_tools
}

is_write_tool if {
    input.tool_name in write_tools
}

is_monitoring_tool if {
    input.tool_name in monitoring_tools
}

is_blocked_tool if {
    input.tool_name in blocked_tools
}

# ── Server Classification ───────────────────────────────────────────────────

is_production_server if {
    startswith(input.server_id, "prod-")
}
