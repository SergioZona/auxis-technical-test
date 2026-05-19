import logging
from typing import Any

from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from sqlalchemy import text

from app.application.ports.outbound.langchain_rag_port import LangChainRagPort
from app.application.ports.outbound.vector_port import VectorPort
from app.infrastructure.config.clients import engine
from app.infrastructure.config.settings import Settings

logger = logging.getLogger(__name__)

# Global reference to vector port for the tool to use
_vector_port: VectorPort | None = None


@tool
async def search_documents_tool(query: str) -> list[dict[str, Any]]:
    """
    Search the Qdrant vector database for semantic information from uploaded tax documents and invoices.
    Use this tool when the user asks questions about the textual content, meaning, or specific details within documents.
    Returns a list of relevant text chunks along with their document_id and page_number for citations.
    """
    if not _vector_port:
        return []

    chunks = await _vector_port.search(query, limit=5)
    return [
        {
            "text": chunk.text,
            "document_id": str(chunk.document_id),
            "page_number": chunk.page_number,
        }
        for chunk in chunks
    ]


@tool
async def query_database_tool(sql_query: str) -> str:
    """
    Execute a READ-ONLY PostgreSQL query against the 'documents' table.
    Use this tool to aggregate data, sum totals, count documents, or filter by exact values (e.g., all 'hybrid' extraction documents).

    Table Schema:
    - id (UUID)
    - filename (VARCHAR)
    - upload_date (TIMESTAMP)
    - form_type (VARCHAR)
    - tax_year (INTEGER)
    - nit_employer (VARCHAR)
    - employer_name (VARCHAR)
    - employee_name (VARCHAR)
    - period_start (TIMESTAMP)
    - period_end (TIMESTAMP)
    - total_gross_income (FLOAT)
    - income_tax_withheld (FLOAT)
    - extraction_method (VARCHAR)
    - extras (JSONB)

    Important: You must only execute read-only queries (SELECT).
    """
    # Enforce read only
    sql_lower = sql_query.lower()
    if any(
        forbidden in sql_lower
        for forbidden in [
            "insert",
            "update",
            "delete",
            "drop",
            "alter",
            "truncate",
            "create",
        ]
    ):
        return "Error: Write queries are forbidden."

    try:
        async with engine.begin() as conn:
            result = await conn.execute(text(sql_query))
            rows = result.mappings().all()
            if not rows:
                return "No results found."
            return str([dict(row) for row in rows])
    except Exception as e:
        return f"Error executing query: {str(e)}"


class LangChainRagAdapter(LangChainRagPort):
    """
    Adapter implementing LangChainRagPort.
    Uses ChatGoogleGenerativeAI (Gemini) or ChatOpenAI (GPT-4o-mini) based on keys.
    """

    def __init__(self, settings: Settings, vector_port: VectorPort):
        self._settings = settings
        self._vector_port = vector_port

        # Set global for tool
        global _vector_port
        _vector_port = vector_port

    def _get_llm(self) -> Any:
        gemini_key = self._settings.gemini_api_key
        openai_key = self._settings.openai_api_key

        if gemini_key:
            return ChatGoogleGenerativeAI(
                model="gemini-2.5-flash", google_api_key=gemini_key, temperature=0.1
            )
        elif openai_key:
            openai_kwargs: dict[str, Any] = {
                "model": "gpt-4o-mini",
                "api_key": openai_key,
                "temperature": 0.1,
            }
            return ChatOpenAI(**openai_kwargs)
        else:
            raise ValueError(
                "No LLM API keys configured (GEMINI_API_KEY or OPENAI_API_KEY required)."
            )

    def _get_callbacks(self) -> list[Any]:
        import os

        callbacks = []
        if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
            try:
                from langfuse.callback import CallbackHandler

                langfuse_handler = CallbackHandler(
                    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                    host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
                )
                callbacks.append(langfuse_handler)
            except ImportError:
                pass
        return callbacks

    def _extract_sources(self, intermediate_steps: list[Any]) -> list[dict[str, Any]]:
        sources = []
        for action, observation in intermediate_steps:
            if action.tool == "search_documents_tool" and isinstance(observation, list):
                for chunk in observation:
                    sources.append(chunk)
            elif action.tool == "query_database_tool":
                sources.append(
                    {
                        "text": f"SQL Query executed: {action.tool_input.get('sql_query', '')}\nResult: {observation}",
                        "document_id": "Database",
                        "page_number": "N/A",
                    }
                )
        return sources

    def _clean_output(self, ans: Any) -> str:
        if isinstance(ans, list):
            text_parts = []
            for part in ans:
                if isinstance(part, dict) and "text" in part:
                    text_parts.append(part["text"])
                elif isinstance(part, str):
                    text_parts.append(part)
            return "\n".join(text_parts)
        if isinstance(ans, dict) and "text" in ans:
            return str(ans["text"])
        return str(ans)

    async def ask_rag_question(self, question: str) -> dict[str, Any]:
        llm = self._get_llm()
        tools = [search_documents_tool, query_database_tool]

        system_prompt = (
            "You are a helpful tax and document intelligence assistant.\n"
            "You have access to two tools:\n"
            "1. search_documents_tool: For semantic text search over document contents (Qdrant).\n"
            "2. query_database_tool: For structured aggregations, filtering, statistics, and exact matches over the PostgreSQL metadata table.\n"
            "IMPORTANT: If a question requires both semantic understanding (e.g. details about contents, categories, or raw descriptions) AND structured metrics (e.g. counts, sums, or SQL queries), you MUST use BOTH tools in tandem. Do not rely on just one if both can enrich the answer.\n"
            "Synthesize the retrieved information clearly. Always return your final answer as clean, direct, human-readable markdown text. Avoid returning list structures, JSON wrappers, or raw dictionaries in your final output."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        agent = create_tool_calling_agent(llm, tools, prompt)
        agent_executor = AgentExecutor(
            agent=agent, tools=tools, verbose=True, return_intermediate_steps=True
        )

        callbacks = self._get_callbacks()
        response = await agent_executor.ainvoke(
            {"input": question}, config={"callbacks": callbacks}
        )

        sources = self._extract_sources(response.get("intermediate_steps", []))
        ans = self._clean_output(response.get("output", ""))

        return {"answer": ans, "sources": sources}

    async def query_database(self, query: str) -> str:
        # Obsolete, redirect to unified agent and return answer string to match port
        res = await self.ask_rag_question(query)
        return str(res.get("answer", ""))
