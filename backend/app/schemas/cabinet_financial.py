"""
Schemas para la vista financiera de Cabinet
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from decimal import Decimal
from decimal import Decimal


class CabinetFinancialRow(BaseModel):
    """Fila individual de la vista financiera"""
    driver_id: str = Field(..., description="ID del conductor")
    driver_name: Optional[str] = Field(None, description="Nombre completo del conductor")
    lead_date: Optional[date] = Field(None, description="Fecha de lead")
    iso_week: Optional[str] = Field(None, description="Semana ISO en formato YYYY-WW")
    week_start: Optional[date] = Field(None, description="Lunes de la semana ISO (canónico para filtros semanales)")
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
    # Campos de scout attribution (display only)
    scout_id: Optional[int] = Field(None, description="ID del scout asignado al driver (atribución canónica)")
    scout_name: Optional[str] = Field(None, description="Nombre del scout (si está disponible)")
    scout_quality_bucket: Optional[str] = Field(None, description="Calidad de la atribución scout: SATISFACTORY_LEDGER, EVENTS_ONLY, MIGRATIONS_ONLY, SCOUTING_DAILY_ONLY, CABINET_PAYMENTS_ONLY, MISSING")
    is_scout_resolved: bool = Field(False, description="Flag indicando si el scout está resuelto (true si hay scout_id)")
    scout_source_table: Optional[str] = Field(None, description="Tabla fuente de donde proviene el scout_id (para auditoría)")
    scout_attribution_date: Optional[date] = Field(None, description="Fecha de atribución del scout")
    scout_priority: Optional[int] = Field(None, description="Prioridad de la fuente de atribución (1=lead_ledger, 2=lead_events, 3=migrations, 4=scouting_daily, 5=cabinet_payments)")

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
    drivers_with_scout: int = Field(..., description="Drivers con scout atribuido (filtrado)")
    drivers_without_scout: int = Field(..., description="Drivers sin scout (filtrado)")
    pct_with_scout: float = Field(..., description="Porcentaje de drivers con scout (filtrado)")


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
    drivers_with_scout: int = Field(..., description="Drivers con scout atribuido (sin filtros)")
    drivers_without_scout: int = Field(..., description="Drivers sin scout (sin filtros)")
    pct_with_scout: float = Field(..., description="Porcentaje de drivers con scout (sin filtros)")


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


class ScoutAttributionMetrics(BaseModel):
    """Métricas de atribución scout para Cobranza Yango"""
    total_drivers: int = Field(..., description="Total de drivers (con filtros aplicados)")
    drivers_with_scout: int = Field(..., description="Drivers con scout asignado")
    drivers_without_scout: int = Field(..., description="Drivers sin scout")
    pct_with_scout: float = Field(..., description="Porcentaje de drivers con scout")
    breakdown_by_quality: dict[str, int] = Field(default_factory=dict, description="Desglose por scout_quality_bucket")
    breakdown_by_source: dict[str, int] = Field(default_factory=dict, description="Desglose por scout_source_table")
    drivers_without_scout_by_reason: dict[str, int] = Field(default_factory=dict, description="Desglose de drivers sin scout por razón (missing_identity, no_source_match)")
    top_missing_examples: list[dict] = Field(default_factory=list, description="Top 10 drivers sin scout con milestone (para debug): [{driver_id, lead_date, reached_m1, reached_m5, reached_m25, amount_due_yango}]")


class ScoutAttributionMetricsResponse(BaseModel):
    """Respuesta del endpoint de métricas de atribución scout"""
    status: str = Field(default="ok", description="Estado de la respuesta")
    metrics: ScoutAttributionMetrics = Field(..., description="Métricas de atribución scout")
    filters: dict = Field(default_factory=dict, description="Filtros aplicados")


class WeeklyKpiRow(BaseModel):
    """Fila de KPI semanal"""
    week_start: date = Field(..., description="Lunes de la semana ISO")
    total_rows: int = Field(..., description="Total de drivers en la semana")
    debt_sum: Decimal = Field(..., description="Suma de deuda (amount_due_yango)")
    with_scout: int = Field(..., description="Drivers con scout asignado")
    pct_with_scout: float = Field(..., description="Porcentaje de drivers con scout")
    reached_m1: int = Field(..., description="Drivers que alcanzaron M1")
    reached_m5: int = Field(..., description="Drivers que alcanzaron M5")
    reached_m25: int = Field(..., description="Drivers que alcanzaron M25")
    paid_sum: Decimal = Field(..., description="Suma de pagos (total_paid_yango)")
    unpaid_sum: Decimal = Field(..., description="Suma de deuda pendiente (amount_due_yango)")


class WeeklyKpisResponse(BaseModel):
    """Respuesta del endpoint de KPIs semanales"""
    status: str = Field(default="ok", description="Estado de la respuesta")
    weeks: list[WeeklyKpiRow] = Field(..., description="Lista de KPIs por semana")
    filters: dict = Field(default_factory=dict, description="Filtros aplicados")

