from typing import Any

from app.application.ports.outbound.langchain_rag_port import LangChainRagPort


class ChatRagUseCase:
    """Use Case to perform natural language question answering over documents vector repository (RAG)."""

    def __init__(self, langchain_rag: LangChainRagPort):
        self._langchain_rag = langchain_rag

    async def execute(self, question: str) -> dict[str, Any]:
        return await self._langchain_rag.ask_rag_question(question)
