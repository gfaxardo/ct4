from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


# Yango Reconciliation Summary Schemas
class YangoReconciliationSummaryRow(BaseModel):
    pay_week_start_monday: date
    milestone_value: int
    amount_expected_sum: Decimal
    amount_paid_confirmed_sum: Decimal
    amount_paid_enriched_sum: Decimal
    amount_paid_total_visible: Decimal
    amount_pending_active_sum: Decimal
    amount_pending_expired_sum: Decimal
    amount_diff: Decimal
    amount_diff_assumed: Decimal
    anomalies_total: int
    count_expected: int
    count_paid_confirmed: int
    count_paid_enriched: int
    count_paid: int
    count_pending_active: int
    count_pending_expired: int
    count_drivers: int
    amount_paid_sum: Optional[Decimal] = None  # Alias para compatibilidad
    amount_paid_assumed: Optional[Decimal] = None  # Alias para compatibilidad

    class Config:
        from_attributes = True


class YangoReconciliationSummaryResponse(BaseModel):
    status: str
    count: int
    filters: Dict[str, Any]
    rows: List[YangoReconciliationSummaryRow]


# Yango Reconciliation Items Schemas
class YangoReconciliationItemRow(BaseModel):
    driver_id: Optional[str] = None
    person_key: Optional[str] = None
    lead_date: Optional[date] = None
    pay_week_start_monday: Optional[date] = None
    milestone_value: Optional[int] = None
    expected_amount: Optional[Decimal] = None
    currency: Optional[str] = None
    due_date: Optional[date] = None
    window_status: Optional[str] = None
    paid_payment_key: Optional[str] = None
    paid_payment_key_confirmed: Optional[str] = None
    paid_payment_key_enriched: Optional[str] = None
    paid_date: Optional[date] = None
    paid_date_confirmed: Optional[date] = None
    paid_date_enriched: Optional[date] = None
    is_paid_effective: Optional[bool] = None
    match_method: Optional[str] = None
    paid_status: Optional[str] = None
    identity_status: Optional[str] = None
    match_rule: Optional[str] = None
    match_confidence: Optional[str] = None

    class Config:
        from_attributes = True


class YangoReconciliationItemsResponse(BaseModel):
    status: str
    count: int
    total: int
    filters: Dict[str, Any]
    rows: List[YangoReconciliationItemRow]


# Yango Ledger Unmatched Schemas
class YangoLedgerUnmatchedRow(BaseModel):
    payment_key: str
    pay_date: Optional[date] = None
    is_paid: Optional[bool] = None
    milestone_value: Optional[int] = None
    driver_id: Optional[str] = None
    person_key: Optional[str] = None
    raw_driver_name: Optional[str] = None
    driver_name_normalized: Optional[str] = None
    match_rule: Optional[str] = None
    match_confidence: Optional[str] = None
    latest_snapshot_at: Optional[datetime] = None
    source_pk: Optional[str] = None
    identity_source: Optional[str] = None
    identity_enriched: Optional[str] = None
    driver_id_final: Optional[str] = None
    person_key_final: Optional[str] = None
    identity_status: Optional[str] = None

    class Config:
        from_attributes = True


class YangoLedgerUnmatchedResponse(BaseModel):
    status: str
    count: int
    total: int
    filters: Dict[str, Any]
    rows: List[YangoLedgerUnmatchedRow]


# Yango Driver Detail Schemas
class ClaimDetailRow(BaseModel):
    milestone_value: Optional[int] = None
    expected_amount: Optional[Decimal] = None
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
    status: str
    driver_id: str
    person_key: Optional[str] = None
    claims: List[ClaimDetailRow]
    summary: Dict[str, Any]


# Payment Eligibility Schemas
class OrderByField(str, Enum):
    payable_date = "payable_date"
    lead_date = "lead_date"
    amount = "amount"


class OrderDirection(str, Enum):
    asc = "asc"
    desc = "desc"


class PaymentEligibilityRow(BaseModel):
    person_key: Optional[str] = None
    origin_tag: Optional[str] = None
    scout_id: Optional[int] = None
    driver_id: Optional[str] = None
    lead_date: Optional[date] = None
    rule_id: Optional[int] = None
    rule_scope: Optional[str] = None
    milestone_trips: Optional[int] = None
    window_days: Optional[int] = None
    currency: Optional[str] = None
    amount: Optional[Decimal] = None
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
    status: str
    count: int
    filters: Dict[str, Any]
    rows: List[PaymentEligibilityRow]
