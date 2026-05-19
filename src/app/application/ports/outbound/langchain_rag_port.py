from abc import ABC, abstractmethod
from typing import Any


class LangChainRagPort(ABC):
    """Port for LangChain-powered conversational RAG and SQL Database queries."""

    @abstractmethod
    async def ask_rag_question(self, question: str) -> dict[str, Any]:
        """
        Ask a natural language question over the vector database (Qdrant) RAG context.
        """
        pass

    @abstractmethod
    async def query_database(self, query: str) -> str:
        """
        Run a natural language query over the structured PostgreSQL database using the LangChain SQL Agent.
        """
        pass
