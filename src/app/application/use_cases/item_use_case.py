"""
Item use case — implements the inbound port, depends on the outbound port.

Rules:
- ONLY imports from domain and application.ports.
- NEVER imports from infrastructure.
- All external dependencies (repository) are injected via constructor.
"""

from app.application.ports.inbound.item_service_port import ItemServicePort
from app.application.ports.outbound.item_repository_port import ItemRepositoryPort
from app.domain.exceptions.item_errors import ItemNotFoundError
from app.domain.models.item import Item, ItemId


class ItemUseCase(ItemServicePort):
    """
    Application use case for Item CRUD operations.
    Implements ItemServicePort (inbound) and uses ItemRepositoryPort (outbound).
    Wired together in infrastructure/config/container.py.
    """

    def __init__(self, repository: ItemRepositoryPort) -> None:
        self._repository = repository

    async def create_item(self, name: str, description: str) -> Item:
        item = Item.create(name=name, description=description)
        return await self._repository.save(item)

    async def get_item(self, item_id: ItemId) -> Item:
        item = await self._repository.find_by_id(item_id)
        if item is None:
            raise ItemNotFoundError(str(item_id))
        return item

    async def get_all_items(self) -> list[Item]:
        return await self._repository.find_all()

    async def update_item(
        self,
        item_id: ItemId,
        name: str | None = None,
        description: str | None = None,
    ) -> Item:
        item = await self.get_item(item_id)
        item.update(name=name, description=description)
        return await self._repository.save(item)

    async def delete_item(self, item_id: ItemId) -> None:
        # Verify existence before deletion
        await self.get_item(item_id)
        await self._repository.delete(item_id)
