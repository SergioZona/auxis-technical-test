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


async def test_parse_pdf_triggering_fallbacks(
    parser: PyMuPDFDocumentParser,
    mock_ai_extractor: AsyncMock,
) -> None:
    # Mock AI extractor to return empty to force fallbacks to run
    mock_ai_extractor.extract_metadata.return_value = {}

    text_lines = [
        "Número de formulario: 987654321",
        "Razón social: EMPRESA S.A.S. NIT 800.123.456-7",
        "NIT: 800.123.456-7",
        "Número de identificación: 10203040",
        "Primer apellido: GONZALEZ",
        "Segundo apellido: RODRIGUEZ",
        "Primer nombre: PEDRO",
        "Año gravable: 2024",
        "Formulario 210",
        "2024-01-15",
        "2024-12-15",
        "Total ingresos brutos: $120.000.000",
        "Valor de la retención en la fuente: $12.000.000",
        "Pagos por salarios: $100.000.000",
        "Pagos por prestaciones sociales: $20.000.000",
        "Otros pagos: $0",
        "Aportes obligatorios por salud: $4.000.000",
        "Aportes obligatorios a fondos de pensiones: $4.000.000",
        "Ingreso laboral promedio: $10.000.000",
        "Total retención año gravable: $12.000.000",
        "BOGOTÁ",
    ]
    pdf_bytes = create_text_pdf(text_lines)

    doc = await parser.parse(pdf_bytes, "Fallback_Document.pdf")

    assert isinstance(doc, Document)
    assert doc.form_type == "210"
    assert doc.tax_year == 2024
    assert doc.nit_employer == "800.123.456-7"
    assert doc.employer_name == "EMPRESA S.A.S."
    assert doc.employee_document_id == "10203040"
    assert doc.employee_name == "PEDRO GONZALEZ RODRIGUEZ"
    assert doc.period_start == "2024-01-15"
    assert doc.period_end == "2024-12-15"
    assert doc.total_gross_income == 120000000.0
    assert doc.income_tax_withheld == 12000000.0
    assert doc.extras.get("location") == "BOGOTÁ"
    assert doc.extras.get("salary_payments") == 100000000.0
    assert doc.extras.get("social_benefits") == 20000000.0
    assert doc.extras.get("health_contributions") == 4000000.0
    assert doc.extras.get("pension_contributions") == 4000000.0
    assert doc.extras.get("average_monthly_income") == 10000000.0
    assert doc.extras.get("total_annual_withholding") == 12000000.0
