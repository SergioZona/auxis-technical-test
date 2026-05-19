from unittest.mock import AsyncMock

import pytest

from app.application.use_cases.chat_rag_use_case import ChatRagUseCase


@pytest.fixture
def mock_langchain_rag() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def use_case(mock_langchain_rag: AsyncMock) -> ChatRagUseCase:
    return ChatRagUseCase(langchain_rag=mock_langchain_rag)


async def test_chat_rag_use_case_executes(
    use_case: ChatRagUseCase,
    mock_langchain_rag: AsyncMock,
) -> None:
    mock_langchain_rag.ask_rag_question.return_value = "The tax year is 2023."

    result = await use_case.execute("What is the tax year?")

    mock_langchain_rag.ask_rag_question.assert_called_once_with("What is the tax year?")
    assert result == "The tax year is 2023."
