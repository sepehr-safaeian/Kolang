"""Common shared types, errors, and utilities for Kolang ACP Core."""

from acp_core.common.context import (
    get_request_context,
    get_request_principal_or_none,
    set_request_context,
    set_request_principal,
)
from acp_core.common.errors import ConfigurationError, KolangError
from acp_core.common.settings import Settings, get_settings
from acp_core.common.types import PrincipalId, ServerId, ToolId, WorkspaceId

__all__ = [
    "ConfigurationError",
    "KolangError",
    "PrincipalId",
    "ServerId",
    "Settings",
    "ToolId",
    "WorkspaceId",
    "get_request_context",
    "get_request_principal_or_none",
    "get_settings",
    "set_request_context",
    "set_request_principal",
]
