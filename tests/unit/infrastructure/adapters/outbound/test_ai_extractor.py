from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.adapters.outbound.ai_extractor import LlmAiExtractor
from app.infrastructure.config.settings import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        gemini_api_key="mock-gemini-key",
        openai_api_key="mock-openai-key",
        qdrant_host="localhost",
        qdrant_port=6333,
        qdrant_collection="documents",
        max_upload_size_mb=10,
    )


def test_get_llm_gemini_priority(settings: Settings) -> None:
    extractor = LlmAiExtractor(settings)

    with patch(
        "app.infrastructure.adapters.outbound.ai_extractor.ChatGoogleGenerativeAI"
    ) as mock_gemini:
        llm = extractor._get_llm()
        assert llm is not None
        mock_gemini.assert_called_once()


def test_get_llm_openai_fallback(settings: Settings) -> None:
    settings.gemini_api_key = ""
    extractor = LlmAiExtractor(settings)

    with patch(
        "app.infrastructure.adapters.outbound.ai_extractor.ChatOpenAI"
    ) as mock_openai:
        llm = extractor._get_llm()
        assert llm is not None
        mock_openai.assert_called_once()


def test_get_llm_no_keys(settings: Settings) -> None:
    settings.gemini_api_key = ""
    settings.openai_api_key = ""
    extractor = LlmAiExtractor(settings)

    with pytest.raises(ValueError, match="No LLM API keys configured"):
        extractor._get_llm()


def test_parse_response_content(settings: Settings) -> None:
    extractor = LlmAiExtractor(settings)

    # string content
    assert extractor._parse_response_content("hello") == "hello"

    # list content
    list_content = ["hello ", {"type": "text", "text": "world"}, 123]
    assert extractor._parse_response_content(list_content) == "hello world"


def test_clean_json_string(settings: Settings) -> None:
    extractor = LlmAiExtractor(settings)

    raw = '```json\n{"key": "value"}\n```'
    assert extractor._clean_json_string(raw) == '{"key": "value"}'

    assert extractor._clean_json_string("simple string") == "simple string"


def test_coerce_types(settings: Settings) -> None:
    extractor = LlmAiExtractor(settings)

    raw_dict = {
        "total_gross_income": "100000.50",
        "income_tax_withheld": "5000",
        "tax_year": "2024",
        "extras": {
            "salary_payments": "80000",
            "social_benefits": "invalid-float",
        },
    }

    coerced = extractor._coerce_types(raw_dict)
    assert coerced["total_gross_income"] == 100000.50
    assert coerced["income_tax_withheld"] == 5000.0
    assert coerced["tax_year"] == 2024
    assert coerced["extras"]["salary_payments"] == 80000.0
    assert coerced["extras"]["social_benefits"] is None


@pytest.mark.anyio
async def test_extract_metadata_success(settings: Settings) -> None:
    extractor = LlmAiExtractor(settings)

    # Mock LLM and response
    mock_llm = AsyncMock()
    mock_response = MagicMock()
    mock_response.content = (
        '{"employee_name": "John Doe", "total_gross_income": 50000.0}'
    )
    mock_llm.ainvoke.return_value = mock_response

    with patch.object(extractor, "_get_llm", return_value=mock_llm):
        result = await extractor.extract_metadata(
            text="Sample raw text", image_bytes=b"png-bytes", filename="test.pdf"
        )

        assert result["employee_name"] == "John Doe"
        assert result["total_gross_income"] == 50000.0
        mock_llm.ainvoke.assert_called_once()


@pytest.mark.anyio
async def test_extract_metadata_llm_error(settings: Settings) -> None:
    extractor = LlmAiExtractor(settings)

    with patch.object(extractor, "_get_llm", side_effect=ValueError("LLM Error")):
        result = await extractor.extract_metadata(text="Sample raw text")
        assert result == {}
