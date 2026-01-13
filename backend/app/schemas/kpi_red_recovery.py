"""
Schemas para KPI Red Recovery Metrics
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date


class KpiRedRecoveryMetricsDaily(BaseModel):
    """Métricas diarias de recovery del KPI rojo"""
    metric_date: date = Field(..., description="Fecha de la métrica")
    backlog_start: int = Field(..., description="Backlog al inicio del día")
    new_backlog_in: int = Field(..., description="Leads que entraron al backlog en este día")
    matched_out: int = Field(..., description="Leads que fueron matched (salieron del backlog) en este día")
    backlog_end: int = Field(..., description="Backlog al final del día")
    net_change: int = Field(..., description="Cambio neto del backlog (new_backlog_in - matched_out)")
    top_fail_reason: Optional[str] = Field(None, description="Razón de fallo más común")


class KpiRedRecoveryMetricsResponse(BaseModel):
    """Respuesta del endpoint de métricas de recovery del KPI rojo"""
    today: Optional[KpiRedRecoveryMetricsDaily] = Field(None, description="Métricas de hoy")
    yesterday: Optional[KpiRedRecoveryMetricsDaily] = Field(None, description="Métricas de ayer")
    last_7_days: list[KpiRedRecoveryMetricsDaily] = Field(default_factory=list, description="Métricas de los últimos 7 días")
    current_backlog: int = Field(..., description="Backlog actual del KPI rojo")
