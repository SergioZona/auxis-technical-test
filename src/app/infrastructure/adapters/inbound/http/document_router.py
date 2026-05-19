import os
from typing import Annotated, Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.chat_rag_use_case import ChatRagUseCase
from app.application.use_cases.process_documents_use_case import ProcessDocumentsUseCase
from app.application.use_cases.query_database_use_case import QueryDatabaseUseCase
from app.domain.exceptions.document_errors import FileSizeLimitExceededError
from app.infrastructure.adapters.inbound.http.jsend import success
from app.infrastructure.adapters.outbound.persistence.database import get_db_session
from app.infrastructure.adapters.outbound.persistence.document_repository import (
    PostgresDocumentRepository,
)
from app.infrastructure.config.container import Container

router = APIRouter(tags=["documents"])


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    response: str
    sources: list[dict[str, Any]] = []


class DbQueryRequest(BaseModel):
    query: str


def _map_document_to_dict(doc: Any) -> dict[str, Any]:
    extras = doc.extras or {}
    return {
        "id": str(doc.id),
        "filename": doc.filename,
        "upload_date": doc.upload_date.isoformat() if doc.upload_date else None,
        "extraction_method": doc.extraction_method,
        "form_type": doc.form_type,
        "form_number": extras.get("form_number"),
        "tax_year": doc.tax_year,
        "nit_employer": doc.nit_employer,
        "employer_name": doc.employer_name,
        "employee_document_id": doc.employee_document_id,
        "employee_name": doc.employee_name,
        "location": extras.get("location"),
        "period_start": doc.period_start,
        "period_end": doc.period_end,
        "total_gross_income": doc.total_gross_income,
        "salary_payments": extras.get("salary_payments"),
        "social_benefits": extras.get("social_benefits"),
        "other_income_payments": extras.get("other_income_payments"),
        "health_contributions": extras.get("health_contributions"),
        "pension_contributions": extras.get("pension_contributions"),
        "average_monthly_income": extras.get("average_monthly_income"),
        "income_tax_withheld": doc.income_tax_withheld,
        "total_annual_withholding": extras.get("total_annual_withholding"),
        "chunks_processed": len(doc.chunks) if doc.chunks else 0,
        "others": extras,
    }


@router.post(
    "/documents/upload",
    responses={
        400: {"description": "Invalid file format"},
        413: {"description": "File size limit exceeded"},
        500: {"description": "Internal server error"},
    },
)
@inject
async def upload_documents(
    files: Annotated[list[UploadFile], File()],
    process_use_case: Annotated[
        ProcessDocumentsUseCase, Depends(Provide[Container.process_documents_use_case])
    ],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    """
    Upload multiple PDF documents for extraction.

    **Pipeline:**
    1. Validate file type (PDF) and size.
    2. Extract text via PyMuPDF. Falls back to OCR (pytesseract) if scanned.
    3. Map to canonical schema. Unknown fields go into `others`.
    4. Chunk text (500 chars, 50 overlap).
    5. Embed chunks using `BAAI/bge-small-en-v1.5` (Hugging Face via FastEmbed).
    6. Store metadata in Postgres and embeddings in Qdrant.
    """
    file_tuples = []

    # Ensure upload directory exists
    os.makedirs("data/uploads", exist_ok=True)

    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400, detail=f"File '{f.filename}' is not a PDF."
            )
        content = await f.read()
        file_tuples.append((f.filename, content))

        # Save to local disk for HITL viewing
        import asyncio

        def save_file(name: str, data: bytes) -> None:
            with open(f"data/uploads/{name}", "wb") as out_file:
                out_file.write(data)

        await asyncio.to_thread(save_file, f.filename or "unknown.pdf", content)

    repository = PostgresDocumentRepository(session)

    try:
        documents = await process_use_case.execute(file_tuples, repository)
    except FileSizeLimitExceededError as e:
        raise HTTPException(status_code=413, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    res = [_map_document_to_dict(doc) for doc in documents]
    return success(res)


@router.get("/documents")
async def list_documents(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    limit: int = 10,
    offset: int = 0,
) -> dict[str, Any]:
    """
    Retrieve stored canonical document metadata from Postgres.
    Supports pagination via `limit` and `offset` query parameters.
    """
    repository = PostgresDocumentRepository(session)
    docs = await repository.list_all(limit=limit, offset=offset)
    res = [_map_document_to_dict(doc) for doc in docs]
    return success(res)


@router.post(
    "/documents/chat",
    responses={
        500: {"description": "Internal server error"},
    },
)
@inject
async def chat_documents(
    request: ChatRequest,
    chat_use_case: Annotated[
        ChatRagUseCase, Depends(Provide[Container.chat_rag_use_case])
    ],
) -> dict[str, Any]:
    """
    Perform conversational RAG query over document chunks stored in Qdrant.
    """
    try:
        result = await chat_use_case.execute(request.question)
        return success(
            {"response": result.get("answer", ""), "sources": result.get("sources", [])}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/documents/query-db",
    responses={
        500: {"description": "Internal server error"},
    },
)
@inject
async def query_db(
    request: DbQueryRequest,
    query_use_case: Annotated[
        QueryDatabaseUseCase, Depends(Provide[Container.query_database_use_case])
    ],
) -> dict[str, Any]:
    """
    Query the structured document metadata table in Postgres using natural language.
    """
    try:
        answer = await query_use_case.execute(request.query)
        return success({"response": answer})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/documents/{document_id}/pdf",
    responses={
        400: {"description": "Invalid UUID format"},
        404: {"description": "Document or PDF not found"},
    },
)
async def get_document_pdf(
    document_id: str,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> FileResponse:
    from uuid import UUID

    repository = PostgresDocumentRepository(session)
    try:
        doc_uuid = UUID(document_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid UUID format") from e
    doc = await repository.get_by_id(doc_uuid)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = f"data/uploads/{doc.filename}"
    import os

    from fastapi.responses import FileResponse

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="PDF file not found on disk")

    return FileResponse(
        file_path, media_type="application/pdf", content_disposition_type="inline"
    )


@router.patch(
    "/documents/{document_id}",
    responses={
        400: {"description": "Invalid UUID format"},
        404: {"description": "Document not found"},
    },
)
async def update_document(
    document_id: str,
    updates: dict[str, Any],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> dict[str, Any]:
    from uuid import UUID

    repository = PostgresDocumentRepository(session)
    try:
        doc_uuid = UUID(document_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid UUID format") from e
    doc = await repository.get_by_id(doc_uuid)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Apply updates
    if "form_type" in updates:
        doc.form_type = updates["form_type"]
    if "tax_year" in updates:
        doc.tax_year = updates["tax_year"]
    if "nit_employer" in updates:
        doc.nit_employer = updates["nit_employer"]
    if "employer_name" in updates:
        doc.employer_name = updates["employer_name"]
    if "employee_name" in updates:
        doc.employee_name = updates["employee_name"]
    if "total_gross_income" in updates:
        doc.total_gross_income = updates["total_gross_income"]
    if "income_tax_withheld" in updates:
        doc.income_tax_withheld = updates["income_tax_withheld"]

    # Update extras
    if not doc.extras:
        doc.extras = {}
    for key in [
        "form_number",
        "employee_document_id",
        "location",
        "salary_payments",
        "social_benefits",
        "other_income_payments",
        "health_contributions",
        "pension_contributions",
        "average_monthly_income",
        "total_annual_withholding",
    ]:
        if key in updates:
            doc.extras[key] = updates[key]

    await repository.update(doc)
    return success({"message": "Document updated successfully"})
