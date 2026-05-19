import abc
from typing import List, Optional
from uuid import UUID

from app.domain.models.document import Document


class DocumentRepositoryPort(abc.ABC):
    """
    Outbound port for persisting canonical document metadata (e.g., PostgreSQL).
    """

    @abc.abstractmethod
    async def save(self, document: Document) -> Document:
        """Saves a document entity to persistence."""
        pass

    @abc.abstractmethod
    async def get_by_id(self, document_id: UUID) -> Optional[Document]:
        """Retrieves a document by its ID."""
        pass

    @abc.abstractmethod
    async def list_all(self, limit: int = 100, offset: int = 0) -> List[Document]:
        """Lists all stored documents."""
        pass

    @abc.abstractmethod
    async def update(self, document: Document) -> Document:
        """Updates an existing document."""
        pass
