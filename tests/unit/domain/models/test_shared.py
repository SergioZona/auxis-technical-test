from dataclasses import dataclass

from app.domain.models.shared import Entity, ValueObject


def test_entity_base_class() -> None:
    """Verifies that Entity base class can be inherited."""

    @dataclass
    class DummyEntity(Entity):
        id: str

    e1 = DummyEntity(id="1")
    e2 = DummyEntity(id="1")

    # Dataclass automatically provides equality based on fields
    assert e1 == e2


def test_value_object_base_class() -> None:
    """Verifies that ValueObject base class can be inherited and is frozen."""

    @dataclass(frozen=True)
    class DummyVO(ValueObject):
        value: str

    v1 = DummyVO(value="test")
    v2 = DummyVO(value="test")

    assert v1 == v2
