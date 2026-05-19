"""
Pydantic schemas for inbound HTTP requests and outbound responses.
These live in the infrastructure layer — the domain knows nothing about them.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ── Request schemas ───────────────────────────────────────────────────────────


class CreateItemRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, examples=["My Item"])
    description: str = Field(
        ..., min_length=1, max_length=1000, examples=["A sample description"]
    )


class UpdateItemRequest(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1, max_length=1000)


# ── Response schemas ──────────────────────────────────────────────────────────


class ItemResponse(BaseModel):
    id: UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PingResponse(BaseModel):
    message: str = "pong"


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
