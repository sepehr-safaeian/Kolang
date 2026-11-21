package kolang.example

import rego.v1

default allow := false
default require_approval := false

# Allow admin unrestricted access
allow if {
    some role in input.principal_roles
    role == "admin"
}

# Allow read actions for developers
allow if {
    some role in input.principal_roles
    role == "developer"
    startswith(input.tool_name, "read_")
}

# Require approval for destructive operations
require_approval if {
    input.tool_name in {"delete_record", "drop_table", "deploy_release"}
}
