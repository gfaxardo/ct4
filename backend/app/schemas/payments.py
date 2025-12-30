"""
Schemas para endpoints de reconciliación de pagos Yango
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import date
from uuid import UUID
from enum import Enum


# ============================================================================
# Summary Response Schemas
# ============================================================================

class YangoReconciliationSummaryRow(BaseModel):
    """Fila de resumen agregado por semana y milestone"""
    pay_week_start_monday: date
    milestone_value: int
    amount_expected_sum: float
    amount_paid_confirmed_sum: float
    amount_paid_enriched_sum: float
    amount_paid_total_visible: float
    amount_pending_active_sum: float
    amount_pending_expired_sum: float
    amount_diff: float
    amount_diff_assumed: float
    anomalies_total: int
    count_expected: int
    count_paid_confirmed: int
    count_paid_enriched: int
    count_paid: int
    count_pending_active: int
    count_pending_expired: int
    count_drivers: int
    # Aliases para compatibilidad
    amount_paid_sum: Optional[float] = None
    amount_paid_assumed: Optional[float] = None

    class Config:
        from_attributes = True


class YangoReconciliationSummaryResponse(BaseModel):
    """Respuesta del endpoint de resumen de reconciliación"""
    status: str
    count: int
    filters: Dict[str, Any]
    rows: List[YangoReconciliationSummaryRow]


# ============================================================================
# Items Response Schemas
# ============================================================================

class YangoReconciliationItemRow(BaseModel):
    """Fila de item detallado de reconciliación"""
    driver_id: Optional[str] = None
    person_key: Optional[UUID] = None
    lead_date: date
    pay_week_start_monday: date
    milestone_value: int
    expected_amount: float
    currency: str
    due_date: date
    window_status: Optional[str] = None
    paid_payment_key: Optional[str] = None
    paid_payment_key_confirmed: Optional[str] = None
    paid_payment_key_enriched: Optional[str] = None
    paid_date: Optional[date] = None
    paid_date_confirmed: Optional[date] = None
    paid_date_enriched: Optional[date] = None
    is_paid_effective: bool
    match_method: str
    paid_status: str
    identity_status: Optional[str] = None
    match_rule: Optional[str] = None
    match_confidence: Optional[str] = None

    class Config:
        from_attributes = True


class YangoReconciliationItemsResponse(BaseModel):
    """Respuesta del endpoint de items de reconciliación"""
    status: str
    count: int
    total: int
    filters: Dict[str, Any]
    rows: List[YangoReconciliationItemRow]


# ============================================================================
# Ledger Unmatched Schemas
# ============================================================================

class YangoLedgerUnmatchedRow(BaseModel):
    """Fila de ledger sin match contra claims"""
    payment_key: str
    pay_date: date
    is_paid: bool
    milestone_value: int
    driver_id: Optional[str] = None
    person_key: Optional[UUID] = None
    raw_driver_name: Optional[str] = None
    driver_name_normalized: Optional[str] = None
    match_rule: Optional[str] = None
    match_confidence: Optional[str] = None
    latest_snapshot_at: Optional[Any] = None  # datetime
    source_pk: Optional[str] = None
    identity_source: Optional[str] = None
    identity_enriched: Optional[bool] = None
    driver_id_final: Optional[str] = None
    person_key_final: Optional[UUID] = None
    identity_status: Optional[str] = None

    class Config:
        from_attributes = True


class YangoLedgerUnmatchedResponse(BaseModel):
    """Respuesta del endpoint de ledger sin match"""
    status: str
    count: int
    total: int
    filters: Dict[str, Any]
    rows: List[YangoLedgerUnmatchedRow]


# ============================================================================
# Driver Detail Schemas
# ============================================================================

class ClaimDetailRow(BaseModel):
    """Fila de detalle de claim para un conductor"""
    milestone_value: int
    expected_amount: float
    currency: str
    lead_date: date
    due_date: date
    pay_week_start_monday: date
    paid_status: str
    paid_payment_key: Optional[str] = None
    paid_date: Optional[date] = None
    is_paid_effective: bool
    match_method: str
    identity_status: Optional[str] = None
    match_rule: Optional[str] = None
    match_confidence: Optional[str] = None

    class Config:
        from_attributes = True


class YangoDriverDetailResponse(BaseModel):
    """Respuesta del endpoint de detalle de conductor"""
    status: str
    driver_id: str
    person_key: Optional[UUID] = None
    claims: List[ClaimDetailRow]
    summary: Dict[str, Any]


# ============================================================================
# Payment Eligibility Schemas
# ============================================================================

class OrderByField(str, Enum):
    """Campos permitidos para ordenar en payment eligibility"""
    payable_date = "payable_date"
    lead_date = "lead_date"
    amount = "amount"


class OrderDirection(str, Enum):
    """Dirección de ordenamiento"""
    asc = "asc"
    desc = "desc"


class PaymentEligibilityRow(BaseModel):
    """Fila de elegibilidad de pago desde ops.v_payment_calculation"""
    # Campos comunes de la vista (flexible para SELECT *)
    origin_tag: Optional[str] = None
    rule_scope: Optional[str] = None
    is_payable: Optional[bool] = None
    scout_id: Optional[int] = None
    driver_id: Optional[str] = None
    payable_date: Optional[date] = None
    lead_date: Optional[date] = None
    amount: Optional[float] = None
    # Campos adicionales que pueden existir en la vista
    milestone_value: Optional[int] = None
    currency: Optional[str] = None
    person_key: Optional[UUID] = None
    # Permitir campos adicionales dinámicos
    class Config:
        from_attributes = True
        extra = "allow"  # Permite campos adicionales de la vista


class PaymentEligibilityResponse(BaseModel):
    """Respuesta del endpoint de elegibilidad de pago"""
    status: str
    count: int
    filters: Dict[str, Any]
    rows: List[PaymentEligibilityRow]


# ============================================================================
# Claims 14d Schemas
# ============================================================================

class Claims14dRow(BaseModel):
    """Fila de claim desde ops.v_yango_payments_claims_cabinet_14d"""
    driver_id: Optional[str] = None
    person_key: Optional[UUID] = None
    lead_date: date
    pay_week_start_monday: date
    milestone_value: int
    expected_amount: float
    currency: str
    due_date: date
    window_status: str
    paid_status: str
    is_paid_confirmed: bool
    is_paid_enriched: bool
    paid_date: Optional[date] = None
    identity_status: Optional[str] = None
    match_rule: Optional[str] = None
    match_confidence: Optional[str] = None
    paid_payment_key: Optional[str] = None
    paid_payment_key_confirmed: Optional[str] = None
    paid_payment_key_enriched: Optional[str] = None

    class Config:
        from_attributes = True


class Claims14dResponse(BaseModel):
    """Respuesta del endpoint de claims 14d"""
    status: str
    count: int
    total: int
    filters: Dict[str, Any]
    rows: List[Claims14dRow]


class Claims14dSummaryRow(BaseModel):
    """Fila de resumen agregado por semana y milestone"""
    pay_week_start_monday: date
    milestone_value: int
    expected_amount_sum: float
    paid_confirmed_amount_sum: float
    paid_enriched_amount_sum: float
    pending_active_amount_sum: float
    pending_expired_amount_sum: float
    expected_count: int
    paid_confirmed_count: int
    paid_enriched_count: int
    pending_active_count: int
    pending_expired_count: int

    class Config:
        from_attributes = True


class Claims14dSummaryResponse(BaseModel):
    """Respuesta del endpoint de resumen de claims 14d"""
    status: str
    count: int
    filters: Dict[str, Any]
    rows: List[Claims14dSummaryRow]


# ============================================================================
# Claims Cabinet Schemas (Nueva vista v_claims_payment_status_cabinet)
# ============================================================================

class ClaimsCabinetRow(BaseModel):
    """Fila de claim desde ops.v_claims_payment_status_cabinet"""
    driver_id: Optional[str] = None
    person_key: Optional[UUID] = None
    milestone_value: int
    lead_date: date
    due_date: date
    expected_amount: float
    paid_flag: bool
    paid_date: Optional[date] = None
    payment_key: Optional[str] = None
    payment_identity_status: Optional[str] = None
    payment_match_rule: Optional[str] = None
    payment_match_confidence: Optional[str] = None
    payment_status: str  # 'paid' | 'not_paid'
    payment_reason: str  # 'payment_found' | 'no_payment_found'

    class Config:
        from_attributes = True


class ClaimsCabinetResponse(BaseModel):
    """Respuesta del endpoint de claims cabinet"""
    status: str
    count: int
    total: int
    filters: Dict[str, Any]
    rows: List[ClaimsCabinetRow]


class ClaimsCabinetSummaryRow(BaseModel):
    """Fila de resumen agregado por semana y milestone desde ops.v_claims_payment_status_cabinet"""
    pay_week_start_monday: date
    milestone_value: int
    expected_amount_sum: float
    paid_amount_sum: float
    not_paid_amount_sum: float
    expected_count: int
    paid_count: int
    not_paid_count: int

    class Config:
        from_attributes = True


class ClaimsCabinetSummaryResponse(BaseModel):
    """Respuesta del endpoint de resumen de claims cabinet"""
    status: str
    count: int
    filters: Dict[str, Any]
    rows: List[ClaimsCabinetSummaryRow]


# ============================================================================
# Evidence Pack Schemas
# ============================================================================

class CabinetPaymentEvidencePackRow(BaseModel):
    """Fila de evidence pack para responder a Yango con evidencia clara"""
    claim_driver_id: Optional[str] = None
    claim_person_key: Optional[UUID] = None
    claim_milestone_value: int
    lead_date: date
    due_date: date
    expected_amount: float
    payment_status: str  # 'paid' | 'not_paid'
    reason_code: str
    action_priority: str
    paid_flag: bool
    payment_key: Optional[str] = None
    pay_date: Optional[date] = None
    ledger_driver_id_final: Optional[str] = None
    ledger_person_key_original: Optional[UUID] = None
    ledger_milestone_value: Optional[int] = None
    match_rule: Optional[str] = None
    match_confidence: Optional[str] = None
    identity_status: Optional[str] = None
    milestone_paid: Optional[int] = None  # Cuando reason_code='payment_found_other_milestone'
    evidence_level: str  # 'driver_id_exact' | 'person_key_only' | 'other_milestone' | 'none'

    class Config:
        from_attributes = True


class CabinetPaymentEvidencePackResponse(BaseModel):
    """Respuesta del endpoint de evidence pack"""
    status: str
    count: int
    total: int
    filters: Dict[str, Any]
    aggregates: Optional[Dict[str, Any]] = None  # Agregados por evidence_level y reason_code
    rows: List[CabinetPaymentEvidencePackRow]


# ============================================================================
# Drivers Cabinet Schemas
# ============================================================================

class CabinetDriverRow(BaseModel):
    """Fila de driver agrupado desde claims cabinet"""
    driver_id: Optional[str] = None
    person_key: Optional[UUID] = None
    driver_name_display: str
    lead_date_min: date
    lead_date_max: date
    expected_total: float
    paid_total: float
    not_paid_total: float
    milestones_reached: Dict[str, bool]  # m1, m5, m25
    milestones_paid: Dict[str, bool]  # paid_m1, paid_m5, paid_m25
    payment_status_driver: str  # 'paid' | 'partial' | 'not_paid'
    action_priority_driver: str  # 'P0' | 'P1' | 'P2'
    counts: Dict[str, int]  # claims_total, claims_paid, claims_not_paid

    class Config:
        from_attributes = True


class CabinetDriversResponse(BaseModel):
    """Respuesta del endpoint de drivers cabinet"""
    status: str
    count: int
    total: int
    filters: Dict[str, Any]
    rows: List[CabinetDriverRow]


class DriverTimelineRow(BaseModel):
    """Fila de timeline de claims para un driver"""
    lead_date: date
    milestone_value: int
    expected_amount: float
    paid_flag: bool
    pay_date: Optional[date] = None
    payment_key: Optional[str] = None
    reason_code: str
    bucket_overdue: str
    evidence_level: Optional[str] = None
    ledger_driver_id_final: Optional[str] = None
    ledger_person_key_original: Optional[UUID] = None
    match_rule: Optional[str] = None
    match_confidence: Optional[str] = None
    identity_status: Optional[str] = None

    class Config:
        from_attributes = True


class DriverTimelineResponse(BaseModel):
    """Respuesta del endpoint de timeline de driver"""
    status: str
    count: int
    driver_id: Optional[str] = None
    driver_name_display: str
    rows: List[DriverTimelineRow]


# ============================================================================
# Yango Cabinet Claims For Collection Schemas
# ============================================================================

class YangoCabinetClaimsForCollectionRow(BaseModel):
    """Fila de claim desde ops.v_yango_cabinet_claims_for_collection"""
    driver_id: Optional[str] = None
    person_key: Optional[UUID] = None
    driver_name: Optional[str] = None
    milestone_value: int
    lead_date: date
    expected_amount: float
    yango_due_date: date
    days_overdue_yango: int
    overdue_bucket_yango: str
    yango_payment_status: str  # 'PAID' | 'PAID_MISAPPLIED' | 'UNPAID'
    payment_key: Optional[str] = None
    pay_date: Optional[date] = None
    reason_code: str
    match_rule: Optional[str] = None
    match_confidence: Optional[str] = None

    class Config:
        from_attributes = True


class YangoCabinetClaimsForCollectionResponse(BaseModel):
    """Respuesta del endpoint de claims for collection"""
    rows: List[YangoCabinetClaimsForCollectionRow]
    aggregates: Dict[str, Any]