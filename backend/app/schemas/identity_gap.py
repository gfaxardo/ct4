"""
Schemas para Identity Gap & Recovery
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
from uuid import UUID


class IdentityGapRow(BaseModel):
    """Fila individual de análisis de brecha"""
    lead_id: str = Field(..., description="ID del lead (external_id o id)")
    lead_date: date = Field(..., description="Fecha de creación del lead")
    person_key: Optional[UUID] = Field(None, description="Person key asignado (NULL si no tiene identidad)")
    has_identity: bool = Field(..., description="TRUE si tiene person_key asignado")
    has_origin: bool = Field(..., description="TRUE si tiene registro en canon.identity_origin")
    has_driver_activity: bool = Field(..., description="TRUE si tiene actividad en summary_daily")
    trips_14d: int = Field(..., description="Total de viajes completados dentro de la ventana de 14 días")
    gap_reason: str = Field(..., description="Razón de la brecha: no_identity, no_origin, activity_without_identity, no_activity, resolved")
    gap_age_days: int = Field(..., description="Días desde lead_date hasta hoy")
    risk_level: str = Field(..., description="Nivel de riesgo: high, medium, low")


class IdentityGapTotals(BaseModel):
    """Totales agregados de brechas"""
    total_leads: int = Field(..., description="Total de leads")
    unresolved: int = Field(..., description="Total de leads unresolved")
    resolved: int = Field(..., description="Total de leads resolved")
    pct_unresolved: float = Field(..., description="Porcentaje de leads unresolved")


class IdentityGapBreakdown(BaseModel):
    """Desglose por gap_reason y risk_level"""
    gap_reason: str
    risk_level: str
    count: int


class IdentityGapResponse(BaseModel):
    """Respuesta del endpoint de identity gaps"""
    totals: IdentityGapTotals
    breakdown: List[IdentityGapBreakdown]
    items: List[IdentityGapRow]
    meta: dict = Field(default_factory=dict, description="Metadatos de paginación")


class IdentityGapAlertRow(BaseModel):
    """Fila individual de alerta"""
    lead_id: str = Field(..., description="ID del lead con problema")
    alert_type: str = Field(..., description="Tipo de alerta: over_24h_no_identity, over_7d_unresolved, activity_no_identity")
    severity: str = Field(..., description="Nivel de severidad: high, medium, low")
    days_open: int = Field(..., description="Días desde lead_date hasta hoy")
    suggested_action: str = Field(..., description="Acción sugerida para resolver la alerta")


class IdentityGapAlertsResponse(BaseModel):
    """Respuesta del endpoint de alertas"""
    items: List[IdentityGapAlertRow]
    total: int = Field(..., description="Total de alertas")
    meta: dict = Field(default_factory=dict, description="Metadatos adicionales")
