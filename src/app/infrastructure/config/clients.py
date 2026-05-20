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


# ── Langfuse Tracing Client ───────────────────────────────────────────────────
_langfuse_handler = None

def get_langfuse_handler():
    global _langfuse_handler
    if not settings.langfuse_public_key or not settings.langfuse_secret_key:
        return None

    if _langfuse_handler is not None:
        return _langfuse_handler

    try:
        import os

        os.environ.setdefault("LANGFUSE_PUBLIC_KEY", settings.langfuse_public_key)
        os.environ.setdefault("LANGFUSE_SECRET_KEY", settings.langfuse_secret_key)
        os.environ.setdefault("LANGFUSE_HOST", settings.langfuse_host)

        from langfuse.callback import CallbackHandler

        _langfuse_handler = CallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
        return _langfuse_handler
    except ImportError as e:
        import logging

        logging.getLogger(__name__).warning(
            f"Langfuse tracing disabled — missing dependency: {e}"
        )
        return None
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(
            f"Error initializing Langfuse CallbackHandler: {e}"
        )
        return None
