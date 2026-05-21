from unittest.mock import AsyncMock

import fitz
import pytest

from app.domain.models.document import Document
from app.infrastructure.adapters.outbound.document_parser import PyMuPDFDocumentParser


@pytest.fixture
def mock_ai_extractor() -> AsyncMock:
    extractor = AsyncMock()
    # Default mock response for document level extract
    extractor.extract_metadata.return_value = {
        "document_type": "invoice",
        "doc_date": "2024-08-08",
        "doc_number": "76543",
        "vendor_name": "Initech Corporation",
        "client_name": "Acme Corporation",
        "total_amount": 50000.0,
        "tax_amount": 1000.0,
        "tables": [{"description": "Consulting Services", "total": 50000.0}],
        "extras": {"custom_id": "12345"},
    }
    return extractor


@pytest.fixture
def parser(mock_ai_extractor: AsyncMock) -> PyMuPDFDocumentParser:
    return PyMuPDFDocumentParser(ai_extractor=mock_ai_extractor)


def create_text_pdf(text_elements: list[str]) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    for idx, text in enumerate(text_elements):
        page.insert_text((50, 20 + idx * 15), text)
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


async def test_parse_text_only_pdf_success(
    parser: PyMuPDFDocumentParser,
    mock_ai_extractor: AsyncMock,
) -> None:
    # Generate text PDF with > 100 chars to classify as "text"
    text_lines = [
        "Invoice from Initech Corporation to Acme Corporation.",
        "Invoice Number: 76543, Date: 2024-08-08.",
        "Total Amount Due: $50,000.00, Tax Amount: $1,000.00.",
        "This is some extra text to exceed the ocr threshold of 100 characters so that it is processed as pure text and not scanned PDF.",
    ]
    pdf_bytes = create_text_pdf(text_lines)

    # Execute parser
    doc = await parser.parse(pdf_bytes, "Invoice_76543.pdf")

    # Assertions
    assert isinstance(doc, Document)
    assert doc.extraction_method == "text"
    assert doc.document_type == "invoice"
    assert doc.doc_date == "2024-08-08"
    assert doc.doc_number == "76543"
    assert doc.vendor_name == "Initech Corporation"
    assert doc.client_name == "Acme Corporation"
    assert doc.total_amount == 50000.0
    assert doc.tax_amount == 1000.0
    assert len(doc.tables) == 1
    assert doc.tables[0]["description"] == "Consulting Services"
    assert doc.extras.get("custom_id") == "12345"
    assert len(doc.chunks) > 0


async def test_parse_scanned_pdf_ai_fallback_success(
    parser: PyMuPDFDocumentParser,
    mock_ai_extractor: AsyncMock,
) -> None:
    # PDF with little text → classified as scanned
    pdf_bytes = create_text_pdf(["Scanned Page"])

    # Mock AI extractor response for visual/scanned page
    mock_ai_extractor.extract_metadata.return_value = {
        "document_type": "receipt",
        "doc_date": "2024-09-09",
        "doc_number": "R-101",
        "vendor_name": "Gas Station",
        "client_name": "Employee Reimbursement",
        "total_amount": 45.50,
        "tax_amount": 3.20,
        "tables": [],
        "extras": {"fuel_type": "Premium"},
    }

    # Execute parser
    doc = await parser.parse(pdf_bytes, "Scanned_Receipt.pdf")

    # Assertions
    assert isinstance(doc, Document)
    assert doc.extraction_method == "ocr"
    assert doc.document_type == "receipt"
    assert doc.doc_date == "2024-09-09"
    assert doc.doc_number == "R-101"
    assert doc.vendor_name == "Gas Station"
    assert doc.total_amount == 45.50
    assert doc.extras.get("fuel_type") == "Premium"
    mock_ai_extractor.extract_metadata.assert_called()
