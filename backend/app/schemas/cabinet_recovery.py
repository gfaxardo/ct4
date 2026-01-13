"""
Schemas para Cabinet Recovery Impact 14d
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import date, datetime


class CabinetRecoveryImpactTotals(BaseModel):
    """Totales de impacto de recovery"""
    total_leads: int = Field(..., description="Total de leads")
    unidentified_count: int = Field(..., description="Leads sin identidad")
    identified_no_origin_count: int = Field(..., description="Leads con identidad pero sin origin")
    recovered_within_14d_count: int = Field(..., description="Leads recuperados dentro de 14 días")
    recovered_late_count: int = Field(..., description="Leads recuperados después de 14 días")
    recovered_within_14d_and_claim_count: int = Field(..., description="Leads recuperados dentro de 14 días y con claim")
    still_unidentified_count: int = Field(..., description="Leads todavía sin identidad")
    identified_but_missing_origin_count: int = Field(..., description="Leads con identidad pero falta origin")
    identified_origin_no_claim_count: int = Field(..., description="Leads con identidad y origin pero sin claim")


class CabinetRecoveryImpactSeriesItem(BaseModel):
    """Item de serie temporal"""
    event_date: date = Field(..., description="Fecha", alias="date")
    unidentified: int = Field(..., description="Leads sin identidad")
    recovered_within_14d: int = Field(..., description="Leads recuperados dentro de 14 días")
    recovered_late: int = Field(..., description="Leads recuperados después de 14 días")
    claims: int = Field(..., description="Leads con claims")
    
    class Config:
        populate_by_name = True


class CabinetRecoveryImpactResponse(BaseModel):
    """Respuesta del endpoint de impacto de recovery"""
    totals: CabinetRecoveryImpactTotals = Field(..., description="Totales de impacto")
    series: Optional[List[CabinetRecoveryImpactSeriesItem]] = Field(None, description="Serie temporal (últimos 30 días)")
    top_reasons: Optional[Dict[str, int]] = Field(None, description="Top razones de fallo (si existen)")
