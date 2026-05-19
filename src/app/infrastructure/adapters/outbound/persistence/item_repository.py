"""
SQLAlchemy async PostgreSQL repository — outbound adapter.
Implements ItemRepositoryPort (the driven port).

This is a PLACEHOLDER. All methods raise NotImplementedError with clear guidance.
Replace each method body with real SQLAlchemy async queries.
"""

from app.application.ports.outbound.item_repository_port import ItemRepositoryPort
from app.domain.models.item import Item, ItemId


class SQLAlchemyItemRepository(ItemRepositoryPort):
    """
    Outbound adapter: PostgreSQL via SQLAlchemy async.

    To implement:
    1. Inject an AsyncSession via __init__
    2. Create an ORM model (e.g., ItemModel) mapped to the `items` table
    3. Implement each method using `session.execute(select(ItemModel)...)` etc.

    Example __init__:
        def __init__(self, session: AsyncSession) -> None:
            self._session = session
    """

    async def save(self, item: Item) -> Item:
        """
        INSERT or UPDATE the item record.
        Use session.merge() for upsert behaviour.
        """
        raise NotImplementedError(
            "Implement save() using SQLAlchemy AsyncSession.merge()"
        )

    async def find_by_id(self, item_id: ItemId) -> Item | None:
        """
        SELECT * FROM items WHERE id = :item_id
        Return None if not found — do NOT raise here.
        """
        raise NotImplementedError(
            "Implement find_by_id() using SQLAlchemy AsyncSession.get()"
        )

    async def find_all(self) -> list[Item]:
        """
        SELECT * FROM items ORDER BY created_at DESC
        """
        raise NotImplementedError(
            "Implement find_all() using SQLAlchemy select(ItemModel)"
        )

    async def delete(self, item_id: ItemId) -> None:
        """
        DELETE FROM items WHERE id = :item_id
        """
        raise NotImplementedError(
            "Implement delete() using SQLAlchemy AsyncSession.delete()"
        )
