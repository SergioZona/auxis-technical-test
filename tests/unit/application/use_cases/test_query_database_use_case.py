from unittest.mock import AsyncMock

import pytest

from app.application.use_cases.query_database_use_case import QueryDatabaseUseCase


@pytest.fixture
def mock_langchain_rag() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def use_case(mock_langchain_rag: AsyncMock) -> QueryDatabaseUseCase:
    return QueryDatabaseUseCase(langchain_rag=mock_langchain_rag)


async def test_query_database_use_case_executes(
    use_case: QueryDatabaseUseCase,
    mock_langchain_rag: AsyncMock,
) -> None:
    mock_langchain_rag.query_database.return_value = (
        "Total gross income sum is $123,000,000."
    )

    result = await use_case.execute("What is the sum of total gross income?")

    mock_langchain_rag.query_database.assert_called_once_with(
        "What is the sum of total gross income?"
    )
    assert result == "Total gross income sum is $123,000,000."
