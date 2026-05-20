from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPBasicCredentials

from app.infrastructure.adapters.inbound.http.auth import require_api_token


@pytest.mark.anyio
async def test_require_api_token_anonymous_if_empty_settings() -> None:
    mock_settings = MagicMock()
    mock_settings.api_username = "auxis"
    mock_settings.api_password = ""

    with patch(
        "app.infrastructure.adapters.inbound.http.auth.get_settings",
        return_value=mock_settings,
    ):
        res = await require_api_token(credentials=None)
        assert res == "anonymous"


@pytest.mark.anyio
async def test_require_api_token_raises_401_if_credentials_missing() -> None:
    mock_settings = MagicMock()
    mock_settings.api_username = "auxis"
    mock_settings.api_password = "AuxisPassword123!"

    with patch(
        "app.infrastructure.adapters.inbound.http.auth.get_settings",
        return_value=mock_settings,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await require_api_token(credentials=None)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Missing credentials"


@pytest.mark.anyio
async def test_require_api_token_raises_401_if_credentials_invalid() -> None:
    mock_settings = MagicMock()
    mock_settings.api_username = "auxis"
    mock_settings.api_password = "AuxisPassword123!"

    credentials = HTTPBasicCredentials(username="auxis", password="wrongpassword")

    with patch(
        "app.infrastructure.adapters.inbound.http.auth.get_settings",
        return_value=mock_settings,
    ):
        with pytest.raises(HTTPException) as exc_info:
            await require_api_token(credentials=credentials)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert exc_info.value.detail == "Invalid username or password"


@pytest.mark.anyio
async def test_require_api_token_success_with_valid_credentials() -> None:
    mock_settings = MagicMock()
    mock_settings.api_username = "auxis"
    mock_settings.api_password = "AuxisPassword123!"

    credentials = HTTPBasicCredentials(username="auxis", password="AuxisPassword123!")

    with patch(
        "app.infrastructure.adapters.inbound.http.auth.get_settings",
        return_value=mock_settings,
    ):
        res = await require_api_token(credentials=credentials)
        assert res == "auxis"
