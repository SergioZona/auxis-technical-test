"""
JSend response wrapper — the only place in the codebase that builds HTTP response bodies.
All routers must use these helpers. Never build raw dicts in router handlers.

Spec: https://github.com/omniti-labs/jsend
"""

from typing import Any


def success(data: Any) -> dict[str, Any]:
    """
    For successful requests that return data.
    HTTP 2xx responses.
    """
    return {"status": "success", "data": data}


def fail(data: dict[str, Any]) -> dict[str, Any]:
    """
    For client-side errors (validation, not found, etc.).
    HTTP 4xx responses.
    The `data` dict should map field names → error messages.
    """
    return {"status": "fail", "data": data}


def error(message: str, code: int | None = None) -> dict[str, Any]:
    """
    For server-side errors (unexpected failures).
    HTTP 5xx responses.
    """
    payload: dict[str, Any] = {"status": "error", "message": message}
    if code is not None:
        payload["code"] = code
    return payload
