import logging
from uuid import UUID

from qdrant_client.http import models

from app.application.ports.outbound.vector_port import VectorPort
from app.domain.models.document import DocumentChunk
from app.infrastructure.config.clients import get_embedding_model, get_qdrant_client
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


class QdrantVectorRepository(VectorPort):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = get_qdrant_client()
        self.collection_name = self.settings.qdrant_collection
        self.embedding_model = get_embedding_model()
        # Ensure collection exists asynchronously
        # For a true async setup, initialization might happen elsewhere,
        # but FastEmbed uses sync generators which we'll handle gracefully.

    async def _ensure_collection(self) -> None:
        if not await self.client.collection_exists(self.collection_name):
            # FastEmbed bge-small-en-v1.5 has dim=384
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=384, distance=models.Distance.COSINE
                ),
            )

    async def upsert_chunks(self, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return

        await self._ensure_collection()

        texts = [chunk.text for chunk in chunks]

        # FastEmbed is sync, so we run it in a thread or just call it directly
        # (it's fast enough for small chunks, but thread is safer for event loop)
        import asyncio

        loop = asyncio.get_running_loop()
        embeddings_generator = await loop.run_in_executor(
            None, lambda: list(self.embedding_model.embed(texts))
        )

        points = []
        for i, chunk in enumerate(chunks):
            # Assign embedding to model for completeness
            chunk.embedding = embeddings_generator[i].tolist()

            points.append(
                models.PointStruct(
                    id=str(chunk.id),
                    vector=chunk.embedding,
                    payload={
                        "document_id": str(chunk.document_id),
                        "text": chunk.text,
                        "page_number": chunk.page_number,
                        "chunk_index": chunk.chunk_index,
                    },
                )
            )

        await self.client.upsert(collection_name=self.collection_name, points=points)

    async def search(self, query_text: str, limit: int = 5) -> list[DocumentChunk]:
        await self._ensure_collection()

        import asyncio

        loop = asyncio.get_running_loop()
        query_vector = await loop.run_in_executor(
            None, lambda: list(self.embedding_model.embed([query_text]))[0].tolist()
        )

        search_result = await self.client.query_points(
            collection_name=self.collection_name, query=query_vector, limit=limit
        )

        results = []
        for hit in search_result.points:
            payload = hit.payload or {}
            vector_data = hit.vector
            embedding: list[float] | None = None
            if isinstance(vector_data, list):
                embedding = [
                    float(x) for x in vector_data if isinstance(x, (int, float))
                ]

            results.append(
                DocumentChunk(
                    id=UUID(str(hit.id)),
                    document_id=UUID(str(payload.get("document_id", "")))
                    if payload.get("document_id")
                    else UUID(int=0),
                    text=str(payload.get("text", "")),
                    page_number=int(payload["page_number"])
                    if payload.get("page_number") is not None
                    else None,
                    chunk_index=int(payload["chunk_index"])
                    if payload.get("chunk_index") is not None
                    else 0,
                    embedding=embedding,
                )
            )
        return results

    async def delete_by_document_id(self, document_id: UUID) -> None:
        await self._ensure_collection()
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=str(document_id)),
                        )
                    ]
                )
            ),
        )
