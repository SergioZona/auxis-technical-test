"""
Domain model for a tax withholding certificate document.

Canonical schema keeps the 10 most query-critical structured columns.
Everything else (secondary financials, average income, etc.) lives in `extras` (JSONB).
Processing metadata (file_size, page_count, processing_time_ms) is tracked separately.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from .shared import Entity


@dataclass
class DocumentChunk(Entity):
    """A chunk of text from a document, used for vector embeddings (Qdrant)."""

    id: UUID = field(default_factory=uuid4)
    document_id: UUID = field(default_factory=uuid4)
    text: str = ""
    page_number: int | None = None
    embedding: list[float] | None = None
    chunk_index: int = 0


@dataclass
class Document(Entity):
    """
    Canonical domain model for an uploaded tax/income certificate document.

    ## Structured columns (query / filter targets)
    - form_type            – Document type code (\"220\", \"210\", \"invoice\"…)
    - tax_year             – Año gravable / fiscal year
    - nit_employer         – NIT of the issuing company
    - employer_name        – Razón social / company name
    - employee_document_id – Cédula / ID of the employee
    - employee_name        – Full name of the employee
    - period_start         – Start of certification period (YYYY-MM-DD)
    - period_end           – End of certification period (YYYY-MM-DD)
    - total_gross_income   – Total ingresos brutos (primary KPI)
    - income_tax_withheld  – Retención en la fuente (secondary KPI)

    ## Processing metadata
    - extraction_method    – \"text\" | \"ocr\" | \"hybrid\"
    - file_size_bytes      – Raw file size in bytes
    - page_count           – Number of pages in the PDF
    - processing_time_ms   – End-to-end parse time in milliseconds

    ## JSONB overflow
    - extras               – All secondary fields: sub-financials, location,
                             description, form_number, and anything the AI found.
    """

    id: UUID = field(default_factory=uuid4)
    filename: str = ""
    upload_date: datetime = field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    # ── 10 canonical columns ──────────────────────────────────────────────────
    form_type: str | None = None
    tax_year: int | None = None
    nit_employer: str | None = None
    employer_name: str | None = None
    employee_document_id: str | None = None
    employee_name: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    total_gross_income: float | None = None
    income_tax_withheld: float | None = None

    # ── Processing metadata ───────────────────────────────────────────────────
    extraction_method: str | None = None  # "text" | "ocr" | "hybrid"
    file_size_bytes: int | None = None
    page_count: int | None = None
    processing_time_ms: int | None = None

    # ── JSONB overflow ────────────────────────────────────────────────────────
    extras: dict[str, Any] = field(default_factory=dict)

    # ── Vector search chunks ──────────────────────────────────────────────────
    chunks: list[DocumentChunk] = field(default_factory=list)

    def add_chunk(self, chunk: DocumentChunk) -> None:
        self.chunks.append(chunk)

    def __setattr__(self, name: str, value: Any) -> None:
        canonical_fields = {
            "id",
            "filename",
            "upload_date",
            "form_type",
            "tax_year",
            "nit_employer",
            "employer_name",
            "employee_document_id",
            "employee_name",
            "period_start",
            "period_end",
            "total_gross_income",
            "income_tax_withheld",
            "extraction_method",
            "file_size_bytes",
            "page_count",
            "processing_time_ms",
            "extras",
            "chunks",
        }
        if name in canonical_fields or name.startswith("_"):
            super().__setattr__(name, value)
        else:
            if not hasattr(self, "extras") or self.extras is None:
                super().__setattr__("extras", {})
            self.extras[name] = value

    def __getattr__(self, name: str) -> Any:
        if (
            name != "extras"
            and hasattr(self, "extras")
            and self.extras
            and name in self.extras
        ):
            return self.extras[name]
        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{name}'"
        )
