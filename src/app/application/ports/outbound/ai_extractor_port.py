from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class AiExtractorPort(ABC):
    """Port for AI/LLM-based document metadata extraction and description."""

    @abstractmethod
    async def extract_metadata(
        self,
        text: Optional[str] = None,
        image_bytes: Optional[bytes] = None,
        filename: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze text or page image to extract canonical metadata and page descriptions.
        Returns a dictionary with canonical fields and an optional "description" key.
        """
        pass
