from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.adapters.outbound.langchain_rag_adapter import (
    LangChainRagAdapter,
    query_database_tool,
    search_documents_tool,
)
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


@pytest.fixture
def mock_vector_port() -> AsyncMock:
    return AsyncMock()


def test_rag_get_llm_gemini(settings: Settings, mock_vector_port: AsyncMock) -> None:
    adapter = LangChainRagAdapter(settings, mock_vector_port)
    with patch(
        "app.infrastructure.adapters.outbound.langchain_rag_adapter.ChatGoogleGenerativeAI"
    ) as mock_gemini:
        llm = adapter._get_llm()
        assert llm is not None
        mock_gemini.assert_called_once()


def test_rag_get_llm_openai_fallback(
    settings: Settings, mock_vector_port: AsyncMock
) -> None:
    settings.gemini_api_key = ""
    adapter = LangChainRagAdapter(settings, mock_vector_port)
    with patch(
        "app.infrastructure.adapters.outbound.langchain_rag_adapter.ChatOpenAI"
    ) as mock_openai:
        llm = adapter._get_llm()
        assert llm is not None
        mock_openai.assert_called_once()


def test_rag_get_llm_no_keys(settings: Settings, mock_vector_port: AsyncMock) -> None:
    settings.gemini_api_key = ""
    settings.openai_api_key = ""
    adapter = LangChainRagAdapter(settings, mock_vector_port)
    with pytest.raises(ValueError, match="No LLM API keys configured"):
        adapter._get_llm()


@pytest.mark.anyio
async def test_search_documents_tool(mock_vector_port: AsyncMock) -> None:
    from app.domain.models.document import DocumentChunk

    chunk = DocumentChunk(text="sample text", page_number=2, chunk_index=0)
    mock_vector_port.search.return_value = [chunk]

    # Instantiate adapter to assign the global _vector_port variable
    _ = LangChainRagAdapter(Settings(), mock_vector_port)

    results = await search_documents_tool.ainvoke({"query": "tax info"})
    assert len(results) == 1
    assert results[0]["text"] == "sample text"
    assert results[0]["page_number"] == 2


@pytest.mark.anyio
async def test_query_database_tool_forbidden() -> None:
    result = await query_database_tool.ainvoke({"sql_query": "DROP TABLE documents;"})
    assert "forbidden" in result.lower()


@pytest.mark.anyio
async def test_query_database_tool_success() -> None:
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    mock_result.mappings().all.return_value = [{"total": 100}]
    mock_conn.execute.return_value = mock_result

    mock_begin = MagicMock()
    mock_begin.__aenter__.return_value = mock_conn

    mock_engine = MagicMock()
    mock_engine.begin.return_value = mock_begin

    with patch(
        "app.infrastructure.adapters.outbound.langchain_rag_adapter.engine", mock_engine
    ):
        result = await query_database_tool.ainvoke(
            {"sql_query": "SELECT count(*) as total FROM documents;"}
        )
        assert "100" in result


@pytest.mark.anyio
async def test_ask_rag_question_success(
    settings: Settings, mock_vector_port: AsyncMock
) -> None:
    adapter = LangChainRagAdapter(settings, mock_vector_port)

    mock_llm = MagicMock()
    mock_agent = MagicMock()

    # Mock AgentExecutor behavior
    mock_agent_executor_instance = AsyncMock()
    mock_agent_executor_instance.ainvoke.return_value = {
        "output": "This is a RAG response",
        "intermediate_steps": [
            (
                MagicMock(tool="search_documents_tool", tool_input={"query": "test"}),
                [{"text": "obs text", "document_id": "doc1", "page_number": 1}],
            )
        ],
    }

    with (
        patch.object(adapter, "_get_llm", return_value=mock_llm),
        patch(
            "app.infrastructure.adapters.outbound.langchain_rag_adapter.create_tool_calling_agent",
            return_value=mock_agent,
        ),
        patch(
            "app.infrastructure.adapters.outbound.langchain_rag_adapter.AgentExecutor",
            return_value=mock_agent_executor_instance,
        ),
    ):
        res = await adapter.ask_rag_question("How much was total tax?")
        assert res["answer"] == "This is a RAG response"
        assert len(res["sources"]) == 1
        assert res["sources"][0]["text"] == "obs text"


@pytest.mark.anyio
async def test_query_database_wrapper(
    settings: Settings, mock_vector_port: AsyncMock
) -> None:
    adapter = LangChainRagAdapter(settings, mock_vector_port)

    with patch.object(
        adapter,
        "ask_rag_question",
        return_value={"answer": "Query response", "sources": []},
    ) as mock_ask:
        result = await adapter.query_database("SELECT * FROM documents;")
        assert result == "Query response"
        mock_ask.assert_called_once_with("SELECT * FROM documents;")
