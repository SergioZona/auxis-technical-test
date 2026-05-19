from typing import List, Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, Float, Integer, String, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.outbound.document_repository_port import DocumentRepositoryPort
from app.domain.models.document import Document
from app.infrastructure.adapters.outbound.persistence.database import Base


class DocumentModel(Base):
    """
    SQLAlchemy ORM for the `documents` table.
    10 canonical queryable columns + processing metadata + JSONB extras.
    """

    __tablename__ = "documents"

    # ── Primary key ───────────────────────────────────────────────────────────
    id = Column(PGUUID(as_uuid=True), primary_key=True)
    filename = Column(String, nullable=False)
    upload_date = Column(DateTime, nullable=False, server_default=func.now())

    # ── 10 canonical columns ──────────────────────────────────────────────────
    form_type = Column(String, nullable=True)
    tax_year = Column(Integer, nullable=True)
    nit_employer = Column(String, nullable=True)
    employer_name = Column(String, nullable=True)
    employee_document_id = Column(String, nullable=True)
    employee_name = Column(String, nullable=True)
    period_start = Column(String, nullable=True)
    period_end = Column(String, nullable=True)
    total_gross_income = Column(Float, nullable=True)
    income_tax_withheld = Column(Float, nullable=True)

    # ── Processing metadata ───────────────────────────────────────────────────
    extraction_method = Column(String, nullable=True)   # "text" | "ocr" | "hybrid"
    file_size_bytes = Column(Integer, nullable=True)
    page_count = Column(Integer, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)

    # ── JSONB overflow (secondary fields + description + anything else) ───────
    extras = Column(JSONB, nullable=False, default={})


def _model_to_domain(m: DocumentModel) -> Document:
    return Document(
        id=m.id,
        filename=m.filename,
        upload_date=m.upload_date,
        form_type=m.form_type,
        tax_year=m.tax_year,
        nit_employer=m.nit_employer,
        employer_name=m.employer_name,
        employee_document_id=m.employee_document_id,
        employee_name=m.employee_name,
        period_start=m.period_start,
        period_end=m.period_end,
        total_gross_income=m.total_gross_income,
        income_tax_withheld=m.income_tax_withheld,
        extraction_method=m.extraction_method,
        file_size_bytes=m.file_size_bytes,
        page_count=m.page_count,
        processing_time_ms=m.processing_time_ms,
        extras=m.extras or {},
    )


class PostgresDocumentRepository(DocumentRepositoryPort):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def save(self, document: Document) -> Document:
        model = DocumentModel(
            id=document.id,
            filename=document.filename,
            upload_date=document.upload_date,
            form_type=document.form_type,
            tax_year=document.tax_year,
            nit_employer=document.nit_employer,
            employer_name=document.employer_name,
            employee_document_id=document.employee_document_id,
            employee_name=document.employee_name,
            period_start=document.period_start,
            period_end=document.period_end,
            total_gross_income=document.total_gross_income,
            income_tax_withheld=document.income_tax_withheld,
            extraction_method=document.extraction_method,
            file_size_bytes=document.file_size_bytes,
            page_count=document.page_count,
            processing_time_ms=document.processing_time_ms,
            extras=document.extras,
        )
        self._session.add(model)
        await self._session.commit()
        return document

    async def get_by_id(self, document_id: UUID) -> Optional[Document]:
        result = await self._session.execute(
            select(DocumentModel).where(DocumentModel.id == document_id)
        )
        model = result.scalar_one_or_none()
        return _model_to_domain(model) if model else None

    async def list_all(self, limit: int = 100, offset: int = 0) -> List[Document]:
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
            model.form_type = document.form_type
            model.tax_year = document.tax_year
            model.nit_employer = document.nit_employer
            model.employer_name = document.employer_name
            model.employee_document_id = document.employee_document_id
            model.employee_name = document.employee_name
            model.period_start = document.period_start
            model.period_end = document.period_end
            model.total_gross_income = document.total_gross_income
            model.income_tax_withheld = document.income_tax_withheld
            model.extras = document.extras
            await self._session.commit()
        return document
