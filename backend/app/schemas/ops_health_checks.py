"""
Schemas Pydantic para consultar checks de salud del sistema.

Basado en la vista ops.v_health_checks.
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class HealthCheckRow(BaseModel):
    """Fila de un check de salud.
    
    Representa el resultado de evaluar una condición de salud.
    """
    check_key: str
    severity: str  # 'error' | 'warning' | 'info'
    status: str  # 'OK' | 'WARN' | 'ERROR'
    message: str
    drilldown_url: Optional[str] = None
    last_evaluated_at: datetime

    class Config:
        from_attributes = True


class HealthChecksResponse(BaseModel):
    """Response para checks de salud del sistema."""
    items: list[HealthCheckRow]

