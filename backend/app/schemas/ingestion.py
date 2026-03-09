"""
Ingestion run Pydantic schemas for API validation.

Usado como response_model en POST /identity/run y POST /identity/drivers-index/refresh.
"""
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel

from app.models.ops import RunStatus


class IngestionRun(BaseModel):
    """Schema de respuesta para una corrida de ingesta."""
    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: RunStatus
    stats: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

    class Config:
        from_attributes = True
