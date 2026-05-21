import asyncio
import logging

from app.application.ports.outbound.document_parser_port import DocumentParserPort
from app.application.ports.outbound.document_repository_port import (
    DocumentRepositoryPort,
)
from app.application.ports.outbound.vector_port import VectorPort
from app.domain.exceptions.document_errors import FileSizeLimitExceededError
from app.domain.models.document import Document

logger = logging.getLogger(__name__)


class ProcessDocumentsUseCase:
    def __init__(
        self,
        parser: DocumentParserPort,
        vector_db: VectorPort,
        max_upload_size_mb: int = 10,
    ):
        self.parser = parser
        self.vector_db = vector_db
        self.max_upload_size_mb = max_upload_size_mb

    async def execute(
        self, files: list[tuple[str, bytes]], repository: DocumentRepositoryPort
    ) -> list[Document]:
        """
        Process multiple uploaded documents.
        Extracts canonical metadata, generates embeddings for chunks, and persists them.
        To avoid SQLAlchemy AsyncSession concurrent access conflicts, parsing runs in parallel,
        while database persistence runs sequentially.
        """
        max_size_bytes = self.max_upload_size_mb * 1024 * 1024

        for filename, content in files:
            if len(content) > max_size_bytes:
                raise FileSizeLimitExceededError(
                    f"File {filename} exceeds limit of {self.max_upload_size_mb}MB"
                )

        # ── Step 1: Parse all files concurrently (pure CPU/IO, no DB session access) ──
        parse_tasks = [
            self.parser.parse(content, filename) for filename, content in files
        ]
        parse_results = await asyncio.gather(*parse_tasks, return_exceptions=True)

        parsed_documents: list[Document] = []
        for res in parse_results:
            if isinstance(res, Exception):
                logger.error(f"Failed to parse document: {res}")
                raise res
            if not isinstance(res, Document):
                raise TypeError(f"Expected Document, got {type(res)}")
            parsed_documents.append(res)

        # ── Step 2: Persist sequentially to prevent transaction collisions ──
        processed_documents: list[Document] = []
        for doc in parsed_documents:
            saved_doc = await repository.save(doc)
            if saved_doc.chunks:
                for chunk in saved_doc.chunks:
                    chunk.document_id = saved_doc.id
                await self.vector_db.upsert_chunks(saved_doc.chunks)
            processed_documents.append(saved_doc)

        return processed_documents
