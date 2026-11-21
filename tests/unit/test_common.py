from __future__ import annotations

from acp_core.common.context import (
    RequestContext,
    get_request_context,
    get_request_context_or_none,
    request_context_scope,
)
from acp_core.common.errors import (
    AuthenticationError,
    ErrorResponse,
    KolangError,
)
from acp_core.common.types import PrincipalKind, ToolCallResult


def test_request_context_defaults() -> None:
    ctx = RequestContext(request_id="r-1")
    assert ctx.request_id == "r-1"
    assert ctx.correlation_id == "r-1"


def test_request_context_scope() -> None:
    assert get_request_context_or_none() is None
    with request_context_scope(request_id="r-100", correlation_id="c-200") as ctx:
        assert ctx.request_id == "r-100"
        assert ctx.correlation_id == "c-200"
        active = get_request_context()
        assert active.request_id == "r-100"
    assert get_request_context_or_none() is None


def test_error_hierarchy() -> None:
    err = AuthenticationError("Invalid token", details={"reason": "expired"})
    assert isinstance(err, KolangError)
    assert err.code == "AUTHENTICATION_ERROR"
    assert err.status_code == 401
    assert err.details["reason"] == "expired"

    response = ErrorResponse.from_error(err)
    assert response.error == "AUTHENTICATION_ERROR"
    assert response.message == "Invalid token"


def test_domain_enums() -> None:
    assert PrincipalKind.AGENT == "agent"
    assert PrincipalKind.USER == "user"
    assert PrincipalKind.SERVICE == "service"

    assert ToolCallResult.ALLOWED == "allowed"
    assert ToolCallResult.DENIED == "denied"
    assert ToolCallResult.PENDING_APPROVAL == "pending_approval"
