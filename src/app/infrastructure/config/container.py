"""
DI Container — composition root.
This is the ONLY place where concrete implementations are wired to abstractions.
Nothing outside this file should instantiate adapters or use cases directly.
"""

from dependency_injector import containers, providers

from app.application.use_cases.chat_rag_use_case import ChatRagUseCase
from app.application.use_cases.process_documents_use_case import ProcessDocumentsUseCase
from app.application.use_cases.query_database_use_case import QueryDatabaseUseCase
from app.infrastructure.adapters.outbound.ai_extractor import LlmAiExtractor
from app.infrastructure.adapters.outbound.document_parser import PyMuPDFDocumentParser
from app.infrastructure.adapters.outbound.langchain_rag_adapter import LangChainRagAdapter
from app.infrastructure.adapters.outbound.persistence.vector_repository import (
    QdrantVectorRepository,
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

    ai_extractor: providers.Singleton[LlmAiExtractor] = providers.Singleton(
        LlmAiExtractor,
        settings=settings,
    )

    document_parser: providers.Singleton[PyMuPDFDocumentParser] = providers.Singleton(
        PyMuPDFDocumentParser,
        ai_extractor=ai_extractor,
    )

    vector_repository: providers.Singleton[QdrantVectorRepository] = providers.Singleton(
        QdrantVectorRepository,
    )

    langchain_rag_adapter: providers.Singleton[LangChainRagAdapter] = providers.Singleton(
        LangChainRagAdapter,
        settings=settings,
        vector_port=vector_repository,
    )

    # document_repository is session-scoped so it's a Factory injected per request
    # We expose it as a provider but wiring happens at the router level via FastAPI dep

    # ── Use cases (application) ───────────────────────────────────────────────

    process_documents_use_case: providers.Factory[ProcessDocumentsUseCase] = providers.Factory(
        ProcessDocumentsUseCase,
        parser=document_parser,
        vector_db=vector_repository,
        max_upload_size_mb=settings.provided.max_upload_size_mb,
    )

    chat_rag_use_case: providers.Factory[ChatRagUseCase] = providers.Factory(
        ChatRagUseCase,
        langchain_rag=langchain_rag_adapter,
    )

    query_database_use_case: providers.Factory[QueryDatabaseUseCase] = providers.Factory(
        QueryDatabaseUseCase,
        langchain_rag=langchain_rag_adapter,
    )
