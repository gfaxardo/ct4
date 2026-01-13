"""
Ingestion run Pydantic schemas for API validation.

Defines schemas for tracking and displaying ingestion job status.
"""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel

from app.models.ops import RunStatus


class IngestionRunBase(BaseModel):
    """Base schema for ingestion run data."""
    status: RunStatus
    stats: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class IngestionRun(IngestionRunBase):
    """Full ingestion run schema with timestamps."""
    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
