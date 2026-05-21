from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.exceptions.document_errors import (
    ExtractionFailedError,
    FileSizeLimitExceededError,
    InvalidFileFormatError,
    OCRFailureError,
)
from app.infrastructure.main import create_app


@pytest.mark.anyio
async def test_lifespan_execution():
    with patch("app.infrastructure.main.engine") as mock_engine:
        mock_conn = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.begin.return_value.__aexit__ = AsyncMock(return_value=None)

        app = create_app()
        async with app.router.lifespan_context(app):
            pass

        mock_engine.begin.assert_called_once()
        mock_conn.run_sync.assert_called_once()


@pytest.mark.anyio
async def test_openapi_schema_fix():
    app = create_app()
    # First call generates the schema and fixes octet-stream
    schema = app.openapi()
    assert "openapi" in schema

    # Second call should return cached schema
    cached_schema = app.openapi()
    assert cached_schema is schema


@pytest.mark.anyio
async def test_global_exception_handlers():
    app = create_app()

    @app.get("/test-exception/invalid-file")
    async def trigger_invalid_file():
        raise InvalidFileFormatError("Invalid format")

    @app.get("/test-exception/size")
    async def trigger_size():
        raise FileSizeLimitExceededError("Size limit exceeded")

    @app.get("/test-exception/extract")
    async def trigger_extract():
        raise ExtractionFailedError("Extraction failed")

    @app.get("/test-exception/ocr")
    async def trigger_ocr():
        raise OCRFailureError("OCR failed")

    @app.get("/test-exception/generic")
    async def trigger_generic():
        raise Exception("Generic error")

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        # Trigger and test exception handlers
        res = await client.get("/test-exception/invalid-file")
        assert res.status_code == 400
        assert res.json()["status"] == "fail"

        res = await client.get("/test-exception/size")
        assert res.status_code == 413
        assert res.json()["status"] == "fail"

        res = await client.get("/test-exception/extract")
        assert res.status_code == 422
        assert res.json()["status"] == "error"

        res = await client.get("/test-exception/ocr")
        assert res.status_code == 422
        assert res.json()["status"] == "error"

        res = await client.get("/test-exception/generic")
        assert res.status_code == 500
        assert res.json()["status"] == "error"
