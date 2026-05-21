from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.domain.models.document import Document
from app.infrastructure.main import create_app


@pytest.fixture
def mock_process_use_case() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_chat_use_case() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_query_use_case() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def test_app(
    mock_process_use_case: AsyncMock,
    mock_chat_use_case: AsyncMock,
    mock_query_use_case: AsyncMock,
):
    app = create_app()
    app.container.process_documents_use_case.override(mock_process_use_case)
    app.container.chat_rag_use_case.override(mock_chat_use_case)
    app.container.query_database_use_case.override(mock_query_use_case)
    yield app
    app.container.reset_override()


@pytest.fixture
async def test_client(test_app) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as c:
        yield c


@pytest.mark.anyio
async def test_upload_documents_success(
    test_client: AsyncClient, mock_process_use_case: AsyncMock
) -> None:
    doc = Document(
        filename="test.pdf", document_type="invoice", extraction_method="text"
    )
    mock_process_use_case.execute.return_value = [doc]

    # Mock PostgresDocumentRepository to avoid real DB execution
    with patch(
        "app.infrastructure.adapters.inbound.http.document_router.PostgresDocumentRepository"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.save = AsyncMock(return_value=doc)

        files = {"files": ("test.pdf", b"pdf content", "application/pdf")}
        response = await test_client.post("/api/v1/documents/upload", files=files)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert len(body["data"]) == 1
        assert body["data"][0]["filename"] == "test.pdf"


@pytest.mark.anyio
async def test_list_documents_success(test_client: AsyncClient) -> None:
    doc = Document(filename="test.pdf", document_type="invoice")

    with patch(
        "app.infrastructure.adapters.inbound.http.document_router.PostgresDocumentRepository"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.list_all = AsyncMock(return_value=[doc])

        response = await test_client.get("/api/v1/documents")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert len(body["data"]) == 1
        assert body["data"][0]["filename"] == "test.pdf"


@pytest.mark.anyio
async def test_chat_documents_success(
    test_client: AsyncClient, mock_chat_use_case: AsyncMock
) -> None:
    mock_chat_use_case.execute.return_value = {
        "answer": "RAG response",
        "sources": [{"text": "source text"}],
    }

    payload = {"question": "What is tax?"}
    response = await test_client.post("/api/v1/documents/chat", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["response"] == "RAG response"
    assert len(body["data"]["sources"]) == 1


@pytest.mark.anyio
async def test_query_db_success(
    test_client: AsyncClient, mock_query_use_case: AsyncMock
) -> None:
    mock_query_use_case.execute.return_value = "query database result"

    payload = {"query": "Find gross income"}
    response = await test_client.post("/api/v1/documents/query-db", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["data"]["response"] == "query database result"


@pytest.mark.anyio
async def test_get_document_pdf_success(test_client: AsyncClient) -> None:
    doc_id = uuid4()
    doc = Document(id=doc_id, filename="test.pdf")

    with (
        patch(
            "app.infrastructure.adapters.inbound.http.document_router.PostgresDocumentRepository"
        ) as MockRepo,
        patch("os.path.exists", return_value=True),
        patch("fastapi.responses.FileResponse") as MockFileResponse,
    ):
        mock_repo = MockRepo.return_value
        mock_repo.get_by_id = AsyncMock(return_value=doc)

        # Make MockFileResponse look like a valid response
        MockFileResponse.return_value.status_code = 200

        response = await test_client.get(f"/api/v1/documents/{doc_id}/pdf")
        assert response.status_code == 200


@pytest.mark.anyio
async def test_update_document_success(test_client: AsyncClient) -> None:
    doc_id = uuid4()
    doc = Document(id=doc_id, filename="test.pdf", document_type="invoice")

    with patch(
        "app.infrastructure.adapters.inbound.http.document_router.PostgresDocumentRepository"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_by_id = AsyncMock(return_value=doc)
        mock_repo.update = AsyncMock(return_value=doc)

        payload = {"document_type": "receipt"}
        response = await test_client.patch(f"/api/v1/documents/{doc_id}", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["data"]["message"] == "Document updated successfully"
        assert doc.document_type == "receipt"


@pytest.mark.anyio
async def test_upload_non_pdf_file_fails(test_client: AsyncClient) -> None:
    files = {"files": ("test.txt", b"txt content", "text/plain")}
    response = await test_client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert "not a PDF" in response.json()["detail"]


@pytest.mark.anyio
async def test_upload_file_size_exceeded_fails(
    test_client: AsyncClient, mock_process_use_case: AsyncMock
) -> None:
    from app.domain.exceptions.document_errors import FileSizeLimitExceededError

    mock_process_use_case.execute.side_effect = FileSizeLimitExceededError("Too big")

    with patch(
        "app.infrastructure.adapters.inbound.http.document_router.PostgresDocumentRepository"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.save = AsyncMock()
        files = {"files": ("test.pdf", b"pdf content", "application/pdf")}
        response = await test_client.post("/api/v1/documents/upload", files=files)
        assert response.status_code == 413
        assert "Too big" in response.json()["detail"]


@pytest.mark.anyio
async def test_upload_generic_exception_fails(
    test_client: AsyncClient, mock_process_use_case: AsyncMock
) -> None:
    mock_process_use_case.execute.side_effect = Exception("Generic upload error")

    with patch(
        "app.infrastructure.adapters.inbound.http.document_router.PostgresDocumentRepository"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.save = AsyncMock()
        files = {"files": ("test.pdf", b"pdf content", "application/pdf")}
        response = await test_client.post("/api/v1/documents/upload", files=files)
        assert response.status_code == 500
        assert "Generic upload error" in response.json()["detail"]


@pytest.mark.anyio
async def test_chat_generic_exception_fails(
    test_client: AsyncClient, mock_chat_use_case: AsyncMock
) -> None:
    mock_chat_use_case.execute.side_effect = Exception("Chat failed")
    payload = {"question": "What is tax?"}
    response = await test_client.post("/api/v1/documents/chat", json=payload)
    assert response.status_code == 500
    assert "Chat failed" in response.json()["detail"]


@pytest.mark.anyio
async def test_query_db_generic_exception_fails(
    test_client: AsyncClient, mock_query_use_case: AsyncMock
) -> None:
    mock_query_use_case.execute.side_effect = Exception("Query failed")
    payload = {"query": "Find gross income"}
    response = await test_client.post("/api/v1/documents/query-db", json=payload)
    assert response.status_code == 500
    assert "Query failed" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_document_pdf_invalid_uuid_fails(test_client: AsyncClient) -> None:
    response = await test_client.get("/api/v1/documents/invalid-uuid/pdf")
    assert response.status_code == 400
    assert "Invalid UUID format" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_document_pdf_not_found_fails(test_client: AsyncClient) -> None:
    doc_id = uuid4()
    with patch(
        "app.infrastructure.adapters.inbound.http.document_router.PostgresDocumentRepository"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_by_id = AsyncMock(return_value=None)
        response = await test_client.get(f"/api/v1/documents/{doc_id}/pdf")
        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_get_document_pdf_file_not_found_on_disk(
    test_client: AsyncClient,
) -> None:
    doc_id = uuid4()
    doc = Document(id=doc_id, filename="missing.pdf")
    with (
        patch(
            "app.infrastructure.adapters.inbound.http.document_router.PostgresDocumentRepository"
        ) as MockRepo,
        patch("os.path.exists", return_value=False),
    ):
        mock_repo = MockRepo.return_value
        mock_repo.get_by_id = AsyncMock(return_value=doc)
        response = await test_client.get(f"/api/v1/documents/{doc_id}/pdf")
        assert response.status_code == 404
        assert "PDF file not found on disk" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_document_invalid_uuid_fails(test_client: AsyncClient) -> None:
    response = await test_client.patch("/api/v1/documents/invalid-uuid", json={})
    assert response.status_code == 400
    assert "Invalid UUID format" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_document_not_found_fails(test_client: AsyncClient) -> None:
    doc_id = uuid4()
    with patch(
        "app.infrastructure.adapters.inbound.http.document_router.PostgresDocumentRepository"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_by_id = AsyncMock(return_value=None)
        response = await test_client.patch(f"/api/v1/documents/{doc_id}", json={})
        assert response.status_code == 404
        assert "Document not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_update_document_all_fields_success(test_client: AsyncClient) -> None:
    doc_id = uuid4()
    doc = Document(
        id=doc_id,
        filename="test.pdf",
        document_type="invoice",
        doc_date="2023-01-01",
        doc_number="123",
        vendor_name="Old",
        client_name="Old Employee",
        total_amount=100.0,
        tax_amount=10.0,
        extras={"existing": "data"},
    )

    with patch(
        "app.infrastructure.adapters.inbound.http.document_router.PostgresDocumentRepository"
    ) as MockRepo:
        mock_repo = MockRepo.return_value
        mock_repo.get_by_id = AsyncMock(return_value=doc)
        mock_repo.update = AsyncMock(return_value=doc)

        updates = {
            "document_type": "receipt",
            "doc_date": "2024-01-01",
            "doc_number": "456",
            "vendor_name": "New",
            "client_name": "New Employee",
            "total_amount": 200.0,
            "tax_amount": 20.0,
            "extras": {"existing": "data", "new_extra": "new_val"},
            "custom_field": "val",
        }

        response = await test_client.patch(f"/api/v1/documents/{doc_id}", json=updates)
        assert response.status_code == 200
        assert doc.document_type == "receipt"
        assert doc.doc_date == "2024-01-01"
        assert doc.doc_number == "456"
        assert doc.vendor_name == "New"
        assert doc.client_name == "New Employee"
        assert doc.total_amount == 200.0
        assert doc.tax_amount == 20.0
        assert doc.extras["existing"] == "data"
        assert doc.extras["new_extra"] == "new_val"
        assert doc.extras["custom_field"] == "val"
