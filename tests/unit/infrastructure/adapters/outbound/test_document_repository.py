from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.domain.models.document import Document
from app.infrastructure.adapters.outbound.persistence.document_repository import (
    DocumentModel,
    PostgresDocumentRepository,
    _model_to_domain,
)


@pytest.fixture
def mock_session() -> MagicMock:
    session = MagicMock()
    session.commit = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def repo(mock_session: MagicMock) -> PostgresDocumentRepository:
    return PostgresDocumentRepository(mock_session)


def test_model_to_domain() -> None:
    model = DocumentModel(
        id=uuid4(),
        filename="test.pdf",
        document_type="invoice",
        doc_date="2024-08-08",
        doc_number="12345",
        vendor_name="Vendor Inc",
        client_name="Client LLC",
        total_amount=50000.0,
        tax_amount=1000.0,
        extraction_method="text",
        file_size_bytes=1000,
        page_count=1,
        processing_time_ms=100,
        tables=[{"description": "Item 1", "total": 50000.0}],
        extras={"custom_field": "val"},
    )
    domain = _model_to_domain(model)
    assert domain.id == model.id
    assert domain.filename == "test.pdf"
    assert domain.document_type == "invoice"


async def test_repo_save(
    repo: PostgresDocumentRepository, mock_session: AsyncMock
) -> None:
    doc = Document(filename="test.pdf", document_type="invoice")
    result = await repo.save(doc)
    assert result == doc
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()


async def test_repo_get_by_id_found(
    repo: PostgresDocumentRepository, mock_session: AsyncMock
) -> None:
    doc_id = uuid4()
    model = DocumentModel(
        id=doc_id,
        filename="test.pdf",
        document_type="invoice",
        extras={},
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = model
    mock_session.execute.return_value = mock_result

    result = await repo.get_by_id(doc_id)
    assert result is not None
    assert result.id == doc_id
    assert result.filename == "test.pdf"


async def test_repo_get_by_id_not_found(
    repo: PostgresDocumentRepository, mock_session: AsyncMock
) -> None:
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    result = await repo.get_by_id(uuid4())
    assert result is None


async def test_repo_list_all(
    repo: PostgresDocumentRepository, mock_session: AsyncMock
) -> None:
    model1 = DocumentModel(
        id=uuid4(), filename="file1.pdf", document_type="invoice", extras={}
    )
    model2 = DocumentModel(
        id=uuid4(), filename="file2.pdf", document_type="invoice", extras={}
    )

    mock_result = MagicMock()
    mock_result.scalars().all.return_value = [model1, model2]
    mock_session.execute.return_value = mock_result

    result = await repo.list_all(limit=5, offset=1)
    assert len(result) == 2
    assert result[0].filename == "file1.pdf"
    assert result[1].filename == "file2.pdf"


async def test_repo_update_found(
    repo: PostgresDocumentRepository, mock_session: AsyncMock
) -> None:
    doc_id = uuid4()
    model = DocumentModel(
        id=doc_id,
        filename="test.pdf",
        document_type="invoice",
        extras={},
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = model
    mock_session.execute.return_value = mock_result

    doc = Document(id=doc_id, filename="test.pdf", document_type="receipt")
    result = await repo.update(doc)
    assert result.document_type == "receipt"
    assert model.document_type == "receipt"
    mock_session.commit.assert_called_once()


async def test_repo_update_not_found(
    repo: PostgresDocumentRepository, mock_session: AsyncMock
) -> None:
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    doc = Document(id=uuid4(), filename="test.pdf", document_type="receipt")
    result = await repo.update(doc)
    assert result == doc
    mock_session.commit.assert_not_called()
