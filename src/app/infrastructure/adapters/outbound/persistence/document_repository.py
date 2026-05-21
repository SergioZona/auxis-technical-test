from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, Float, Integer, String, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.application.ports.outbound.document_repository_port import (
    DocumentRepositoryPort,
)
from app.domain.models.document import Document
from app.infrastructure.adapters.outbound.persistence.database import Base


class DocumentModel(Base):
    """
    SQLAlchemy ORM for the `documents` table.
    7 canonical queryable columns + processing metadata + JSONB tables + JSONB extras.
    """

    __tablename__ = "documents"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    upload_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    # ── 7 canonical columns ───────────────────────────────────────────────────
    document_type: Mapped[str | None] = mapped_column(String, nullable=True)
    doc_date: Mapped[str | None] = mapped_column(String, nullable=True)
    doc_number: Mapped[str | None] = mapped_column(String, nullable=True)
    vendor_name: Mapped[str | None] = mapped_column(String, nullable=True)
    client_name: Mapped[str | None] = mapped_column(String, nullable=True)
    total_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    tax_amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Processing metadata ───────────────────────────────────────────────────
    extraction_method: Mapped[str | None] = mapped_column(String, nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    processing_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ── JSONB columns ─────────────────────────────────────────────────────────
    tables: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    extras: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)


def _model_to_domain(m: DocumentModel) -> Document:
    return Document(
        id=m.id,
        filename=m.filename,
        upload_date=m.upload_date,
        document_type=m.document_type,
        doc_date=m.doc_date,
        doc_number=m.doc_number,
        vendor_name=m.vendor_name,
        client_name=m.client_name,
        total_amount=m.total_amount,
        tax_amount=m.tax_amount,
        extraction_method=m.extraction_method,
        file_size_bytes=m.file_size_bytes,
        page_count=m.page_count,
        processing_time_ms=m.processing_time_ms,
        tables=m.tables or [],
        extras=m.extras or {},
    )


class PostgresDocumentRepository(DocumentRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, document: Document) -> Document:
        upload_date = document.upload_date
        if upload_date and upload_date.tzinfo is not None:
            upload_date = upload_date.replace(tzinfo=None)

        model = DocumentModel(
            id=document.id,
            filename=document.filename,
            upload_date=upload_date,
            document_type=document.document_type,
            doc_date=document.doc_date,
            doc_number=document.doc_number,
            vendor_name=document.vendor_name,
            client_name=document.client_name,
            total_amount=document.total_amount,
            tax_amount=document.tax_amount,
            extraction_method=document.extraction_method,
            file_size_bytes=document.file_size_bytes,
            page_count=document.page_count,
            processing_time_ms=document.processing_time_ms,
            tables=document.tables,
            extras=document.extras,
        )
        self._session.add(model)
        await self._session.commit()
        return document

    async def get_by_id(self, document_id: UUID) -> Document | None:
        result = await self._session.execute(
            select(DocumentModel).where(DocumentModel.id == document_id)
        )
        model = result.scalar_one_or_none()
        return _model_to_domain(model) if model else None

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Document]:
        result = await self._session.execute(
            select(DocumentModel)
            .order_by(DocumentModel.upload_date.desc())
            .offset(offset)
            .limit(limit)
        )
        return [_model_to_domain(m) for m in result.scalars().all()]

    async def update(self, document: Document) -> Document:
        result = await self._session.execute(
            select(DocumentModel).where(DocumentModel.id == document.id)
        )
        model = result.scalar_one_or_none()
        if model:
            model.document_type = document.document_type
            model.doc_date = document.doc_date
            model.doc_number = document.doc_number
            model.vendor_name = document.vendor_name
            model.client_name = document.client_name
            model.total_amount = document.total_amount
            model.tax_amount = document.tax_amount
            model.tables = document.tables
            model.extras = document.extras
            await self._session.commit()
        return document
