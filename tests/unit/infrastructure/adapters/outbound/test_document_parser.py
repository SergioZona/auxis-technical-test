from unittest.mock import AsyncMock

import fitz
import pytest

from app.domain.models.document import Document
from app.infrastructure.adapters.outbound.document_parser import PyMuPDFDocumentParser


@pytest.fixture
def mock_ai_extractor() -> AsyncMock:
    extractor = AsyncMock()
    extractor.extract_metadata.return_value = {}
    return extractor


@pytest.fixture
def parser(mock_ai_extractor: AsyncMock) -> PyMuPDFDocumentParser:
    return PyMuPDFDocumentParser(ai_extractor=mock_ai_extractor)


def create_text_pdf(text_elements: list[str]) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    for idx, text in enumerate(text_elements):
        # Use small vertical spacing to avoid off-page clipping
        page.insert_text((50, 20 + idx * 15), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


async def test_parse_text_only_pdf_success(
    parser: PyMuPDFDocumentParser,
    mock_ai_extractor: AsyncMock,
) -> None:
    # Generate mock PDF bytes for text-based Form 220
    text_lines = [
        "Año gravable 2025",
        "certificado de ingresos y retenciones",
        "Año gravable",
        "220",  # form_number
        "901638314",  # nit_employer
        "5",  # dv
        "TRAFFIC TECH COLOMBIA",  # employer_name
        "1006025642",  # employee_document_id
        "ZONA",
        "MORENO",
        "SERGIO",
        "JULIAN",
        "2025",  # stop word
        "08",
        "11",
        "2025",
        "12",
        "31",  # period_start/end
        "COLOMBIA",  # location
        # Amounts (must have >= 27 entries)
        "$72.221.000",  # salary_payments (0)
        "$0",
        "$0",
        "$0",
        "$0",
        "$0",
        "$0",  # social_benefits (6)
        "$0",
        "$0",
        "$0",
        "$0",  # other_income_payments (10)
        "$0",
        "$0",
        "$0",
        "$0",
        "$0",
        "$72.221.000",  # total_gross_income (16)
        "$0",  # health_contributions (17)
        "$0",  # pension_contributions (18)
        "$0",
        "$0",
        "$0",
        "$0",
        "$0",  # average_monthly_income (23)
        "$6.131.000",  # income_tax_withheld (24)
        "$0",
        "$6.131.000",  # total_annual_withholding (26)
    ]
    pdf_bytes = create_text_pdf(text_lines)

    # Execute parser
    doc = await parser.parse(pdf_bytes, "Certificado.pdf")

    # Assertions
    assert isinstance(doc, Document)
    assert doc.extraction_method == "text"
    assert doc.form_type == "220"
    assert doc.tax_year == 2025
    assert doc.nit_employer == "901638314-5"
    assert doc.employer_name == "TRAFFIC TECH COLOMBIA"
    assert doc.employee_name == "SERGIO JULIAN ZONA MORENO"
    assert doc.total_gross_income == 72221000.0
    assert doc.income_tax_withheld == 6131000.0
    assert len(doc.chunks) > 0


async def test_parse_scanned_pdf_ai_fallback_success(
    parser: PyMuPDFDocumentParser,
    mock_ai_extractor: AsyncMock,
) -> None:
    # PDF with no text → classified as scanned
    pdf_bytes = create_text_pdf([])

    # Mock AI extractor response for multimodal scanned page
    mock_ai_extractor.extract_metadata.return_value = {
        "description": "Scanned document preview",
        "employee_name": "SERGIO JULIAN ZONA MORENO",
        "total_gross_income": 72221000.0,
        "tax_year": 2025,
        "form_type": "220",
    }

    # Execute parser
    doc = await parser.parse(pdf_bytes, "Scanned_Certificado.pdf")

    # Assertions
    assert isinstance(doc, Document)
    assert doc.extraction_method == "ocr"
    assert doc.employee_name == "SERGIO JULIAN ZONA MORENO"
    assert doc.total_gross_income == 72221000.0
    assert doc.tax_year == 2025
    assert doc.form_type == "220"
    mock_ai_extractor.extract_metadata.assert_called()
    # AI is called for page extraction (image) + reconcile (always AI-first)
    assert mock_ai_extractor.extract_metadata.call_count >= 1
