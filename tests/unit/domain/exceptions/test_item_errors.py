from app.domain.exceptions.item_errors import ItemNotFoundError


def test_item_not_found_error() -> None:
    """Verifies the custom exception can be raised and stringified correctly."""
    error = ItemNotFoundError("test-item-123")
    assert isinstance(error, Exception)
    assert "test-item-123" in str(error)
