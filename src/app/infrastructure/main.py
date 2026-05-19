"""
FastAPI application factory.
This is the infrastructure entry point — wires the DI container, registers
routers, and installs global exception handlers.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.domain.exceptions.item_errors import ItemAlreadyExistsError, ItemNotFoundError
from app.infrastructure.adapters.inbound.http.health_router import (
    router as health_router,
)
from app.infrastructure.adapters.inbound.http.item_router import router as item_router
from app.infrastructure.adapters.inbound.http.jsend import error as jsend_error
from app.infrastructure.adapters.inbound.http.jsend import fail as jsend_fail
from app.infrastructure.config.container import Container
from app.infrastructure.config.settings import get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    # ── DI container ────────────────────────────────────────────────────────
    container = Container()
    container.wire(
        modules=[
            "app.infrastructure.adapters.inbound.http.item_router",
        ]
    )

    # ── FastAPI app ──────────────────────────────────────────────────────────
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Hexagonal Architecture Backend Template",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.container = container  # type: ignore[attr-defined]

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
    app.include_router(health_router)  # /health, /ready, /ping
    app.include_router(item_router, prefix=api_prefix)  # /api/v1/items

    # ── Global exception handlers (domain → JSend) ────────────────────────────
    @app.exception_handler(ItemNotFoundError)
    async def item_not_found_handler(
        request: Request, exc: ItemNotFoundError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=jsend_fail({"item_id": str(exc)}),
        )

    @app.exception_handler(ItemAlreadyExistsError)
    async def item_exists_handler(
        request: Request, exc: ItemAlreadyExistsError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content=jsend_fail({"item_id": str(exc)}),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=jsend_error("Internal server error", code=500),
        )

    return app


# Entry point for uvicorn: `uvicorn app.infrastructure.main:app`
app = create_app()
