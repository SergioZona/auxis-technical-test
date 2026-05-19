"""Inbound port — defines what the application exposes to driving adapters."""

from abc import ABC, abstractmethod

from app.domain.models.item import Item, ItemId


class ItemServicePort(ABC):
    """
    Driving port (inbound).
    Implemented by: ItemUseCase (application layer).
    Called by: HTTP router (infrastructure/inbound adapter).

    This ABC is the contract between the outside world and the application core.
    Do NOT import infrastructure types here.
    """

    @abstractmethod
    async def create_item(self, name: str, description: str) -> Item:
        """Create and persist a new item."""
        ...

    @abstractmethod
    async def get_item(self, item_id: ItemId) -> Item:
        """Return a single item by its id. Raises ItemNotFoundError if missing."""
        ...

    @abstractmethod
    async def get_all_items(self) -> list[Item]:
        """Return all items."""
        ...

    @abstractmethod
    async def update_item(
        self,
        item_id: ItemId,
        name: str | None,
        description: str | None,
    ) -> Item:
        """Partially update an item. Raises ItemNotFoundError if missing."""
        ...

    @abstractmethod
    async def delete_item(self, item_id: ItemId) -> None:
        """Delete an item. Raises ItemNotFoundError if missing."""
        ...
