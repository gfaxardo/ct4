from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID


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


# Yango Cabinet Claims Schemas
class YangoCabinetClaimRow(BaseModel):
    claim_key: Optional[str] = None
    person_key: Optional[str] = None
    driver_id: Optional[str] = None
    driver_name: Optional[str] = None
    milestone_value: Optional[int] = None
    lead_date: Optional[date] = None
    expected_amount: Optional[Decimal] = None
    yango_due_date: Optional[date] = None
    days_overdue_yango: Optional[int] = None
    overdue_bucket_yango: Optional[str] = None
    yango_payment_status: Optional[str] = None
    reason_code: Optional[str] = None
    identity_status: Optional[str] = None
    match_rule: Optional[str] = None
    match_confidence: Optional[str] = None
    is_reconcilable_enriched: Optional[bool] = None
    payment_key: Optional[str] = None
    pay_date: Optional[date] = None
    suggested_driver_id: Optional[str] = None

    class Config:
        from_attributes = True


class YangoCabinetClaimsResponse(BaseModel):
    status: str
    count: int
    total: int
    filters: Dict[str, Any]
    rows: List[YangoCabinetClaimRow]


# Yango Cabinet Claim Drilldown Schemas
class LeadCabinetInfo(BaseModel):
    source_pk: Optional[str] = None
    match_rule: Optional[str] = None
    match_score: Optional[float] = None
    confidence_level: Optional[str] = None
    linked_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PaymentInfo(BaseModel):
    payment_key: Optional[str] = None
    pay_date: Optional[date] = None
    milestone_value: Optional[int] = None
    identity_status: Optional[str] = None
    match_rule: Optional[str] = None

    class Config:
        from_attributes = True


class ReconciliationInfo(BaseModel):
    reconciliation_status: Optional[str] = None
    expected_amount: Optional[Decimal] = None
    paid_payment_key: Optional[str] = None
    paid_date: Optional[date] = None
    match_method: Optional[str] = None

    class Config:
        from_attributes = True


class YangoCabinetClaimDrilldownResponse(BaseModel):
    status: str
    claim: Optional[YangoCabinetClaimRow] = None
    lead_cabinet: Optional[LeadCabinetInfo] = None
    payment_exact: Optional[PaymentInfo] = None
    payments_other_milestones: List[PaymentInfo] = []
    reconciliation: Optional[ReconciliationInfo] = None
    misapplied_explanation: Optional[str] = None


# Yango Cabinet MV Health Schema
class YangoCabinetMvHealthRow(BaseModel):
    mv_name: str
    last_ok_refresh_finished_at: Optional[datetime] = None
    hours_since_ok_refresh: Optional[float] = None
    status_bucket: str  # OK, WARN, CRIT, NO_REFRESH
    last_status: Optional[str] = None
    last_error: Optional[str] = None
    rows_after_refresh: Optional[int] = None
    calculated_at: datetime

    class Config:
        from_attributes = True


# Driver Matrix Schemas
class DriverMatrixRow(BaseModel):
    driver_id: Optional[str] = None
    person_key: Optional[UUID] = None
    driver_name: Optional[str] = None
    lead_date: Optional[date] = None
    week_start: Optional[date] = None
    origin_tag: Optional[str] = None
    connected_flag: Optional[bool] = None
    connected_date: Optional[date] = None
    # Milestone M1
    m1_achieved_flag: Optional[bool] = None
    m1_achieved_date: Optional[date] = None
    m1_expected_amount_yango: Optional[Decimal] = None
    m1_yango_payment_status: Optional[str] = None
    m1_window_status: Optional[str] = None
    m1_overdue_days: Optional[int] = None
    # Milestone M5
    m5_achieved_flag: Optional[bool] = None
    m5_achieved_date: Optional[date] = None
    m5_expected_amount_yango: Optional[Decimal] = None
    m5_yango_payment_status: Optional[str] = None
    m5_window_status: Optional[str] = None
    m5_overdue_days: Optional[int] = None
    # Milestone M25
    m25_achieved_flag: Optional[bool] = None
    m25_achieved_date: Optional[date] = None
    m25_expected_amount_yango: Optional[Decimal] = None
    m25_yango_payment_status: Optional[str] = None
    m25_window_status: Optional[str] = None
    m25_overdue_days: Optional[int] = None
    # Scout
    scout_due_flag: Optional[bool] = None
    scout_paid_flag: Optional[bool] = None
    scout_amount: Optional[Decimal] = None
    # Flags de inconsistencia de milestones
    m5_without_m1_flag: Optional[bool] = None
    m25_without_m5_flag: Optional[bool] = None
    milestone_inconsistency_notes: Optional[str] = None

    class Config:
        from_attributes = True


class DriverMatrixTotals(BaseModel):
    drivers: int
    expected_yango_sum: Decimal
    paid_sum: Decimal
    receivable_sum: Decimal
    expired_count: int
    in_window_count: int


class DriverMatrixMeta(BaseModel):
    page: int
    limit: int
    total_rows: int


class DriverMatrixResponse(BaseModel):
    rows: List[DriverMatrixRow]
    meta: DriverMatrixMeta
    totals: DriverMatrixTotals


# Ops Driver Matrix Response (formato meta/data)
class OpsDriverMatrixMeta(BaseModel):
    limit: int
    offset: int
    returned: int
    total: int


class OpsDriverMatrixResponse(BaseModel):
    meta: OpsDriverMatrixMeta
    data: List[DriverMatrixRow]


# Cabinet Milestones Reconciliation Schemas
class CabinetReconciliationRow(BaseModel):
    driver_id: Optional[str] = None
    milestone_value: Optional[int] = None
    
    # ACHIEVED fields
    achieved_flag: Optional[bool] = None
    achieved_person_key: Optional[str] = None
    achieved_lead_date: Optional[date] = None
    achieved_date: Optional[date] = None
    achieved_trips_in_window: Optional[int] = None
    window_days: Optional[int] = None
    expected_amount: Optional[Decimal] = None
    achieved_currency: Optional[str] = None
    rule_id: Optional[int] = None
    
    # PAID fields
    paid_flag: Optional[bool] = None
    paid_person_key: Optional[str] = None
    pay_date: Optional[date] = None
    payment_key: Optional[str] = None
    identity_status: Optional[str] = None
    match_rule: Optional[str] = None
    match_confidence: Optional[str] = None
    latest_snapshot_at: Optional[datetime] = None
    
    # Reconciliation
    reconciliation_status: Optional[str] = None  # OK, ACHIEVED_NOT_PAID, PAID_WITHOUT_ACHIEVEMENT, NOT_APPLICABLE

    class Config:
        from_attributes = True


class CabinetReconciliationResponse(BaseModel):
    status: str
    count: int
    total: int
    filters: Dict[str, Any]
    rows: List[CabinetReconciliationRow]