"""Pydantic schemas for Yango Payments Reconciliation"""
from pydantic import BaseModel
from typing import Optional, Literal
from datetime import date, datetime
from uuid import UUID
from enum import Enum


class YangoPaymentIngestResponse(BaseModel):
    """Response for Yango payment ingest snapshot"""
    status: str
    rows_inserted: int
    snapshot_at: datetime


class YangoReconciliationSummaryRow(BaseModel):
    """Summary row for Yango reconciliation (aggregated by week and milestone)"""
    pay_week_start_monday: date
    milestone_value: int
    amount_expected_sum: float
    amount_paid_confirmed_sum: float
    amount_paid_enriched_sum: float
    amount_paid_total_visible: float
    amount_paid_sum: Optional[float] = None  # For backward compatibility, alias of amount_paid_total_visible
    amount_paid_assumed: Optional[float] = None
    amount_pending_active_sum: Optional[float] = None
    amount_pending_expired_sum: Optional[float] = None
    amount_diff: float
    amount_diff_assumed: Optional[float] = None
    anomalies_total: int
    count_expected: int
    count_paid_confirmed: int
    count_paid_enriched: int
    count_paid: int  # Total: confirmed + enriched
    count_pending_active: Optional[int] = None
    count_pending_expired: Optional[int] = None
    count_drivers: Optional[int] = None
    
    class Config:
        from_attributes = True


class YangoReconciliationSummaryResponse(BaseModel):
    """Response for Yango reconciliation summary endpoint"""
    status: str
    count: int
    filters: dict
    rows: list[YangoReconciliationSummaryRow]


class YangoReconciliationItemRow(BaseModel):
    """Item row for Yango reconciliation (detailed claims)"""
    driver_id: Optional[str] = None
    person_key: Optional[UUID] = None
    lead_date: Optional[date] = None
    pay_week_start_monday: Optional[date] = None
    milestone_value: Optional[int] = None
    expected_amount: Optional[float] = None
    currency: Optional[str] = None
    due_date: Optional[date] = None
    window_status: Optional[str] = None
    paid_payment_key: Optional[str] = None
    paid_payment_key_confirmed: Optional[str] = None
    paid_payment_key_enriched: Optional[str] = None
    paid_date: Optional[date] = None
    paid_date_confirmed: Optional[date] = None
    paid_date_enriched: Optional[date] = None
    paid_is_paid: Optional[bool] = None
    is_paid_confirmed: Optional[bool] = None
    is_paid_enriched: Optional[bool] = None
    is_paid_effective: Optional[bool] = None
    match_method: Optional[str] = None
    paid_status: Optional[str] = None  # 'paid_confirmed' | 'paid_enriched' | 'pending_active' | 'pending_expired'
    # Identity enrichment fields
    identity_status: Optional[str] = None  # 'confirmed' | 'enriched' | 'ambiguous' | 'no_match'
    match_rule: Optional[str] = None  # 'source_upstream' | 'name_full_unique' | 'name_tokens_unique' | 'ambiguous' | 'no_match'
    match_confidence: Optional[str] = None  # 'high' | 'medium' | 'low'
    
    class Config:
        from_attributes = True


class YangoReconciliationItemsResponse(BaseModel):
    """Response for Yango reconciliation items endpoint"""
    status: str
    count: int
    total: Optional[int] = None
    filters: dict
    rows: list[YangoReconciliationItemRow]


class YangoLedgerUnmatchedRow(BaseModel):
    """Fila de ledger sin match contra claims"""
    payment_key: Optional[str] = None
    pay_date: Optional[date] = None
    is_paid: Optional[bool] = None
    milestone_value: Optional[int] = None
    driver_id: Optional[str] = None  # Alias de driver_id_final para compatibilidad
    person_key: Optional[UUID] = None  # Alias de person_key_final para compatibilidad
    raw_driver_name: Optional[str] = None
    driver_name_normalized: Optional[str] = None
    match_rule: Optional[str] = None
    match_confidence: Optional[str] = None
    latest_snapshot_at: Optional[datetime] = None
    source_pk: Optional[str] = None
    identity_source: Optional[str] = None  # 'original' | 'enriched_by_name' | 'none'
    identity_enriched: Optional[bool] = None  # Flag que indica si la identidad fue enriquecida
    driver_id_final: Optional[str] = None  # Campo final (original o enriched)
    person_key_final: Optional[UUID] = None  # Campo final (original o enriched)
    # New fields from enriched view
    identity_status: Optional[str] = None  # 'confirmed' | 'enriched' | 'ambiguous' | 'no_match'
    
    class Config:
        from_attributes = True


class YangoLedgerUnmatchedResponse(BaseModel):
    """Respuesta del endpoint de ledger sin match"""
    status: str = "ok"
    count: int
    total: int
    filters: dict
    rows: list[YangoLedgerUnmatchedRow]


class ClaimDetailRow(BaseModel):
    """Detalle de un claim para un conductor"""
    milestone_value: Optional[int] = None
    expected_amount: Optional[float] = None
    currency: Optional[str] = None
    lead_date: Optional[date] = None
    due_date: Optional[date] = None
    pay_week_start_monday: Optional[date] = None
    paid_status: Optional[str] = None
    paid_payment_key: Optional[str] = None
    paid_date: Optional[date] = None
    is_paid_effective: Optional[bool] = None
    match_method: Optional[str] = None
    identity_status: Optional[str] = None
    match_rule: Optional[str] = None
    match_confidence: Optional[str] = None
    
    class Config:
        from_attributes = True


class YangoDriverDetailResponse(BaseModel):
    """Respuesta del endpoint de detalle por conductor"""
    status: str = "ok"
    driver_id: str
    person_key: Optional[UUID] = None
    claims: list[ClaimDetailRow]
    summary: dict  # total_expected, total_paid, count_paid, count_pending_active, count_pending_expired


# Schemas for Payment Eligibility endpoint
class OrderByField(str, Enum):
    """Campos válidos para ordenamiento en payment eligibility"""
    payable_date = "payable_date"
    lead_date = "lead_date"
    amount = "amount"


class OrderDirection(str, Enum):
    """Dirección de ordenamiento"""
    asc = "ASC"
    desc = "DESC"


class PaymentEligibilityRow(BaseModel):
    """Fila de resultado de payment eligibility query"""
    origin_tag: Optional[str] = None
    rule_scope: Optional[str] = None
    is_payable: Optional[bool] = None
    scout_id: Optional[int] = None
    driver_id: Optional[str] = None
    person_key: Optional[UUID] = None
    payable_date: Optional[date] = None
    expected_amount: Optional[float] = None
    currency: Optional[str] = None
    milestone_value: Optional[int] = None
    window_days: Optional[int] = None
    # Agregar más campos según la vista ops.v_payment_calculation
    
    class Config:
        from_attributes = True


class PaymentEligibilityResponse(BaseModel):
    """Respuesta del endpoint de payment eligibility"""
    status: str
    count: int
    filters: dict
    rows: list[PaymentEligibilityRow]
