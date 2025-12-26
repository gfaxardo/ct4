from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from uuid import UUID
from enum import Enum


class OrderByField(str, Enum):
    """Campo por el cual ordenar los resultados"""
    payable_date = "payable_date"
    lead_date = "lead_date"
    amount = "amount"


class OrderDirection(str, Enum):
    """Dirección del ordenamiento"""
    asc = "asc"
    desc = "desc"


class PaymentEligibilityRow(BaseModel):
    """Fila de resultado de la vista ops.v_payment_calculation"""
    person_key: Optional[UUID] = None
    origin_tag: Optional[str] = None
    scout_id: Optional[int] = None
    driver_id: Optional[str] = None
    lead_date: Optional[date] = None
    rule_id: Optional[int] = None
    rule_scope: Optional[str] = None  # 'scout' | 'partner'
    milestone_trips: Optional[int] = None
    window_days: Optional[int] = None
    currency: Optional[str] = None
    amount: Optional[float] = None  # Numeric -> float
    rule_valid_from: Optional[date] = None
    rule_valid_to: Optional[date] = None
    milestone_achieved: Optional[bool] = None
    achieved_date: Optional[date] = None
    achieved_trips_in_window: Optional[int] = None
    is_payable: Optional[bool] = None
    payable_date: Optional[date] = None
    payment_scheme: Optional[str] = None

    class Config:
        from_attributes = True


class PaymentEligibilityResponse(BaseModel):
    """Respuesta del endpoint de elegibilidad de pagos"""
    status: str = "ok"
    count: int
    filters: dict
    rows: list[PaymentEligibilityRow]


# ============================================================================
# Schemas para Conciliación de Pagos Yango
# ============================================================================

class YangoPaymentIngestResponse(BaseModel):
    """Respuesta del endpoint de ingest de snapshots de pagos Yango"""
    status: str = "ok"
    rows_inserted: int
    snapshot_at: datetime

    class Config:
        from_attributes = True


class YangoReconciliationSummaryRow(BaseModel):
    """Fila de resultado de ops.v_yango_reconciliation_summary o ops.v_yango_reconciliation_summary_ui"""
    pay_week_start_monday: Optional[date] = None
    milestone_value: Optional[int] = None
    reconciliation_status: Optional[str] = None
    # Campos de summary original
    count_items: Optional[int] = None
    count_drivers_with_driver_id: Optional[int] = None
    count_drivers_with_person_key: Optional[int] = None
    count_drivers_total: Optional[int] = None
    sum_amount_expected: Optional[float] = None
    count_paid: Optional[int] = None
    count_pending: Optional[int] = None
    count_anomalies: Optional[int] = None
    min_payable_date: Optional[date] = None
    max_payable_date: Optional[date] = None
    min_paid_date: Optional[date] = None
    max_paid_date: Optional[date] = None
    # Campos de summary_ui (opcionales, tolerantes)
    rows_count: Optional[int] = None
    amount_expected_sum: Optional[float] = None
    amount_paid_sum: Optional[float] = None
    amount_diff: Optional[float] = None
    count_expected: Optional[int] = None
    count_drivers: Optional[int] = None

    class Config:
        from_attributes = True


class YangoReconciliationSummaryResponse(BaseModel):
    """Respuesta del endpoint de resumen de reconciliación Yango"""
    status: str = "ok"
    count: int
    filters: dict
    rows: list[YangoReconciliationSummaryRow]


class YangoReconciliationItemRow(BaseModel):
    """Fila de resultado de ops.v_yango_reconciliation_detail"""
    pay_week_start_monday: Optional[date] = None
    pay_iso_year_week: Optional[str] = None
    payable_date: Optional[date] = None
    achieved_date: Optional[date] = None
    lead_date: Optional[date] = None
    lead_origin: Optional[str] = None
    payer: Optional[str] = None
    milestone_type: Optional[str] = None
    milestone_value: Optional[int] = None
    window_days: Optional[int] = None
    trips_in_window: Optional[int] = None
    person_key: Optional[UUID] = None
    driver_id: Optional[str] = None
    expected_amount: Optional[float] = None
    currency: Optional[str] = None
    created_at_export: Optional[datetime] = None
    paid_payment_key: Optional[str] = None
    paid_snapshot_at: Optional[datetime] = None
    paid_source_pk: Optional[str] = None
    paid_date: Optional[date] = None
    paid_time: Optional[str] = None  # TIME type from PostgreSQL
    paid_raw_driver_name: Optional[str] = None
    paid_driver_name_normalized: Optional[str] = None
    paid_is_paid: Optional[bool] = None
    paid_match_rule: Optional[str] = None
    paid_match_confidence: Optional[str] = None
    match_method: Optional[str] = None
    reconciliation_status: Optional[str] = None
    sort_date: Optional[date] = None

    class Config:
        from_attributes = True


class YangoReconciliationItemsResponse(BaseModel):
    """Respuesta del endpoint de items de reconciliación Yango"""
    status: str = "ok"
    count: int
    filters: dict
    rows: list[YangoReconciliationItemRow]

