from app.application.ports.outbound.langchain_rag_port import LangChainRagPort


class QueryDatabaseUseCase:
    """Use Case to perform natural language querying over the PostgreSQL structured database."""

    def __init__(self, langchain_rag: LangChainRagPort):
        self._langchain_rag = langchain_rag

    async def execute(self, query: str) -> str:
        return await self._langchain_rag.query_database(query)
