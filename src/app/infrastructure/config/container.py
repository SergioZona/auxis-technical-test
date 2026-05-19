"""
DI Container — composition root.
This is the ONLY place where concrete implementations are wired to abstractions.
Nothing outside this file should instantiate adapters or use cases directly.
"""

from dependency_injector import containers, providers

from app.application.use_cases.item_use_case import ItemUseCase
from app.infrastructure.adapters.outbound.persistence.item_repository import (
    SQLAlchemyItemRepository,
)
from app.infrastructure.config.settings import Settings, get_settings


class Container(containers.DeclarativeContainer):
    """
    Dependency injection container.
    Wires: outbound adapters → use cases → inbound adapters.

    Usage:
        container = Container()
        container.wire(modules=[__name__])
    """

    # ── Settings ──────────────────────────────────────────────────────────────
    settings: providers.Singleton[Settings] = providers.Singleton(get_settings)

    # ── Outbound adapters (driven) ─────────────────────────────────────────────
    # Replace SQLAlchemyItemRepository with your real implementation.
    # For testing, override with a mock/in-memory repo:
    #   container.item_repository.override(InMemoryItemRepository())
    item_repository: providers.Factory[SQLAlchemyItemRepository] = providers.Factory(
        SQLAlchemyItemRepository,
    )

    # ── Use cases (application) ───────────────────────────────────────────────
    item_use_case: providers.Factory[ItemUseCase] = providers.Factory(
        ItemUseCase,
        repository=item_repository,
    )
