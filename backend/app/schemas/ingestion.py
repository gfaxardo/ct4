from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from app.models.ops import RunStatus


class IngestionRunBase(BaseModel):
    status: RunStatus
    stats: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class IngestionRun(IngestionRunBase):
    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True



























