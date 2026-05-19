"""Shared base classes for domain entities and value objects."""

from dataclasses import dataclass


@dataclass
class Entity:
    """
    Base class for all domain entities.
    Entities have identity — two entities with the same id are the same,
    regardless of their other attributes.
    """


@dataclass(frozen=True)
class ValueObject:
    """
    Base class for all value objects.
    Value objects are immutable. Equality is based on their attributes,
    not on identity.
    """
