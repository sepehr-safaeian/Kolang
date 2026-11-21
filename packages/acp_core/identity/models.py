"""
Identity domain models for Kolang.

Defines principals, token claims, and authentication context.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from acp_core.contracts.models import Principal


class TokenClaims(BaseModel):
    """Decoded and validated OIDC/JWT token claims."""

    sub: str
    iss: str
    aud: list[str] = Field(default_factory=list)
    exp: int
    iat: int
    roles: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    client_id: str | None = None
    scope: str | None = None


class AuthContext(BaseModel):
    """Full authentication context for a request."""

    principal: Principal
    token_claims: TokenClaims
    authenticated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    auth_method: str = "oidc"
