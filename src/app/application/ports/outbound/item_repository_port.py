"""Outbound port — defines what the application needs from driven adapters."""

from abc import ABC, abstractmethod

from app.domain.models.item import Item, ItemId


class ItemRepositoryPort(ABC):
    """
    Driven port (outbound).
    Implemented by: SQLAlchemyItemRepository (infrastructure/outbound adapter).
    Used by: ItemUseCase (application layer).

    This ABC is the contract between the application core and the outside world.
    Do NOT import infrastructure types here.
    """

    @abstractmethod
    async def save(self, item: Item) -> Item:
        """Persist an item (create or update). Returns the saved item."""
        ...

    @abstractmethod
    async def find_by_id(self, item_id: ItemId) -> Item | None:
        """Return an item by id, or None if not found."""
        ...

    @abstractmethod
    async def find_all(self) -> list[Item]:
        """Return all persisted items."""
        ...

    @abstractmethod
    async def delete(self, item_id: ItemId) -> None:
        """Delete an item by id. No-op if not found."""
        ...
