from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_healthz_endpoint(client: AsyncClient) -> None:
    response = await client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_readyz_endpoint_healthy(client: AsyncClient) -> None:
    with patch("apps.api.app.routers.health.ping_db", new_callable=AsyncMock) as mock_ping:
        mock_ping.return_value = True
        response = await client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "checks" in data
        assert data["checks"]["database"] == "ok"


@pytest.mark.asyncio
async def test_readyz_endpoint_unhealthy(client: AsyncClient) -> None:
    with patch("apps.api.app.routers.health.ping_db", new_callable=AsyncMock) as mock_ping:
        mock_ping.return_value = False
        response = await client.get("/readyz")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert "checks" in data
        assert data["checks"]["database"] == "unavailable"


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient) -> None:
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Kolang"
    assert "docs" in data


@pytest.mark.asyncio
async def test_request_headers_propagation(client: AsyncClient) -> None:
    custom_req_id = "req-custom-999"
    custom_corr_id = "corr-custom-888"
    response = await client.get(
        "/healthz",
        headers={
            "X-Request-ID": custom_req_id,
            "X-Correlation-ID": custom_corr_id,
        },
    )
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_req_id
    assert response.headers.get("X-Correlation-ID") == custom_corr_id
