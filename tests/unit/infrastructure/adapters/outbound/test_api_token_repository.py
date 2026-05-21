"""Unit tests for api_token_repository."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.infrastructure.adapters.outbound.persistence.api_token_repository import (
    ApiTokenModel,
    hash_token,
    verify_db_token,
)


def test_hash_token_returns_sha256_hex() -> None:
    result = hash_token("mysecrettoken")
    assert len(result) == 64
    assert result == hash_token("mysecrettoken")


def test_hash_token_strips_whitespace() -> None:
    assert hash_token("  token  ") == hash_token("token")


def test_hash_token_is_deterministic() -> None:
    assert hash_token("abc") == hash_token("abc")


def test_hash_token_differs_for_different_inputs() -> None:
    assert hash_token("token1") != hash_token("token2")


@pytest.mark.asyncio
async def test_verify_db_token_returns_false_for_empty_token() -> None:
    session = AsyncMock()
    assert await verify_db_token(session, "") is False
    session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_verify_db_token_returns_false_when_not_found() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    assert await verify_db_token(session, "sometoken") is False


@pytest.mark.asyncio
async def test_verify_db_token_returns_true_when_active_no_expiry() -> None:
    session = AsyncMock()
    model = ApiTokenModel(
        id=uuid4(),
        token_hash=hash_token("validtoken"),
        description="test",
        is_active=True,
        expires_at=None,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = model
    session.execute.return_value = mock_result

    assert await verify_db_token(session, "validtoken") is True


@pytest.mark.asyncio
async def test_verify_db_token_returns_false_when_expired() -> None:
    session = AsyncMock()
    model = ApiTokenModel(
        id=uuid4(),
        token_hash=hash_token("expiredtoken"),
        description="test",
        is_active=True,
        expires_at=datetime.now() - timedelta(days=1),
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = model
    session.execute.return_value = mock_result

    assert await verify_db_token(session, "expiredtoken") is False


@pytest.mark.asyncio
async def test_verify_db_token_returns_true_when_not_yet_expired() -> None:
    session = AsyncMock()
    model = ApiTokenModel(
        id=uuid4(),
        token_hash=hash_token("futuretoken"),
        description="test",
        is_active=True,
        expires_at=datetime.now() + timedelta(days=30),
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = model
    session.execute.return_value = mock_result

    assert await verify_db_token(session, "futuretoken") is True
