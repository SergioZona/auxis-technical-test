"""
Unit tests for ItemUseCase.
All outbound dependencies are mocked — no I/O, no DB, pure logic.
"""

from unittest.mock import AsyncMock

import pytest

from app.application.use_cases.item_use_case import ItemUseCase
from app.domain.exceptions.item_errors import ItemNotFoundError
from app.domain.models.item import Item, ItemId


@pytest.fixture
def mock_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def use_case(mock_repository: AsyncMock) -> ItemUseCase:
    return ItemUseCase(repository=mock_repository)


@pytest.fixture
def sample_item() -> Item:
    return Item.create(name="Widget", description="A sample widget")


async def test_create_item_calls_repository(
    use_case: ItemUseCase,
    mock_repository: AsyncMock,
    sample_item: Item,
) -> None:
    mock_repository.save.return_value = sample_item
    result = await use_case.create_item(name="Widget", description="A sample widget")
    mock_repository.save.assert_called_once()
    assert result.name == "Widget"


async def test_get_item_returns_item(
    use_case: ItemUseCase,
    mock_repository: AsyncMock,
    sample_item: Item,
) -> None:
    mock_repository.find_by_id.return_value = sample_item
    result = await use_case.get_item(sample_item.id)
    assert result == sample_item


async def test_get_item_raises_when_not_found(
    use_case: ItemUseCase,
    mock_repository: AsyncMock,
) -> None:
    mock_repository.find_by_id.return_value = None
    with pytest.raises(ItemNotFoundError):
        await use_case.get_item(ItemId.generate())


async def test_delete_item_calls_repository(
    use_case: ItemUseCase,
    mock_repository: AsyncMock,
    sample_item: Item,
) -> None:
    mock_repository.find_by_id.return_value = sample_item
    mock_repository.delete.return_value = None
    await use_case.delete_item(sample_item.id)
    mock_repository.delete.assert_called_once_with(sample_item.id)


async def test_update_item_raises_when_not_found(
    use_case: ItemUseCase,
    mock_repository: AsyncMock,
) -> None:
    mock_repository.find_by_id.return_value = None
    with pytest.raises(ItemNotFoundError):
        await use_case.update_item(ItemId.generate(), name="New", description=None)
