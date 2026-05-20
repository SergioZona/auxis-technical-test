"""
HTTP Basic Authentication dependency for FastAPI.
Validates the Authorization header against fixed credentials in settings.
"""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.infrastructure.config.settings import get_settings

_basic_scheme = HTTPBasic(auto_error=False)


async def require_api_token(
    credentials: HTTPBasicCredentials | None = Depends(_basic_scheme),
) -> str:
    """Enforces HTTP Basic authentication using api_username and api_password."""
    settings = get_settings()

    # Skip if api_password not set in env (local development/tests)
    if not settings.api_password:
        return "anonymous"

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials",
            headers={"WWW-Authenticate": "Basic"},
        )

    # Use secure comparison to prevent timing attacks
    is_correct_username = secrets.compare_digest(
        credentials.username.encode("utf-8"), settings.api_username.encode("utf-8")
    )
    is_correct_password = secrets.compare_digest(
        credentials.password.encode("utf-8"), settings.api_password.encode("utf-8")
    )

    if not is_correct_username or not is_correct_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return credentials.username
