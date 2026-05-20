import hashlib
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, String, func, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.adapters.outbound.persistence.database import Base


class ApiTokenModel(Base):
    """
    SQLAlchemy model for DB-backed bearer tokens.
    Stores cryptographically secure SHA-256 hashes of tokens.
    """

    __tablename__ = "api_tokens"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    description: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


def hash_token(token: str) -> str:
    """Computes SHA-256 hash of a raw token."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


async def verify_db_token(session: AsyncSession, token: str) -> bool:
    """
    Validates a raw bearer token against active, non-expired hashes in the DB.
    """
    if not token:
        return False

    hashed = hash_token(token)
    now = datetime.now()

    query = select(ApiTokenModel).where(
        ApiTokenModel.token_hash == hashed,
        ApiTokenModel.is_active == True,
    )
    result = await session.execute(query)
    model = result.scalar_one_or_none()

    if not model:
        return False

    if model.expires_at and model.expires_at < now:
        return False

    return True
