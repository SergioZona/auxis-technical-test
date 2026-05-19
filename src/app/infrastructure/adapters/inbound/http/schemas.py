"""
Pydantic schemas for inbound HTTP requests and outbound responses.
These live in the infrastructure layer — the domain knows nothing about them.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ── Response schemas ──────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str

