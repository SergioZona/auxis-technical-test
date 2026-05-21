"""Shared test fixtures and configuration."""

import pytest
from httpx import ASGITransport, AsyncClient

import os

# Set dummy environment variables for tests before importing the application
os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_PASSWORD", "test_db_pass")
os.environ.setdefault("SECRET_KEY", "test_secret_key")
os.environ.setdefault("OPENAI_API_KEY", "test_openai_key")
os.environ.setdefault("GEMINI_API_KEY", "test_gemini_key")

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
