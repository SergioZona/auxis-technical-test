"""
Health and ping/pong endpoints.
These are infrastructure-level probes — no business logic, no use cases.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.infrastructure.adapters.inbound.http.jsend import success
from app.infrastructure.config.settings import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Liveness probe",
    description="Returns 200 when the service is running. Use for Docker/K8s liveness checks.",
    response_description="Service health status",
)
async def health(
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    """Liveness probe — the app is up and responsive."""
    return success(
        {
            "status": "healthy",
            "service": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
        }
    )


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Returns 200 when the service is ready to handle traffic.",
)
async def ready(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, Any]:
    """
    Readiness probe — placeholder.
    In production: check DB connectivity, cache, external deps.
    """
    return success(
        {
            "status": "ready",
            "service": settings.app_name,
        }
    )



