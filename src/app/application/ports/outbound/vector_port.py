import abc
from uuid import UUID

from app.domain.models.document import DocumentChunk


class VectorPort(abc.ABC):
    """
    Outbound port for vector database operations (e.g., Qdrant).
    """

    @abc.abstractmethod
    async def upsert_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Upserts a list of document chunks into the vector database."""
        pass

    @abc.abstractmethod
    async def search(self, query_text: str, limit: int = 5) -> list[DocumentChunk]:
        """Searches the vector database for chunks similar to the query."""
        pass

    @abc.abstractmethod
    async def delete_by_document_id(self, document_id: UUID) -> None:
        """Deletes all chunks associated with a specific document ID."""
        pass
