"""Shared test fixtures and configuration."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.infrastructure.main import create_app


@pytest.fixture
def app():
    """Create a fresh app instance for each test."""
    return create_app()


@pytest.fixture
async def client(app):
    """Async HTTP client wired to the test app — no real network calls."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
