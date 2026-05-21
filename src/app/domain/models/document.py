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
    Canonical domain model for an uploaded general invoice or business document.

    ## Structured columns (query / filter targets)
    - document_type        – E.g. "invoice", "receipt", "certificate"
    - doc_date             – YYYY-MM-DD
    - doc_number           – Invoice/receipt number
    - vendor_name          – Company/person issuing the document
    - client_name          – Company/person receiving the document
    - total_amount         – Grand total of the invoice
    - tax_amount           – Total tax amount applied

    ## Processing metadata
    - extraction_method    – "text" | "ocr" | "hybrid"
    - file_size_bytes      – Raw file size in bytes
    - page_count           – Number of pages in the PDF
    - processing_time_ms   – End-to-end parse time in milliseconds

    ## JSONB overflow and tables
    - tables               – Extracted structured tables (line items)
    - extras               – All dynamic / other fields extracted from the invoice
    """

    id: UUID = field(default_factory=uuid4)
    filename: str = ""
    upload_date: datetime = field(
        default_factory=lambda: datetime.now(UTC).replace(tzinfo=None)
    )

    # ── 7 canonical columns ───────────────────────────────────────────────────
    document_type: str | None = None
    doc_date: str | None = None
    doc_number: str | None = None
    vendor_name: str | None = None
    client_name: str | None = None
    total_amount: float | None = None
    tax_amount: float | None = None

    # ── Processing metadata ───────────────────────────────────────────────────
    extraction_method: str | None = None  # "text" | "ocr" | "hybrid"
    file_size_bytes: int | None = None
    page_count: int | None = None
    processing_time_ms: int | None = None

    # ── JSONB fields ──────────────────────────────────────────────────────────
    tables: list[dict[str, Any]] = field(default_factory=list)
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
            "document_type",
            "doc_date",
            "doc_number",
            "vendor_name",
            "client_name",
            "total_amount",
            "tax_amount",
            "extraction_method",
            "file_size_bytes",
            "page_count",
            "processing_time_ms",
            "tables",
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
