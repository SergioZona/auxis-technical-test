from unittest.mock import AsyncMock

import pytest

from app.application.use_cases.process_documents_use_case import ProcessDocumentsUseCase
from app.domain.exceptions.document_errors import FileSizeLimitExceededError
from app.domain.models.document import Document, DocumentChunk


@pytest.fixture
def mock_parser() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_vector_db() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def use_case(
    mock_parser: AsyncMock, mock_vector_db: AsyncMock
) -> ProcessDocumentsUseCase:
    return ProcessDocumentsUseCase(
        parser=mock_parser,
        vector_db=mock_vector_db,
        max_upload_size_mb=1,
    )


async def test_process_documents_success(
    use_case: ProcessDocumentsUseCase,
    mock_parser: AsyncMock,
    mock_vector_db: AsyncMock,
    mock_repository: AsyncMock,
) -> None:
    # Setup mock parser to return a Document with chunk
    doc = Document(filename="test.pdf", extraction_method="text")
    chunk = DocumentChunk(text="Sample text", chunk_index=0)
    doc.add_chunk(chunk)
    mock_parser.parse.return_value = doc

    # Setup mock DB repository
    mock_repository.save.return_value = doc

    # Execute
    files = [("test.pdf", b"Some content")]
    result = await use_case.execute(files=files, repository=mock_repository)

    # Assertions
    assert len(result) == 1
    assert result[0] == doc
    mock_parser.parse.assert_called_once_with(b"Some content", "test.pdf")
    mock_repository.save.assert_called_once_with(doc)
    mock_vector_db.upsert_chunks.assert_called_once_with(doc.chunks)


async def test_process_documents_file_size_exceeded(
    use_case: ProcessDocumentsUseCase,
    mock_repository: AsyncMock,
) -> None:
    # 2 MB is larger than our use_case's max_upload_size_mb (1 MB)
    large_content = b"a" * (2 * 1024 * 1024)
    files = [("large.pdf", large_content)]

    with pytest.raises(FileSizeLimitExceededError):
        await use_case.execute(files=files, repository=mock_repository)
