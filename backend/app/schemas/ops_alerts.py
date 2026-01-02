"""
Schemas Pydantic para listar y consultar alertas operacionales.

Basados en el modelo ops.alerts.
"""
from pydantic import BaseModel, computed_field, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
import enum


class AlertSeverity(str, enum.Enum):
    """Severidad de una alerta."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class OpsAlertRow(BaseModel):
    """Una fila de alerta operacional para listado."""
    id: int
    created_at: datetime
    alert_type: str
    severity: AlertSeverity
    message: str
    week_label: Optional[str]
    details: Optional[Dict[str, Any]] = None
    run_id: Optional[int] = None
    acknowledged_at: Optional[datetime] = None

    @field_validator('severity', mode='before')
    @classmethod
    def parse_severity(cls, v: Any) -> str:
        """Convierte AlertSeverity del modelo a string para el enum del schema."""
        if hasattr(v, 'value'):
            return v.value
        if isinstance(v, str):
            return v
        return str(v)

    @computed_field
    def acknowledged(self) -> bool:
        """Campo derivado: True si acknowledged_at no es None."""
        return self.acknowledged_at is not None

    class Config:
        from_attributes = True


class OpsAlertsResponse(BaseModel):
    """Response para listado paginado de alertas operacionales."""
    items: list[OpsAlertRow]
    total: int
    limit: int
    offset: int

