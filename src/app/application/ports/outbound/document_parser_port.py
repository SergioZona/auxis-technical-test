import abc
from typing import BinaryIO

from app.domain.models.document import Document


class DocumentParserPort(abc.ABC):
    """
    Outbound port for parsing files (PDFs, images) into Document models.
    Handles text extraction, OCR fallback, and mapping to canonical structure.
    """

    @abc.abstractmethod
    async def parse(self, file_content: bytes, filename: str) -> Document:
        """Parses raw file bytes and extracts text and canonical metadata."""
        pass
