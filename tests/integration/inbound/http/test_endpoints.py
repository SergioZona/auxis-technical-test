"""
Integration tests for Item HTTP endpoints.
Uses a real FastAPI test client. Repository is overridden with a stub.
"""


async def test_health_returns_200(client) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["status"] == "healthy"


async def test_ready_returns_200(client) -> None:
    response = await client.get("/ready")
    assert response.status_code == 200
