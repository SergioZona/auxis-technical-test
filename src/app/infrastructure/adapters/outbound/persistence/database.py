from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.infrastructure.config.clients import async_session_maker


class Base(DeclarativeBase):
    pass


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """Dependency for providing a database session."""
    async with async_session_maker() as session:
        yield session
