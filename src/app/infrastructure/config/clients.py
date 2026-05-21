from fastembed import TextEmbedding
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.config.settings import get_settings

settings = get_settings()

# ── Database Client ───────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Qdrant Client ─────────────────────────────────────────────────────────────
def get_qdrant_client() -> AsyncQdrantClient:
    return AsyncQdrantClient(
        host=settings.qdrant_host, port=settings.qdrant_port, check_compatibility=False
    )


# ── FastEmbed Embedding Model Client ──────────────────────────────────────────
_embedding_model = None


def get_embedding_model() -> TextEmbedding:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
    return _embedding_model


# ── Tracing ───────────────────────────────────────────────────────────────────
# LangSmith tracing is enabled automatically via env vars:
#   LANGCHAIN_TRACING_V2=true
#   LANGCHAIN_API_KEY=ls__...
#   LANGCHAIN_PROJECT=auxis
# No extra client needed — LangChain picks them up at import time.
