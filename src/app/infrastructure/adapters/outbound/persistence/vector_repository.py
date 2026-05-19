import logging
from typing import List
from uuid import UUID

from fastembed import TextEmbedding
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models

from app.application.ports.outbound.vector_port import VectorPort
from app.domain.models.document import DocumentChunk
from app.infrastructure.config.settings import get_settings

logger = logging.getLogger(__name__)


class QdrantVectorRepository(VectorPort):
    def __init__(self):
        self.settings = get_settings()
        self.client = AsyncQdrantClient(host=self.settings.qdrant_host, port=self.settings.qdrant_port, check_compatibility=False)
        self.collection_name = self.settings.qdrant_collection
        # Using Hugging Face BAAI/bge-small-en-v1.5 locally via FastEmbed
        self.embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        # Ensure collection exists asynchronously
        # For a true async setup, initialization might happen elsewhere, 
        # but FastEmbed uses sync generators which we'll handle gracefully.

    async def _ensure_collection(self):
        if not await self.client.collection_exists(self.collection_name):
            # FastEmbed bge-small-en-v1.5 has dim=384
            await self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=384,
                    distance=models.Distance.COSINE
                )
            )

    async def upsert_chunks(self, chunks: List[DocumentChunk]) -> None:
        if not chunks:
            return

        await self._ensure_collection()

        texts = [chunk.text for chunk in chunks]
        
        # FastEmbed is sync, so we run it in a thread or just call it directly 
        # (it's fast enough for small chunks, but thread is safer for event loop)
        import asyncio
        loop = asyncio.get_running_loop()
        embeddings_generator = await loop.run_in_executor(None, lambda: list(self.embedding_model.embed(texts)))
        
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
                        "chunk_index": chunk.chunk_index
                    }
                )
            )

        await self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

    async def search(self, query_text: str, limit: int = 5) -> List[DocumentChunk]:
        await self._ensure_collection()

        import asyncio
        loop = asyncio.get_running_loop()
        query_vector = await loop.run_in_executor(
            None, lambda: list(self.embedding_model.embed([query_text]))[0].tolist()
        )

        search_result = await self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit
        )

        results = []
        for hit in search_result.points:
            results.append(
                DocumentChunk(
                    id=UUID(hit.id),
                    document_id=UUID(hit.payload["document_id"]),
                    text=hit.payload["text"],
                    page_number=hit.payload.get("page_number"),
                    chunk_index=hit.payload.get("chunk_index", 0),
                    embedding=hit.vector
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
                            match=models.MatchValue(value=str(document_id))
                        )
                    ]
                )
            )
        )
