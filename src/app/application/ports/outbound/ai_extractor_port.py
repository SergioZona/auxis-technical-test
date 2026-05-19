from abc import ABC, abstractmethod
from typing import Any


class AiExtractorPort(ABC):
    """Port for AI/LLM-based document metadata extraction and description."""

    @abstractmethod
    async def extract_metadata(
        self,
        text: str | None = None,
        image_bytes: bytes | None = None,
        filename: str | None = None,
    ) -> dict[str, Any]:
        """
        Analyze text or page image to extract canonical metadata and page descriptions.
        Returns a dictionary with canonical fields and an optional "description" key.
        """
        pass
