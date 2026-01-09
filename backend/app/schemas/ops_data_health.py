"""
Schemas Pydantic para consultar salud del sistema de identidad.

Basados en la vista ops.v_identity_system_health.
"""
from pydantic import BaseModel, field_validator
from typing import Optional, Dict
from datetime import datetime


class IdentitySystemHealthRow(BaseModel):
    """Métricas de salud del sistema de identidad canónica.
    
    Basado en ops.v_identity_system_health (1 fila).
    """
    calculated_at: datetime
    last_run_id: Optional[int] = None
    last_run_started_at: Optional[datetime] = None
    last_run_completed_at: Optional[datetime] = None
    last_run_status: str
    last_run_error_message: Optional[str] = None
    minutes_since_last_completed_run: Optional[int] = None
    hours_since_last_completed_run: Optional[int] = None
    unmatched_open_count: int
    unmatched_open_by_reason: Dict[str, int]
    active_alerts_count: int
    active_alerts_by_severity: Dict[str, int]
    total_persons: int
    total_links: int
    links_by_source: Dict[str, int]

    @field_validator('unmatched_open_by_reason', mode='before')
    @classmethod
    def parse_unmatched_by_reason(cls, v) -> Dict[str, int]:
        """Convierte JSONB a dict, maneja {} vacío."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}

    @field_validator('active_alerts_by_severity', mode='before')
    @classmethod
    def parse_alerts_by_severity(cls, v) -> Dict[str, int]:
        """Convierte JSONB a dict, maneja {} vacío."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}

    @field_validator('links_by_source', mode='before')
    @classmethod
    def parse_links_by_source(cls, v) -> Dict[str, int]:
        """Convierte JSONB a dict, maneja {} vacío."""
        if v is None:
            return {}
        if isinstance(v, dict):
            return v
        return {}

    class Config:
        from_attributes = True











