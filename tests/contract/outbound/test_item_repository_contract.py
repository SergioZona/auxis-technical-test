"""
Contract tests for ItemRepositoryPort.
Every concrete repository implementation MUST pass this suite.
Add a new TestXxxRepo class for each new adapter implementation.
"""

from typing import TYPE_CHECKING

import pytest

from app.domain.models.item import Item, ItemId

if TYPE_CHECKING:
    from app.application.ports.outbound.item_repository_port import ItemRepositoryPort


class ItemRepositoryContract:
    """
    Abstract contract — all repo implementations must satisfy these tests.
    Subclasses provide the `repo` fixture with a concrete implementation.
    """

    @pytest.fixture
    def repo(self) -> ItemRepositoryPort:
        raise NotImplementedError("Subclass must provide a `repo` fixture")

    async def test_save_returns_item(self, repo: ItemRepositoryPort) -> None:
        item = Item.create(name="Widget", description="Desc")
        result = await repo.save(item)
        assert result.id == item.id
        assert result.name == item.name

    async def test_find_by_id_returns_saved_item(
        self, repo: ItemRepositoryPort
    ) -> None:
        item = Item.create(name="Widget", description="Desc")
        await repo.save(item)
        found = await repo.find_by_id(item.id)
        assert found is not None
        assert found.id == item.id

    async def test_find_by_id_returns_none_when_missing(
        self, repo: ItemRepositoryPort
    ) -> None:
        result = await repo.find_by_id(ItemId.generate())
        assert result is None

    async def test_find_all_returns_all_items(self, repo: ItemRepositoryPort) -> None:
        item1 = Item.create(name="A", description="D1")
        item2 = Item.create(name="B", description="D2")
        await repo.save(item1)
        await repo.save(item2)
        all_items = await repo.find_all()
        ids = [i.id for i in all_items]
        assert item1.id in ids
        assert item2.id in ids

    async def test_delete_removes_item(self, repo: ItemRepositoryPort) -> None:
        item = Item.create(name="ToDelete", description="Bye")
        await repo.save(item)
        await repo.delete(item.id)
        found = await repo.find_by_id(item.id)
        assert found is None


# ── Placeholder: wire your actual implementation once it is ready ─────────────
# class TestSQLAlchemyItemRepository(ItemRepositoryContract):
#     @pytest.fixture
#     async def repo(self, db_session):
#         return SQLAlchemyItemRepository(db_session)
