from __future__ import annotations

from typing import AsyncGenerator
import pytest
from httpx import ASGITransport, AsyncClient

from apps.api.app.main import create_app
from acp_core.common.context import RequestContext, set_request_context


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_request_context() -> RequestContext:
    ctx = RequestContext(
        request_id="req-test-123",
        correlation_id="corr-test-456",
    )
    set_request_context(ctx)
    return ctx
