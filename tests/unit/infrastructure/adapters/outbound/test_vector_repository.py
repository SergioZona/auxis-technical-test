from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.domain.models.document import DocumentChunk
from app.infrastructure.adapters.outbound.persistence.vector_repository import (
    QdrantVectorRepository,
)


@pytest.fixture
def mock_qdrant_and_embedding():
    with (
        patch(
            "app.infrastructure.adapters.outbound.persistence.vector_repository.get_qdrant_client"
        ) as mock_get_client,
        patch(
            "app.infrastructure.adapters.outbound.persistence.vector_repository.get_embedding_model"
        ) as mock_get_model,
    ):
        mock_client = AsyncMock()
        mock_get_client.return_value = mock_client

        mock_embedding = MagicMock()
        mock_get_model.return_value = mock_embedding

        yield mock_client, mock_embedding


@pytest.mark.anyio
async def test_ensure_collection_creates_if_not_exists(
    mock_qdrant_and_embedding,
) -> None:
    mock_client, _ = mock_qdrant_and_embedding
    mock_client.collection_exists.return_value = False

    repo = QdrantVectorRepository()
    await repo._ensure_collection()

    mock_client.collection_exists.assert_called_once_with(repo.collection_name)
    mock_client.create_collection.assert_called_once()


@pytest.mark.anyio
async def test_ensure_collection_skips_if_exists(mock_qdrant_and_embedding) -> None:
    mock_client, _ = mock_qdrant_and_embedding
    mock_client.collection_exists.return_value = True

    repo = QdrantVectorRepository()
    await repo._ensure_collection()

    mock_client.collection_exists.assert_called_once_with(repo.collection_name)
    mock_client.create_collection.assert_not_called()


@pytest.mark.anyio
async def test_upsert_chunks_empty(mock_qdrant_and_embedding) -> None:
    mock_client, _ = mock_qdrant_and_embedding

    repo = QdrantVectorRepository()
    await repo.upsert_chunks([])

    mock_client.collection_exists.assert_not_called()


@pytest.mark.anyio
async def test_upsert_chunks_success(mock_qdrant_and_embedding) -> None:
    mock_client, mock_embedding = mock_qdrant_and_embedding
    mock_client.collection_exists.return_value = True

    import numpy as np

    mock_embedding.embed.return_value = [np.array([0.1, 0.2])]

    repo = QdrantVectorRepository()
    chunk = DocumentChunk(text="Hello world", chunk_index=1, page_number=2)

    await repo.upsert_chunks([chunk])

    assert chunk.embedding == [0.1, 0.2]
    mock_client.upsert.assert_called_once()


@pytest.mark.anyio
async def test_search_success(mock_qdrant_and_embedding) -> None:
    mock_client, mock_embedding = mock_qdrant_and_embedding
    mock_client.collection_exists.return_value = True

    import numpy as np

    mock_embedding.embed.return_value = [np.array([0.1, 0.2])]

    # Setup mock query response
    mock_hit = MagicMock()
    mock_hit.id = str(uuid4())
    mock_hit.payload = {
        "document_id": str(uuid4()),
        "text": "result text",
        "page_number": 3,
        "chunk_index": 5,
    }
    mock_hit.vector = [0.1, 0.2]

    mock_search_result = MagicMock()
    mock_search_result.points = [mock_hit]
    mock_client.query_points.return_value = mock_search_result

    repo = QdrantVectorRepository()
    results = await repo.search("query text", limit=2)

    assert len(results) == 1
    assert results[0].text == "result text"
    assert results[0].page_number == 3
    assert results[0].chunk_index == 5
    assert results[0].embedding == [0.1, 0.2]
    mock_client.query_points.assert_called_once()


@pytest.mark.anyio
async def test_delete_by_document_id(mock_qdrant_and_embedding) -> None:
    mock_client, _ = mock_qdrant_and_embedding
    mock_client.collection_exists.return_value = True

    repo = QdrantVectorRepository()
    doc_id = uuid4()
    await repo.delete_by_document_id(doc_id)

    mock_client.delete.assert_called_once()
