"""
PDF Document Parser — stateful LangGraph processing pipeline.

Orchestrated via LangGraph:
  1. classify: Page-by-page classification (text, scanned, mixed) using PyMuPDF and heuristics.
  2. extract: Custom page-specific extraction (PyMuPDF text/tables, Multimodal LLM, OCR fallback).
  3. reconcile: Metadata consolidation across pages using sequential form layout parsers, regex heuristics, and document-level AI fallback.
  4. chunk: Smart chunking splitting at page and paragraph boundaries.
  5. assemble: Canonical Document entity generation.
"""

import contextvars
import logging
import re
from typing import Any, TypedDict

import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, StateGraph
from langsmith import traceable

from app.application.ports.outbound.ai_extractor_port import AiExtractorPort
from app.application.ports.outbound.document_parser_port import DocumentParserPort
from app.domain.exceptions.document_errors import ExtractionFailedError
from app.domain.models.document import Document, DocumentChunk

_current_file_content_var = contextvars.ContextVar(
    "_current_file_content_var", default=b""
)

logger = logging.getLogger(__name__)

# Threshold: if extracted text is shorter than this, assume scanned PDF → OCR
_OCR_FALLBACK_THRESHOLD = 100


def _parse_amount(raw: str) -> float | None:
    """Convert Colombian-formatted number strings to float. e.g. '$72.221.000' → 72221000.0"""
    if not raw:
        return None
    cleaned = re.sub(r"[$\s]", "", raw).replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


class ParserState(TypedDict):
    file_content: bytes
    filename: str
    pages: list[dict[str, Any]]
    full_text: str
    reconciled_metadata: dict[str, Any]
    reconciled_extras: dict[str, Any]
    chunks: list[DocumentChunk]
    document: Document | None


class PyMuPDFDocumentParser(DocumentParserPort):
    """
    Multi-strategy PDF parser.
    Orchestrated via LangGraph.
    """

    def __init__(self, ai_extractor: AiExtractorPort):
        self._ai_extractor = ai_extractor

        # Build LangGraph workflow
        builder = StateGraph(ParserState)
        builder.add_node("classify", self._classify_pages_node)
        builder.add_node("extract", self._extract_page_content_node)
        builder.add_node("reconcile", self._reconcile_metadata_node)
        builder.add_node("chunk", self._generate_chunks_node)
        builder.add_node("assemble", self._assemble_document_node)

        builder.set_entry_point("classify")
        builder.add_edge("classify", "extract")
        builder.add_edge("extract", "reconcile")
        builder.add_edge("reconcile", "chunk")
        builder.add_edge("chunk", "assemble")
        builder.add_edge("assemble", END)

        self._graph = builder.compile()

    @traceable(name="parse_document")
    async def parse(self, file_content: bytes, filename: str) -> Document:
        token = _current_file_content_var.set(file_content)
        try:
            initial_state: ParserState = {
                "file_content": b"",  # Keep empty to avoid trace bloat and media upload errors
                "filename": filename,
                "pages": [],
                "full_text": "",
                "reconciled_metadata": {},
                "reconciled_extras": {},
                "chunks": [],
                "document": None,
            }

            result = await self._graph.ainvoke(initial_state)
        finally:
            _current_file_content_var.reset(token)

        if not result:
            raise ExtractionFailedError(f"LangGraph parsing failed for {filename}")
        doc = result.get("document")
        if not isinstance(doc, Document):
            raise ExtractionFailedError(f"LangGraph parsing failed for {filename}")
        return doc

    # ── LangGraph Nodes ────────────────────────────────────────────────────

    def _classify_pages_node(self, state: ParserState) -> dict[str, Any]:
        file_content = _current_file_content_var.get()
        pdf = fitz.open(stream=file_content, filetype="pdf")
        pages = []
        for n in range(len(pdf)):
            page_num = n + 1
            page = pdf.load_page(n)
            selectable_text = page.get_text()

            has_images = len(page.get_images()) > 0
            has_drawings = len(page.get_drawings()) > 10

            # Skip completely empty pages
            if (
                not selectable_text.strip()
                and not has_images
                and len(page.get_drawings()) == 0
            ):
                logger.info(f"Page {page_num} is completely empty. Skipping.")
                continue

            if len(selectable_text.strip()) < _OCR_FALLBACK_THRESHOLD:
                classification = "scanned"
            elif has_images or has_drawings:
                classification = "mixed"
            else:
                classification = "text"

            pages.append(
                {
                    "page_number": page_num,
                    "selectable_text": selectable_text,
                    "has_images": has_images,
                    "has_drawings": has_drawings,
                    "classification": classification,
                    "extracted_text": "",
                    "tables_text": "",
                    "ai_data": {},
                }
            )
        pdf.close()
        return {"pages": pages}

    def _extract_tables_md(self, page: fitz.Page, page_num: int) -> str:
        tables_text = ""
        try:
            tabs = page.find_tables()
            for t in tabs:
                df_md = t.to_markdown()
                if df_md:
                    tables_text += "\n" + df_md + "\n"
        except Exception as e:
            logger.warning(f"PyMuPDF find_tables failed on page {page_num}: {e}")
        return tables_text

    async def _process_scanned_page(
        self, page_num: int, filename: str, png_bytes: bytes
    ) -> tuple[dict[str, Any], str]:
        logger.info(
            f"{filename}: Page {page_num} → scanned. Running AI Visual Analysis."
        )
        ai_data = await self._ai_extractor.extract_metadata(
            text=None,
            image_bytes=png_bytes,
            filename=filename,
        )
        desc = ai_data.get("description", "")
        extracted_text = ""
        if desc:
            extracted_text = f"[AI Visual Analysis]:\n{desc}"
        return ai_data, extracted_text

    async def _process_mixed_page(
        self,
        page_num: int,
        filename: str,
        selectable_text: str,
        png_bytes: bytes,
    ) -> tuple[dict[str, Any], str]:
        logger.info(f"{filename}: Page {page_num} → mixed. Running AI Visual Analysis.")
        ai_data = await self._ai_extractor.extract_metadata(
            text=selectable_text,
            image_bytes=png_bytes,
            filename=filename,
        )
        desc = ai_data.get("description", "")
        extracted_text = selectable_text
        if desc:
            extracted_text += f"\n\n[AI Visual Analysis]:\n{desc}"
        return ai_data, extracted_text

    async def _process_page(
        self, page: fitz.Page, p_info: dict[str, Any], filename: str
    ) -> tuple[str, str, dict[str, Any]]:
        page_num = p_info["page_number"]
        selectable_text = p_info["selectable_text"]
        classification = p_info["classification"]

        tables_text = self._extract_tables_md(page, page_num)
        ai_data: dict[str, Any] = {}
        extracted_text = ""

        if classification in ("scanned", "mixed"):
            pix = page.get_pixmap(dpi=200)
            png_bytes = pix.tobytes("png")

            if classification == "scanned":
                ai_data, extracted_text = await self._process_scanned_page(
                    page_num, filename, png_bytes
                )
            else:
                ai_data, extracted_text = await self._process_mixed_page(
                    page_num, filename, selectable_text, png_bytes
                )
        else:
            extracted_text = selectable_text

        if tables_text:
            extracted_text += f"\n\n[Extracted Tables]:\n{tables_text}"

        return extracted_text, tables_text, ai_data

    async def _extract_page_content_node(self, state: ParserState) -> dict[str, Any]:
        file_content = _current_file_content_var.get()
        pdf = fitz.open(stream=file_content, filetype="pdf")
        pages = list(state["pages"])
        full_text = ""

        for idx, p_info in enumerate(pages):
            page = pdf.load_page(p_info["page_number"] - 1)
            extracted_text, tables_text, ai_data = await self._process_page(
                page, p_info, state["filename"]
            )
            pages[idx] = {
                **p_info,
                "extracted_text": extracted_text,
                "tables_text": tables_text,
                "ai_data": ai_data,
                "ocr_text": "",
            }
            full_text += extracted_text + "\n"

        pdf.close()
        return {"pages": pages, "full_text": full_text}

    async def _reconcile_step_ai_doc(
        self, full_text: str, filename: str, reconciled: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        logger.info(f"'{filename}': Running document-level AI extraction (primary).")
        ai_result = await self._ai_extractor.extract_metadata(
            text=full_text, filename=filename
        )
        extras: dict[str, Any] = {}
        if ai_result:
            for k in reconciled:
                if k in ai_result:
                    reconciled[k] = ai_result[k]
            extras = ai_result.get("extras") or {}
        return reconciled, extras

    def _reconcile_step_ai_pages(
        self,
        pages: list[dict[str, Any]],
        reconciled: dict[str, Any],
        extras: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        for p in pages:
            ai_val = p.get("ai_data") or {}
            for k in reconciled:
                if k == "tables":
                    if reconciled["tables"] is None:
                        reconciled["tables"] = []
                    if "tables" in ai_val and isinstance(ai_val["tables"], list):
                        reconciled["tables"].extend(ai_val["tables"])
                else:
                    if reconciled[k] is None and k in ai_val:
                        reconciled[k] = ai_val[k]

            page_extras = ai_val.get("extras") or {}
            for k, v in page_extras.items():
                if v is not None and extras.get(k) is None:
                    extras[k] = v
        return reconciled, extras

    async def _reconcile_metadata_node(self, state: ParserState) -> dict[str, Any]:
        filename = state["filename"]
        full_text = state["full_text"]
        pages = state["pages"]

        # Track the 7 canonical fields + tables explicitly. Everything else goes into extras.
        reconciled: dict[str, Any] = {
            "document_type": None,
            "doc_date": None,
            "doc_number": None,
            "vendor_name": None,
            "client_name": None,
            "total_amount": None,
            "tax_amount": None,
            "tables": None,
        }

        reconciled, extras = await self._reconcile_step_ai_doc(
            full_text, filename, reconciled
        )
        reconciled, extras = self._reconcile_step_ai_pages(pages, reconciled, extras)

        # Default tables to list if not set
        if reconciled.get("tables") is None:
            reconciled["tables"] = []

        return {"reconciled_metadata": reconciled, "reconciled_extras": extras}

    def _generate_chunks_node(self, state: ParserState) -> dict[str, Any]:
        chunks = []
        chunk_idx = 0
        for p in state["pages"]:
            page_chunks = self._smart_chunk_page(p["page_number"], p["extracted_text"])
            for c in page_chunks:
                c.chunk_index = chunk_idx
                chunks.append(c)
                chunk_idx += 1
        return {"chunks": chunks}

    def _assemble_document_node(self, state: ParserState) -> dict[str, Any]:
        filename = state["filename"]
        reconciled = state["reconciled_metadata"]
        extras = state["reconciled_extras"]
        chunks = state["chunks"]
        pages = state["pages"]

        has_scanned = any(p["classification"] == "scanned" for p in pages)
        extraction_method = "ocr" if has_scanned else "text"
        if not has_scanned and any(p["classification"] == "mixed" for p in pages):
            extraction_method = "hybrid"

        doc = Document(filename=filename, extraction_method=extraction_method)

        for k, v in reconciled.items():
            setattr(doc, k, v)

        for c in chunks:
            doc.add_chunk(c)

        doc.extras = extras
        doc.extras["raw_text_preview"] = state["full_text"][:300].strip()
        doc.page_count = len(pages)

        return {"document": doc}

    # ── Helpers ────────────────────────────────────────────────────────────

    def _smart_chunk_page(
        self,
        page_number: int,
        text: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ) -> list[DocumentChunk]:
        """Split page text using LangChain's RecursiveCharacterTextSplitter."""
        if not text.strip():
            return []

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ".", " ", ""],
        )

        raw_chunks = splitter.split_text(text)

        chunks = []
        for i, chunk_text in enumerate(raw_chunks):
            chunks.append(
                DocumentChunk(
                    text=chunk_text,
                    page_number=page_number,
                    chunk_index=i,
                )
            )
        return chunks
