"""
FastAPI application factory.
This is the infrastructure entry point — wires the DI container, registers
routers, and installs global exception handlers.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.domain.exceptions.document_errors import (
    ExtractionFailedError,
    FileSizeLimitExceededError,
    InvalidFileFormatError,
    OCRFailureError,
)
from app.infrastructure.adapters.inbound.http.document_router import (
    router as document_router,
)
from app.infrastructure.adapters.inbound.http.health_router import (
    router as health_router,
)
from app.infrastructure.adapters.inbound.http.jsend import error as jsend_error
from app.infrastructure.adapters.inbound.http.jsend import fail as jsend_fail
from app.infrastructure.adapters.outbound.persistence.database import Base, engine
# ↓ Must be imported so SQLAlchemy registers the table with Base.metadata BEFORE create_all
from app.infrastructure.adapters.outbound.persistence.document_repository import DocumentModel  # noqa: F401
from app.infrastructure.config.container import Container
from app.infrastructure.config.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    # ── DI container ────────────────────────────────────────────────────────
    container = Container()
    container.wire(
        modules=[
            "app.infrastructure.adapters.inbound.http.document_router",
        ]
    )

    # ── FastAPI app ──────────────────────────────────────────────────────────
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI Engineer Tax Document Extraction API — Hexagonal Architecture",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.container = container  # type: ignore[attr-defined]

    # ── Startup: Create DB tables ─────────────────────────────────────────────
    @app.on_event("startup")
    async def on_startup() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # ── CORS ─────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_hosts,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routers ───────────────────────────────────────────────────────────────
    api_prefix = f"/api/{settings.api_version}"
    app.include_router(health_router)                       # /health, /ready, /ping
    app.include_router(document_router, prefix=api_prefix)  # /api/v1/documents

    # ── Global exception handlers (domain → JSend) ────────────────────────────

    @app.exception_handler(InvalidFileFormatError)
    async def invalid_file_format_handler(
        request: Request, exc: InvalidFileFormatError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=jsend_fail({"detail": str(exc)}),
        )

    @app.exception_handler(FileSizeLimitExceededError)
    async def file_size_handler(
        request: Request, exc: FileSizeLimitExceededError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=413,
            content=jsend_fail({"detail": str(exc)}),
        )

    @app.exception_handler(ExtractionFailedError)
    async def extraction_failed_handler(
        request: Request, exc: ExtractionFailedError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=jsend_error(str(exc), code=422),
        )

    @app.exception_handler(OCRFailureError)
    async def ocr_failure_handler(
        request: Request, exc: OCRFailureError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=jsend_error(str(exc), code=422),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=jsend_error("Internal server error", code=500),
        )

    def custom_openapi() -> dict:
        """
        Swagger UI 5.x broke file upload rendering when FastAPI / Starlette
        switched from `format: binary` to `contentMediaType: application/octet-stream`.
        This patch restores the old schema so the file-picker button appears.
        """
        if app.openapi_schema:
            return app.openapi_schema

        from fastapi.openapi.utils import get_openapi

        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
        )

        def _fix(obj: dict) -> None:
            if obj.get("contentMediaType") == "application/octet-stream":
                obj.pop("contentMediaType", None)
                obj.pop("contentEncoding", None)
                obj["type"] = "string"
                obj["format"] = "binary"
            for value in obj.values():
                if isinstance(value, dict):
                    _fix(value)

        for component_schema in schema.get("components", {}).get("schemas", {}).values():
            _fix(component_schema)

        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]

    return app



# Entry point for uvicorn: `uvicorn app.infrastructure.main:app`
app = create_app()
