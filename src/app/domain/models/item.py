"""Item entity and ItemId value object."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.models.shared import Entity, ValueObject


@dataclass(frozen=True)
class ItemId(ValueObject):
    """Strongly-typed identifier for an Item."""

    value: UUID

    @classmethod
    def generate(cls) -> ItemId:
        return cls(value=uuid4())

    def __str__(self) -> str:
        return str(self.value)


@dataclass
class Item(Entity):
    """
    Item aggregate root.
    Represents the core business concept of this template.
    Replace with your own domain entity.
    """

    id: ItemId
    name: str
    description: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(cls, name: str, description: str) -> Item:
        """Factory method — the only way to create a new Item."""
        return cls(
            id=ItemId.generate(),
            name=name,
            description=description,
        )

    def update(
        self,
        name: str | None = None,
        description: str | None = None,
    ) -> None:
        """Apply allowed mutations and refresh the updated_at timestamp."""
        if name is not None:
            self.name = name
        if description is not None:
            self.description = description
        self.updated_at = datetime.now(UTC)
