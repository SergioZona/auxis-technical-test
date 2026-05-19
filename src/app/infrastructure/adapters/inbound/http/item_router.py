"""
Item HTTP router — inbound adapter.
Translates HTTP ↔ domain. Calls the use case via the inbound port.
Never contains business logic.
"""

from typing import Annotated, Any
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, status

from app.application.ports.inbound.item_service_port import ItemServicePort
from app.domain.models.item import ItemId
from app.infrastructure.adapters.inbound.http.jsend import success
from app.infrastructure.adapters.inbound.http.schemas import (
    CreateItemRequest,
    UpdateItemRequest,
)
from app.infrastructure.config.container import Container

router = APIRouter(prefix="/items", tags=["items"])


def _serialize(item: Any) -> dict[str, Any]:
    """Map a domain Item to a dict matching ItemResponse."""
    return {
        "id": item.id.value,
        "name": item.name,
        "description": item.description,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


@router.post("", status_code=status.HTTP_201_CREATED, response_model=None)
@inject
async def create_item(
    body: CreateItemRequest,
    service: Annotated[ItemServicePort, Depends(Provide[Container.item_use_case])],
) -> dict[str, Any]:
    item = await service.create_item(name=body.name, description=body.description)
    return success(_serialize(item))


@router.get("", response_model=None)
@inject
async def list_items(
    service: Annotated[ItemServicePort, Depends(Provide[Container.item_use_case])],
) -> dict[str, Any]:
    items = await service.get_all_items()
    return success([_serialize(i) for i in items])


@router.get("/{item_id}", response_model=None)
@inject
async def get_item(
    item_id: UUID,
    service: Annotated[ItemServicePort, Depends(Provide[Container.item_use_case])],
) -> dict[str, Any]:
    item = await service.get_item(ItemId(value=item_id))
    return success(_serialize(item))


@router.patch("/{item_id}", response_model=None)
@inject
async def update_item(
    item_id: UUID,
    body: UpdateItemRequest,
    service: Annotated[ItemServicePort, Depends(Provide[Container.item_use_case])],
) -> dict[str, Any]:
    item = await service.update_item(
        ItemId(value=item_id),
        name=body.name,
        description=body.description,
    )
    return success(_serialize(item))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def delete_item(
    item_id: UUID,
    service: Annotated[ItemServicePort, Depends(Provide[Container.item_use_case])],
) -> None:
    await service.delete_item(ItemId(value=item_id))
