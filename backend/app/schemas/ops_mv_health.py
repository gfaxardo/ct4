"""
Schemas Pydantic para consultar salud de Materialized Views.

Basado en pg_matviews y ops.mv_refresh_log.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class MvHealthRow(BaseModel):
    """Fila de salud de una Materialized View.
    
    Incluye información de la MV y su último refresh.
    """
    schema_name: str
    mv_name: str
    is_populated: Optional[bool] = None
    size_mb: float
    last_refresh_at: Optional[datetime] = None
    minutes_since_refresh: Optional[int] = None
    last_refresh_status: Optional[str] = None  # 'SUCCESS' | 'FAILED' | None
    last_refresh_error: Optional[str] = None
    calculated_at: datetime

    class Config:
        from_attributes = True


class MvHealthResponse(BaseModel):
    """Response paginado para salud de Materialized Views."""
    items: list[MvHealthRow]
    total: int
    limit: int
    offset: int


