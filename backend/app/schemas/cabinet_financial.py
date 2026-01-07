"""
Schemas para la vista financiera de Cabinet
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from decimal import Decimal


class CabinetFinancialRow(BaseModel):
    """Fila individual de la vista financiera"""
    driver_id: str = Field(..., description="ID del conductor")
    driver_name: Optional[str] = Field(None, description="Nombre completo del conductor")
    lead_date: Optional[date] = Field(None, description="Fecha de lead")
    iso_week: Optional[str] = Field(None, description="Semana ISO en formato YYYY-WW")
    connected_flag: bool = Field(..., description="Flag indicando si el driver se conectó")
    connected_date: Optional[date] = Field(None, description="Primera fecha de conexión")
    total_trips_14d: int = Field(..., description="Total de viajes completados dentro de la ventana de 14 días")
    reached_m1_14d: bool = Field(..., description="Flag indicando si alcanzó M1 dentro de la ventana")
    reached_m5_14d: bool = Field(..., description="Flag indicando si alcanzó M5 dentro de la ventana")
    reached_m25_14d: bool = Field(..., description="Flag indicando si alcanzó M25 dentro de la ventana")
    expected_amount_m1: Decimal = Field(..., description="Monto esperado para milestone M1")
    expected_amount_m5: Decimal = Field(..., description="Monto esperado para milestone M5")
    expected_amount_m25: Decimal = Field(..., description="Monto esperado para milestone M25")
    expected_total_yango: Decimal = Field(..., description="Total esperado acumulativo de Yango")
    claim_m1_exists: bool = Field(..., description="Flag indicando si existe un claim M1")
    claim_m1_paid: bool = Field(..., description="Flag indicando si el claim M1 está pagado")
    claim_m5_exists: bool = Field(..., description="Flag indicando si existe un claim M5")
    claim_m5_paid: bool = Field(..., description="Flag indicando si el claim M5 está pagado")
    claim_m25_exists: bool = Field(..., description="Flag indicando si existe un claim M25")
    claim_m25_paid: bool = Field(..., description="Flag indicando si el claim M25 está pagado")
    paid_amount_m1: Decimal = Field(..., description="Monto pagado para milestone M1")
    paid_amount_m5: Decimal = Field(..., description="Monto pagado para milestone M5")
    paid_amount_m25: Decimal = Field(..., description="Monto pagado para milestone M25")
    total_paid_yango: Decimal = Field(..., description="Total pagado por Yango")
    amount_due_yango: Decimal = Field(..., description="Monto faltante por cobrar a Yango")

    class Config:
        from_attributes = True


class CabinetFinancialSummary(BaseModel):
    """Resumen ejecutivo de la vista financiera (con filtros aplicados)"""
    total_drivers: int = Field(..., description="Total de drivers cabinet (filtrado)")
    drivers_with_expected: int = Field(..., description="Drivers con deuda esperada (filtrado)")
    drivers_with_debt: int = Field(..., description="Drivers con deuda pendiente (filtrado)")
    total_expected_yango: Decimal = Field(..., description="Total esperado Yango (filtrado)")
    total_paid_yango: Decimal = Field(..., description="Total pagado Yango (filtrado)")
    total_debt_yango: Decimal = Field(..., description="Total deuda Yango (filtrado)")
    collection_percentage: float = Field(..., description="Porcentaje de cobranza (filtrado)")
    drivers_m1: int = Field(..., description="Drivers que alcanzaron M1 (filtrado)")
    drivers_m5: int = Field(..., description="Drivers que alcanzaron M5 (filtrado)")
    drivers_m25: int = Field(..., description="Drivers que alcanzaron M25 (filtrado)")


class CabinetFinancialSummaryTotal(BaseModel):
    """Resumen ejecutivo total (sin filtros)"""
    total_drivers: int = Field(..., description="Total de drivers cabinet (sin filtros)")
    drivers_with_expected: int = Field(..., description="Drivers con deuda esperada (sin filtros)")
    drivers_with_debt: int = Field(..., description="Drivers con deuda pendiente (sin filtros)")
    total_expected_yango: Decimal = Field(..., description="Total esperado Yango (sin filtros)")
    total_paid_yango: Decimal = Field(..., description="Total pagado Yango (sin filtros)")
    total_debt_yango: Decimal = Field(..., description="Total deuda Yango (sin filtros)")
    collection_percentage: float = Field(..., description="Porcentaje de cobranza (sin filtros)")
    drivers_m1: int = Field(..., description="Drivers que alcanzaron M1 (sin filtros)")
    drivers_m5: int = Field(..., description="Drivers que alcanzaron M5 (sin filtros)")
    drivers_m25: int = Field(..., description="Drivers que alcanzaron M25 (sin filtros)")


class CabinetFinancialMeta(BaseModel):
    """Metadatos de paginación"""
    limit: int = Field(..., description="Límite de resultados")
    offset: int = Field(..., description="Offset para paginación")
    returned: int = Field(..., description="Número de resultados devueltos")
    total: int = Field(..., description="Total de resultados disponibles")


class CabinetFinancialResponse(BaseModel):
    """Respuesta del endpoint de vista financiera"""
    meta: CabinetFinancialMeta = Field(..., description="Metadatos de paginación")
    summary: Optional[CabinetFinancialSummary] = Field(None, description="Resumen ejecutivo (con filtros aplicados)")
    summary_total: Optional[CabinetFinancialSummaryTotal] = Field(None, description="Resumen ejecutivo total (sin filtros)")
    data: list[CabinetFinancialRow] = Field(..., description="Lista de drivers con información financiera")

