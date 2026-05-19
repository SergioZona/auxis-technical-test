"""Domain-specific exceptions for the Item aggregate."""


class ItemNotFoundError(Exception):
    """Raised when an Item cannot be found by its id."""

    def __init__(self, item_id: str) -> None:
        self.item_id = item_id
        super().__init__(f"Item '{item_id}' not found.")


class ItemAlreadyExistsError(Exception):
    """Raised when trying to create an Item that already exists."""

    def __init__(self, item_id: str) -> None:
        self.item_id = item_id
        super().__init__(f"Item '{item_id}' already exists.")
