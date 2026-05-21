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
                reconciled[k] = ai_result.get(k)
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
                if reconciled[k] is None and k in ai_val:
                    reconciled[k] = ai_val[k]

            page_extras = ai_val.get("extras") or {}
            for k, v in page_extras.items():
                if v is not None and extras.get(k) is None:
                    extras[k] = v
        return reconciled, extras

    def _apply_form_220_pos_mapping(
        self,
        full_text: str,
        filename: str,
        reconciled: dict[str, Any],
        extras: dict[str, Any],
    ) -> None:
        temp_doc = Document(filename=filename)
        temp_doc.form_type = "220"
        try:
            self._map_form_220(full_text, temp_doc)
            for k in reconciled:
                if reconciled[k] is None:
                    val = getattr(temp_doc, k, None)
                    if val is not None:
                        reconciled[k] = val

            # Merge temp_doc extras if any
            for k, v in temp_doc.extras.items():
                if v is not None and extras.get(k) is None:
                    extras[k] = v
        except Exception as exc:
            logger.warning(f"Form 220 positional mapping failed: {exc}")

    def _reconcile_step_form_220(
        self,
        full_text: str,
        filename: str,
        reconciled: dict[str, Any],
        extras: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        is_form_220 = (
            "certificado de ingresos y retenciones" in full_text.lower()
            or "form 220" in full_text.lower()
            or reconciled.get("form_type") == "220"
        )
        if not is_form_220:
            return reconciled, extras

        if not reconciled.get("form_type"):
            reconciled["form_type"] = "220"

        if reconciled.get("total_gross_income") is None:
            self._apply_form_220_pos_mapping(full_text, filename, reconciled, extras)

        return reconciled, extras

    async def _reconcile_metadata_node(self, state: ParserState) -> dict[str, Any]:
        filename = state["filename"]
        full_text = state["full_text"]
        pages = state["pages"]

        # Track the 10 canonical fields explicitly. Everything else goes into extras.
        reconciled: dict[str, Any] = {
            "form_type": None,
            "tax_year": None,
            "nit_employer": None,
            "employer_name": None,
            "employee_document_id": None,
            "employee_name": None,
            "period_start": None,
            "period_end": None,
            "total_gross_income": None,
            "income_tax_withheld": None,
        }

        reconciled, extras = await self._reconcile_step_ai_doc(
            full_text, filename, reconciled
        )
        reconciled, extras = self._reconcile_step_ai_pages(pages, reconciled, extras)
        reconciled, extras = self._reconcile_step_form_220(
            full_text, filename, reconciled, extras
        )
        reconciled, extras = self._apply_regex_fallbacks(full_text, reconciled, extras)

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

    def _fallback_form_info(
        self, text: str, res: dict[str, Any], ext: dict[str, Any]
    ) -> None:
        if not ext.get("form_number"):
            m = re.search(
                r"(?:Número de formulario|No\.?\s*formulario)[:\s]*(\d+)",
                text,
                re.IGNORECASE,
            )
            if m:
                ext["form_number"] = m.group(1).strip()

        if not res.get("form_type"):
            m = re.search(r"\b(220|210|2516|110)\b", text)
            if m:
                res["form_type"] = m.group(1)

        if not res.get("tax_year"):
            m = re.search(
                r"(?:Año gravable|gravable)[:\s]*(\d{4})", text, re.IGNORECASE
            )
            if m:
                res["tax_year"] = int(m.group(1))

    def _fallback_employer_info(self, text: str, res: dict[str, Any]) -> None:
        if not res.get("employer_name"):
            m = re.search(
                r"(?:Razón social|Razon social)[:\s]+([^\n]+)",
                text,
                re.IGNORECASE,
            )
            if m:
                name_candidate = m.group(1)
                nit_split = re.split(r"\bNIT\b", name_candidate, flags=re.IGNORECASE)
                res["employer_name"] = nit_split[0].strip()

        if not res.get("nit_employer"):
            m = re.search(r"(?:NIT|N\.I\.T\.)[:\s]*([\d.-]+)", text, re.IGNORECASE)
            if m:
                res["nit_employer"] = m.group(1).strip()

    def _fallback_employee_id(self, text: str, res: dict[str, Any]) -> None:
        if not res.get("employee_document_id"):
            m = re.search(
                r"(?:Número de identificación|No.*identificacion)[:\s]*([\d.]+)",
                text,
                re.IGNORECASE,
            )
            if m:
                res["employee_document_id"] = m.group(1).strip()

    def _fallback_identifiers(
        self, text: str, res: dict[str, Any], ext: dict[str, Any]
    ) -> None:
        self._fallback_form_info(text, res, ext)
        self._fallback_employer_info(text, res)
        self._fallback_employee_id(text, res)

    def _fallback_employee(self, text: str, res: dict[str, Any]) -> None:
        if not res.get("employee_name"):
            first_surname = None
            second_surname = None
            first_name = None

            m1 = re.search(r"Primer apellido[:\s]*(\w+)", text, re.IGNORECASE)
            if m1:
                first_surname = m1.group(1)

            m2 = re.search(r"Segundo apellido[:\s]*(\w+)", text, re.IGNORECASE)
            if m2:
                second_surname = m2.group(1)

            m3 = re.search(r"Primer nombre[:\s]*(\w+)", text, re.IGNORECASE)
            if m3:
                first_name = m3.group(1)

            parts = []
            if first_name:
                parts.append(first_name)
            if first_surname:
                parts.append(first_surname)
            if second_surname:
                parts.append(second_surname)

            if parts:
                res["employee_name"] = " ".join(parts)

    def _fallback_location(self, text: str) -> str | None:
        target_cities = {
            "bogota",
            "bogotá",
            "medellin",
            "medellín",
            "cali",
            "barranquilla",
            "cartagena",
        }
        words = re.findall(r"\b[a-zA-ZÁÉÍÓÚáéíóú]+\b", text.strip())
        if words:
            last_word = words[-1]
            if last_word.lower() in target_cities or (
                last_word.isupper() and len(last_word) >= 4
            ):
                return str(last_word)
        return None

    def _fallback_location_dates(
        self, text: str, res: dict[str, Any], ext: dict[str, Any]
    ) -> None:
        if not ext.get("location"):
            loc = self._fallback_location(text)
            if loc:
                ext["location"] = loc

        dates = re.findall(r"\d{4}[-/]\d{2}[-/]\d{2}", text)
        if len(dates) > 0 and not res.get("period_start"):
            res["period_start"] = dates[0]
        if len(dates) > 1 and not res.get("period_end"):
            res["period_end"] = dates[1]

    def _fallback_amounts(
        self, text: str, res: dict[str, Any], ext: dict[str, Any]
    ) -> None:
        def _find_amount(label: str) -> float | None:
            pattern = rf"{label}[^\n]*?(\$?[\d]{{1,3}}(?:\.[\d]{{3}})*(?:,\d{{2}})?)"
            m = re.search(pattern, text, re.IGNORECASE)
            return _parse_amount(m.group(1)) if m else None

        for k, label in [
            ("total_gross_income", r"Total\s+ingresos\s+brutos"),
            (
                "income_tax_withheld",
                r"Valor\s+de\s+la\s+retenci[oó]n\s+en\s+la\s+fuente",
            ),
        ]:
            if res.get(k) is None:
                res[k] = _find_amount(label)

        for k, label in [
            ("salary_payments", r"Pagos\s+por\s+salarios"),
            ("social_benefits", r"Pagos\s+por\s+prestaciones\s+sociales"),
            ("other_income_payments", r"Otros\s+pagos"),
            ("health_contributions", r"Aportes\s+obligatorios\s+por\s+salud"),
            (
                "pension_contributions",
                r"Aportes\s+obligatorios\s+a\s+fondos\s+de\s+pensiones",
            ),
            ("average_monthly_income", r"Ingreso\s+laboral\s+promedio"),
            ("total_annual_withholding", r"Total\s+retenci[oó]n\s+a[ñn]o\s+gravable"),
        ]:
            if ext.get(k) is None:
                ext[k] = _find_amount(label)

    def _apply_regex_fallbacks(
        self, text: str, reconciled: dict[str, Any], extras: dict[str, Any]
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        res = dict(reconciled)
        ext = dict(extras)

        self._fallback_identifiers(text, res, ext)
        self._fallback_employee(text, res)
        self._fallback_location_dates(text, res, ext)
        self._fallback_amounts(text, res, ext)

        return res, ext

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

    def _clean_form_220_lines(self, text: str) -> list[str]:
        lines = []
        for line in text.split("\n"):
            line_str = line.strip()
            if not line_str:
                continue
            if re.match(r"^[\d\s]+$", line_str):
                collapsed = re.sub(r"\s+", "", line_str)
                if collapsed:
                    lines.append(collapsed)
            else:
                lines.append(line_str)
        return lines

    def _parse_form_220_tax_year(self, lines: list[str]) -> int | None:
        for line in lines:
            m = re.search(
                r"(?:Año gravable|gravable)[:\s]*(\d{4})", line, re.IGNORECASE
            )
            if m:
                return int(m.group(1))
        return None

    def _skip_ano_gravable(self, sub: list[str], idx: int) -> int:
        while idx < len(sub) and (
            "año gravable" in sub[idx].lower() or "ano gravable" in sub[idx].lower()
        ):
            idx += 1
        return idx

    def _parse_single_digit_field(
        self, sub: list[str], idx: int
    ) -> tuple[int, str | None]:
        if idx < len(sub) and sub[idx].isdigit():
            return idx + 1, sub[idx]
        return idx, None

    def _parse_field_nit(self, sub: list[str], idx: int) -> tuple[int, str | None]:
        nit_val = None
        if idx < len(sub) and sub[idx].isdigit():
            nit_val = sub[idx]
            idx += 1

        dv_val = None
        if idx < len(sub) and sub[idx].isdigit():
            dv_val = sub[idx]
            idx += 1

        if nit_val and dv_val:
            return idx, f"{nit_val}-{dv_val}"
        return idx, nit_val

    def _parse_field_employer_name(
        self, sub: list[str], idx: int
    ) -> tuple[int, str | None]:
        if idx < len(sub) and not sub[idx].isdigit():
            return idx + 1, sub[idx]
        return idx, None

    def _skip_unwanted_digit(self, sub: list[str], idx: int) -> int:
        if idx < len(sub) and sub[idx].isdigit():
            return idx + 1
        return idx

    def _parse_field_employee_name(
        self, sub: list[str], idx: int
    ) -> tuple[int, str | None]:
        name_parts = []
        while idx < len(sub):
            val = sub[idx]
            if val.isdigit():
                break
            name_parts.append(val)
            idx += 1

        if len(name_parts) >= 3:
            lasts = name_parts[:2]
            firsts = name_parts[2:]
            return idx, " ".join(firsts + lasts)
        if name_parts:
            return idx, " ".join(name_parts)
        return idx, None

    def _parse_field_dates(
        self, sub: list[str], idx: int
    ) -> tuple[int, str | None, str | None]:
        date_ints: list[str] = []
        while idx < len(sub) and len(date_ints) < 9:
            if sub[idx].isdigit() and len(sub[idx]) <= 4:
                date_ints.append(sub[idx])
            idx += 1

        if len(date_ints) >= 6:
            p_start = f"{date_ints[0]}-{date_ints[1].zfill(2)}-{date_ints[2].zfill(2)}"
            p_end = f"{date_ints[3]}-{date_ints[4].zfill(2)}-{date_ints[5].zfill(2)}"
            return idx, p_start, p_end
        return idx, None, None

    def _parse_field_location(self, sub: list[str], idx: int) -> str | None:
        if idx < len(sub) and not sub[idx].startswith("$") and not sub[idx].isdigit():
            return sub[idx]
        return None

    def _parse_form_220_header_fields(self, sub: list[str]) -> dict[str, Any]:
        res: dict[str, Any] = {}
        idx = self._skip_ano_gravable(sub, 0)
        idx, res["form_number"] = self._parse_single_digit_field(sub, idx)
        idx, res["nit_employer"] = self._parse_field_nit(sub, idx)
        idx, res["employer_name"] = self._parse_field_employer_name(sub, idx)
        idx = self._skip_unwanted_digit(sub, idx)
        idx, res["employee_document_id"] = self._parse_single_digit_field(sub, idx)
        idx, res["employee_name"] = self._parse_field_employee_name(sub, idx)
        idx, res["period_start"], res["period_end"] = self._parse_field_dates(sub, idx)
        res["location"] = self._parse_field_location(sub, idx)

        # Cleanup None values
        return {k: v for k, v in res.items() if v is not None}

    def _apply_form_220_amounts(self, sub: list[str], doc: Document) -> None:
        amounts = []
        for line_val in sub:
            if line_val.startswith("$"):
                amt = _parse_amount(line_val)
                if amt is not None:
                    amounts.append(amt)

        if len(amounts) >= 27:
            doc.salary_payments = amounts[0]
            doc.social_benefits = amounts[6]
            doc.other_income_payments = amounts[10]
            doc.total_gross_income = amounts[16]
            doc.health_contributions = amounts[17]
            doc.pension_contributions = amounts[18]
            doc.average_monthly_income = amounts[23]
            doc.income_tax_withheld = amounts[24]
            doc.total_annual_withholding = amounts[26]

    def _find_header_index(self, lines: list[str]) -> int:
        for i, line in enumerate(lines):
            if "certificado de ingresos y retenciones" in line.lower():
                return i
        return -1

    def _apply_header_and_amounts(self, sub: list[str], doc: Document) -> None:
        header_fields = self._parse_form_220_header_fields(sub)
        fields = [
            "form_number",
            "nit_employer",
            "employer_name",
            "employee_document_id",
            "employee_name",
            "period_start",
            "period_end",
            "location",
        ]
        for field in fields:
            if field in header_fields:
                setattr(doc, field, header_fields[field])
        self._apply_form_220_amounts(sub, doc)

    def _map_form_220(self, text: str, doc: Document) -> None:
        """Sequential line-by-line parser for Form 220."""
        lines = self._clean_form_220_lines(text)
        tax_year = self._parse_form_220_tax_year(lines)
        if tax_year:
            doc.tax_year = tax_year

        header_idx = self._find_header_index(lines)
        if header_idx != -1:
            self._apply_header_and_amounts(lines[header_idx + 1 :], doc)
