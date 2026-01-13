"""
Schema Pydantic para el estado global de salud del sistema.

Basado en la vista ops.v_health_global.
"""
from pydantic import BaseModel
from datetime import datetime


class HealthGlobalResponse(BaseModel):
    """Response para el estado global de salud del sistema."""
    global_status: str  # 'OK' | 'WARN' | 'ERROR'
    error_count: int
    warn_count: int
    ok_count: int
    calculated_at: datetime

    class Config:
        from_attributes = True
