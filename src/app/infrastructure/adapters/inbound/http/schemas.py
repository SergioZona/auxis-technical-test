"""
Pydantic schemas for inbound HTTP requests and outbound responses.
These live in the infrastructure layer — the domain knows nothing about them.
"""

from pydantic import BaseModel

# ── Response schemas ──────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    environment: str
