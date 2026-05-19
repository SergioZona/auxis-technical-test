"""
PDF Document Parser — stateful LangGraph processing pipeline.

Orchestrated via LangGraph:
  1. classify: Page-by-page classification (text, scanned, mixed) using PyMuPDF and heuristics.
  2. extract: Custom page-specific extraction (PyMuPDF text/tables, Multimodal LLM, OCR fallback).
  3. reconcile: Metadata consolidation across pages using sequential form layout parsers, regex heuristics, and document-level AI fallback.
  4. chunk: Smart chunking splitting at page and paragraph boundaries.
  5. assemble: Canonical Document entity generation.
"""

import io
import logging
import re
from typing import Any, TypedDict

import fitz  # PyMuPDF
import pytesseract
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import END, StateGraph
from PIL import Image

from app.application.ports.outbound.ai_extractor_port import AiExtractorPort
from app.application.ports.outbound.document_parser_port import DocumentParserPort
from app.domain.exceptions.document_errors import ExtractionFailedError
from app.domain.models.document import Document, DocumentChunk

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

    async def parse(self, file_content: bytes, filename: str) -> Document:
        initial_state: ParserState = {
            "file_content": file_content,
            "filename": filename,
            "pages": [],
            "full_text": "",
            "reconciled_metadata": {},
            "reconciled_extras": {},
            "chunks": [],
            "document": None,
        }

        result = await self._graph.ainvoke(initial_state)
        if not result:
            raise ExtractionFailedError(f"LangGraph parsing failed for {filename}")
        doc = result.get("document")
        if not isinstance(doc, Document):
            raise ExtractionFailedError(f"LangGraph parsing failed for {filename}")
        return doc

    # ── LangGraph Nodes ────────────────────────────────────────────────────

    def _classify_pages_node(self, state: ParserState) -> dict[str, Any]:
        pdf = fitz.open(stream=state["file_content"], filetype="pdf")
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

    def _ocr_page(self, png_bytes: bytes, page_num: int) -> str:
        try:
            img = Image.open(io.BytesIO(png_bytes))
            return str(pytesseract.image_to_string(img, lang="spa+eng").strip())
        except Exception as exc:
            logger.warning(f"OCR failed on page {page_num}: {exc}")
            return ""

    async def _process_page(
        self, page: fitz.Page, p_info: dict[str, Any], filename: str
    ) -> tuple[str, str, dict[str, Any], str]:
        page_num = p_info["page_number"]
        selectable_text = p_info["selectable_text"]
        classification = p_info["classification"]

        tables_text = self._extract_tables_md(page, page_num)
        ocr_text = ""
        ai_data = {}
        extracted_text = ""

        if classification in ("scanned", "mixed"):
            pix = page.get_pixmap(dpi=200)
            png_bytes = pix.tobytes("png")
            ocr_text = self._ocr_page(png_bytes, page_num)

            if classification == "scanned":
                logger.info(f"{filename}: Page {page_num} → scanned. Running OCR + AI.")
                ai_data = await self._ai_extractor.extract_metadata(
                    text=ocr_text or None,
                    image_bytes=png_bytes,
                    filename=filename,
                )
                desc = ai_data.get("description", "")
                extracted_text = ocr_text or ""
                if desc:
                    extracted_text += f"\n\n[AI Visual Analysis]:\n{desc}"
            else:
                logger.info(f"{filename}: Page {page_num} → mixed. Running OCR + AI.")
                combined_text = selectable_text
                if ocr_text and ocr_text not in selectable_text:
                    combined_text = (
                        f"{selectable_text}\n\n[OCR Supplement]:\n{ocr_text}"
                    )
                ai_data = await self._ai_extractor.extract_metadata(
                    text=combined_text,
                    image_bytes=png_bytes,
                    filename=filename,
                )
                desc = ai_data.get("description", "")
                extracted_text = combined_text
                if desc:
                    extracted_text += f"\n\n[AI Visual Analysis]:\n{desc}"
        else:
            extracted_text = selectable_text

        if tables_text:
            extracted_text += f"\n\n[Extracted Tables]:\n{tables_text}"

        return extracted_text, tables_text, ai_data, ocr_text

    async def _extract_page_content_node(self, state: ParserState) -> dict[str, Any]:
        pdf = fitz.open(stream=state["file_content"], filetype="pdf")
        pages = list(state["pages"])
        full_text = ""

        for idx, p_info in enumerate(pages):
            page = pdf.load_page(p_info["page_number"] - 1)
            extracted_text, tables_text, ai_data, ocr_text = await self._process_page(
                page, p_info, state["filename"]
            )
            pages[idx] = {
                **p_info,
                "extracted_text": extracted_text,
                "tables_text": tables_text,
                "ai_data": ai_data,
                "ocr_text": ocr_text,
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
        if is_form_220:
            if not reconciled.get("form_type"):
                reconciled["form_type"] = "220"
            if reconciled.get("total_gross_income") is None:
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

    def _fallback_identifiers(
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

        if not res.get("employee_document_id"):
            m = re.search(
                r"(?:Número de identificación|No.*identificacion)[:\s]*([\d.]+)",
                text,
                re.IGNORECASE,
            )
            if m:
                res["employee_document_id"] = m.group(1).strip()

    def _fallback_employee(self, text: str, res: dict[str, Any]) -> None:
        if not res.get("employee_name"):
            m = re.search(
                r"(?:Primer apellido|MORENO)[:\s]*(\w+)\s+(?:Segundo apellido)?[:\s]*(\w+)?\s+(?:Primer nombre)?[:\s]*(\w+)?",
                text,
                re.IGNORECASE,
            )
            if m:
                parts = [p for p in [m.group(1), m.group(2), m.group(3)] if p]
                res["employee_name"] = " ".join(parts)

    def _fallback_location_dates(
        self, text: str, res: dict[str, Any], ext: dict[str, Any]
    ) -> None:
        if not ext.get("location"):
            m = re.search(
                r"(?:Bogotá|Medellín|Cali|Barranquilla|Cartagena|[A-ZÁÉÍÓÚ]{4,})\s*$",
                text,
                re.MULTILINE,
            )
            if m:
                ext["location"] = m.group(0).strip()

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

    def _parse_form_220_header_fields(self, sub: list[str]) -> dict[str, Any]:
        res: dict[str, Any] = {}
        idx = 0
        while idx < len(sub) and (
            "año gravable" in sub[idx].lower() or "ano gravable" in sub[idx].lower()
        ):
            idx += 1

        if idx < len(sub) and sub[idx].isdigit():
            res["form_number"] = sub[idx]
            idx += 1

        nit_val = None
        if idx < len(sub) and sub[idx].isdigit():
            nit_val = sub[idx]
            idx += 1

        dv_val = None
        if idx < len(sub) and sub[idx].isdigit():
            dv_val = sub[idx]
            idx += 1

        if nit_val and dv_val:
            res["nit_employer"] = f"{nit_val}-{dv_val}"
        elif nit_val:
            res["nit_employer"] = nit_val

        if idx < len(sub) and not sub[idx].isdigit():
            res["employer_name"] = sub[idx]
            idx += 1

        if idx < len(sub) and sub[idx].isdigit():
            idx += 1

        if idx < len(sub) and sub[idx].isdigit():
            res["employee_document_id"] = sub[idx]
            idx += 1

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
            res["employee_name"] = " ".join(firsts + lasts)
        elif name_parts:
            res["employee_name"] = " ".join(name_parts)

        date_ints: list[str] = []
        while idx < len(sub) and len(date_ints) < 9:
            if sub[idx].isdigit() and len(sub[idx]) <= 4:
                date_ints.append(sub[idx])
            idx += 1

        if len(date_ints) >= 6:
            res["period_start"] = (
                f"{date_ints[0]}-{date_ints[1].zfill(2)}-{date_ints[2].zfill(2)}"
            )
            res["period_end"] = (
                f"{date_ints[3]}-{date_ints[4].zfill(2)}-{date_ints[5].zfill(2)}"
            )

        if idx < len(sub) and not sub[idx].startswith("$") and not sub[idx].isdigit():
            res["location"] = sub[idx]

        return res

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

    def _map_form_220(self, text: str, doc: Document) -> None:
        """Sequential line-by-line parser for Form 220."""
        lines = self._clean_form_220_lines(text)
        tax_year = self._parse_form_220_tax_year(lines)
        if tax_year:
            doc.tax_year = tax_year

        header_idx = -1
        for i, line in enumerate(lines):
            if "certificado de ingresos y retenciones" in line.lower():
                header_idx = i
                break

        if header_idx != -1:
            sub = lines[header_idx + 1 :]
            header_fields = self._parse_form_220_header_fields(sub)

            # Map header fields to doc
            if "form_number" in header_fields:
                doc.form_number = header_fields["form_number"]
            if "nit_employer" in header_fields:
                doc.nit_employer = header_fields["nit_employer"]
            if "employer_name" in header_fields:
                doc.employer_name = header_fields["employer_name"]
            if "employee_document_id" in header_fields:
                doc.employee_document_id = header_fields["employee_document_id"]
            if "employee_name" in header_fields:
                doc.employee_name = header_fields["employee_name"]
            if "period_start" in header_fields:
                doc.period_start = header_fields["period_start"]
            if "period_end" in header_fields:
                doc.period_end = header_fields["period_end"]
            if "location" in header_fields:
                doc.location = header_fields["location"]

            self._apply_form_220_amounts(sub, doc)
