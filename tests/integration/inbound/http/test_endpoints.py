"""
Integration tests for Item HTTP endpoints.
Uses a real FastAPI test client. Repository is overridden with a stub.
"""

import pytest

from app.domain.models.item import Item


@pytest.fixture
def sample_item() -> Item:
    return Item.create(name="Widget", description="Test widget")


async def test_health_returns_200(client) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["status"] == "healthy"


async def test_ping_returns_pong(client) -> None:
    response = await client.post("/ping")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["message"] == "pong"


async def test_ready_returns_200(client) -> None:
    response = await client.get("/ready")
    assert response.status_code == 200
