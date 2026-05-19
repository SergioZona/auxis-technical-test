"""Unit tests for the Item domain model."""

from datetime import datetime

from app.domain.models.item import Item, ItemId


def test_item_create_sets_fields() -> None:
    item = Item.create(name="Widget", description="A test widget")
    assert item.name == "Widget"
    assert item.description == "A test widget"
    assert isinstance(item.id, ItemId)
    assert isinstance(item.created_at, datetime)
    assert isinstance(item.updated_at, datetime)


def test_item_ids_are_unique() -> None:
    id1 = ItemId.generate()
    id2 = ItemId.generate()
    assert id1 != id2


def test_item_id_str() -> None:
    item_id = ItemId.generate()
    assert len(str(item_id)) == 36  # UUID string length


def test_item_update_name() -> None:
    item = Item.create(name="Original", description="Desc")
    original_updated_at = item.updated_at
    item.update(name="Updated")
    assert item.name == "Updated"
    assert item.description == "Desc"
    assert item.updated_at >= original_updated_at


def test_item_update_description() -> None:
    item = Item.create(name="Name", description="Old desc")
    item.update(description="New desc")
    assert item.description == "New desc"
    assert item.name == "Name"


def test_item_update_noop_with_none() -> None:
    item = Item.create(name="Name", description="Desc")
    item.update(name=None, description=None)
    assert item.name == "Name"
    assert item.description == "Desc"
