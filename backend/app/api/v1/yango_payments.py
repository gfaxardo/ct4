"""
Endpoints para reconciliación de pagos Yango

Endpoints:
- GET /payments/reconciliation/summary - Resumen agregado por semana y milestone
- GET /payments/reconciliation/items - Items detallados de claims
- GET /payments/reconciliation/ledger/unmatched - Ledger sin match contra claims
- GET /payments/reconciliation/ledger/matched - Ledger con match contra claims
- GET /payments/reconciliation/driver/{driver_id} - Detalle de un conductor
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Literal, List
from datetime import date
import logging
import csv
import io

from app.db import get_db
from app.schemas.payments import (
    YangoReconciliationSummaryRow,
    YangoReconciliationSummaryResponse,
    YangoReconciliationItemRow,
    YangoReconciliationItemsResponse,
    YangoLedgerUnmatchedRow,
    CabinetPaymentEvidencePackRow,
    CabinetPaymentEvidencePackResponse,
    CabinetDriverRow,
    CabinetDriversResponse,
    DriverTimelineRow,
    DriverTimelineResponse,
    YangoLedgerUnmatchedResponse,
    YangoDriverDetailResponse,
    ClaimDetailRow,
    Claims14dRow,
    Claims14dResponse,
    Claims14dSummaryRow,
    Claims14dSummaryResponse,
    ClaimsCabinetRow,
    ClaimsCabinetResponse,
    ClaimsCabinetSummaryRow,
    ClaimsCabinetSummaryResponse,
    YangoCabinetClaimsForCollectionRow,
    YangoCabinetClaimsForCollectionResponse
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/payments/reconciliation/summary", response_model=YangoReconciliationSummaryResponse)
def get_reconciliation_summary(
    db: Session = Depends(get_db),
    week_start: Optional[date] = Query(None, description="Filtra por semana (lunes)"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone (1, 5, 25)"),
    mode: Literal['real', 'assumed'] = Query('real', description="Modo: 'real' (solo pagos confirmados) o 'assumed' (incluye asumidos)"),
    limit: int = Query(1000, ge=1, le=10000, description="Límite de resultados")
):
    """
    Obtiene resumen agregado de reconciliación de pagos Yango por semana y milestone.
    """
    # Construir query dinámico
    where_conditions = []
    params = {}
    
    if week_start:
        where_conditions.append("pay_week_start_monday = :week_start")
        params["week_start"] = week_start
    
    if milestone_value:
        where_conditions.append("milestone_value = :milestone_value")
        params["milestone_value"] = milestone_value
    
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)
    
    # Query para obtener datos agregados
    sql = f"""
        SELECT 
            pay_week_start_monday,
            milestone_value,
            SUM(expected_amount) AS amount_expected_sum,
            SUM(CASE WHEN paid_status = 'paid_confirmed' THEN expected_amount ELSE 0 END) AS amount_paid_confirmed_sum,
            SUM(CASE WHEN paid_status = 'paid_enriched' THEN expected_amount ELSE 0 END) AS amount_paid_enriched_sum,
            SUM(CASE WHEN paid_status IN ('paid_confirmed', 'paid_enriched') THEN expected_amount ELSE 0 END) AS amount_paid_total_visible,
            SUM(CASE WHEN paid_status = 'pending_active' THEN expected_amount ELSE 0 END) AS amount_pending_active_sum,
            SUM(CASE WHEN paid_status = 'pending_expired' THEN expected_amount ELSE 0 END) AS amount_pending_expired_sum,
            SUM(expected_amount) - SUM(CASE WHEN paid_status IN ('paid_confirmed', 'paid_enriched') THEN expected_amount ELSE 0 END) AS amount_diff,
            SUM(expected_amount) - SUM(CASE WHEN paid_status IN ('paid_confirmed', 'paid_enriched', 'pending_active') THEN expected_amount ELSE 0 END) AS amount_diff_assumed,
            COUNT(*) FILTER (WHERE paid_status IN ('paid_confirmed', 'paid_enriched')) AS anomalies_total,
            COUNT(*) AS count_expected,
            COUNT(*) FILTER (WHERE paid_status = 'paid_confirmed') AS count_paid_confirmed,
            COUNT(*) FILTER (WHERE paid_status = 'paid_enriched') AS count_paid_enriched,
            COUNT(*) FILTER (WHERE paid_status IN ('paid_confirmed', 'paid_enriched')) AS count_paid,
            COUNT(*) FILTER (WHERE paid_status = 'pending_active') AS count_pending_active,
            COUNT(*) FILTER (WHERE paid_status = 'pending_expired') AS count_pending_expired,
            COUNT(DISTINCT driver_id) AS count_drivers
        FROM ops.v_yango_payments_claims_cabinet_14d
        {where_clause}
        GROUP BY pay_week_start_monday, milestone_value
        ORDER BY pay_week_start_monday DESC, milestone_value ASC
        LIMIT :limit
    """
    
    params["limit"] = limit
    
    try:
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        # Convertir a modelos Pydantic
        rows = []
        for row in rows_data:
            row_dict = dict(row)
            # Agregar alias para compatibilidad
            row_dict["amount_paid_sum"] = row_dict.get("amount_paid_total_visible")
            row_dict["amount_paid_assumed"] = row_dict.get("amount_pending_active_sum")
            rows.append(YangoReconciliationSummaryRow(**row_dict))
        
        # Obtener datos de validación
        validation_query = text("""
            SELECT 
                COUNT(*) AS ledger_total_rows,
                COUNT(*) FILTER (WHERE is_paid = true) AS ledger_rows_is_paid_true,
                COUNT(*) FILTER (WHERE is_paid = true AND driver_id_final IS NULL) AS ledger_rows_is_paid_true_and_driver_id_null
            FROM ops.v_yango_payments_ledger_latest_enriched
        """)
        validation_result = db.execute(validation_query).fetchone()
        
        filters = {
            "week_start": str(week_start) if week_start else None,
            "milestone_value": milestone_value,
            "mode": mode,
            "limit": limit,
            "_validation": {
                "ledger_total_rows": validation_result.ledger_total_rows or 0,
                "ledger_rows_is_paid_true": validation_result.ledger_rows_is_paid_true or 0,
                "ledger_rows_is_paid_true_and_driver_id_null": validation_result.ledger_rows_is_paid_true_and_driver_id_null or 0
            } if validation_result else {}
        }
        
        return YangoReconciliationSummaryResponse(
            status="ok",
            count=len(rows),
            filters={k: v for k, v in filters.items() if v is not None},
            rows=rows
        )
    except Exception as e:
        logger.error(f"Error en reconciliation summary: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar resumen de reconciliación: {str(e)}"
        )


@router.get("/payments/reconciliation/items", response_model=YangoReconciliationItemsResponse)
def get_reconciliation_items(
    db: Session = Depends(get_db),
    week_start: Optional[date] = Query(None, description="Filtra por semana (lunes)"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone (1, 5, 25)"),
    driver_id: Optional[str] = Query(None, description="Filtra por driver_id"),
    paid_status: Optional[str] = Query(None, description="Filtra por paid_status"),
    limit: int = Query(1000, ge=1, le=10000, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación")
):
    """
    Obtiene items detallados de reconciliación de pagos Yango.
    """
    where_conditions = []
    params = {}
    
    if week_start:
        where_conditions.append("pay_week_start_monday = :week_start")
        params["week_start"] = week_start
    
    if milestone_value:
        where_conditions.append("milestone_value = :milestone_value")
        params["milestone_value"] = milestone_value
    
    if driver_id:
        where_conditions.append("driver_id = :driver_id")
        params["driver_id"] = driver_id
    
    if paid_status:
        where_conditions.append("paid_status = :paid_status")
        params["paid_status"] = paid_status
    
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)
    
    # Query para contar total
    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM ops.v_yango_payments_claims_cabinet_14d
        {where_clause}
    """
    
    # Query para obtener datos
    sql = f"""
        SELECT 
            driver_id,
            person_key,
            lead_date,
            pay_week_start_monday,
            milestone_value,
            expected_amount,
            currency,
            lead_date + INTERVAL '14 days' AS due_date,
            CASE 
                WHEN paid_status = 'paid_confirmed' THEN 'active'
                WHEN paid_status = 'paid_enriched' THEN 'active'
                WHEN paid_status = 'pending_active' THEN 'active'
                WHEN paid_status = 'pending_expired' THEN 'expired'
                ELSE NULL
            END AS window_status,
            paid_payment_key,
            paid_payment_key_confirmed,
            paid_payment_key_enriched,
            paid_date,
            paid_date_confirmed,
            paid_date_enriched,
            is_paid_effective,
            match_method,
            paid_status,
            identity_status,
            match_rule,
            match_confidence
        FROM ops.v_yango_payments_claims_cabinet_14d
        {where_clause}
        ORDER BY pay_week_start_monday DESC, milestone_value ASC, lead_date DESC
        LIMIT :limit OFFSET :offset
    """
    
    params["limit"] = limit
    params["offset"] = offset
    
    try:
        # Obtener total
        count_result = db.execute(text(count_sql), params).fetchone()
        total = count_result.total if count_result else 0
        
        # Obtener datos
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        rows = [YangoReconciliationItemRow(**dict(row)) for row in rows_data]
        
        filters = {
            "week_start": str(week_start) if week_start else None,
            "milestone_value": milestone_value,
            "driver_id": driver_id,
            "paid_status": paid_status,
            "limit": limit,
            "offset": offset
        }
        
        return YangoReconciliationItemsResponse(
            status="ok",
            count=len(rows),
            total=total,
            filters={k: v for k, v in filters.items() if v is not None},
            rows=rows
        )
    except Exception as e:
        logger.error(f"Error en reconciliation items: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar items de reconciliación: {str(e)}"
        )


@router.get("/payments/reconciliation/ledger/unmatched", response_model=YangoLedgerUnmatchedResponse)
def get_ledger_unmatched(
    db: Session = Depends(get_db),
    is_paid: Optional[bool] = Query(None, description="Filtra por is_paid"),
    driver_id: Optional[str] = Query(None, description="Filtra por driver_id"),
    identity_status: Optional[str] = Query(None, description="Filtra por identity_status"),
    limit: int = Query(1000, ge=1, le=10000, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación")
):
    """
    Obtiene registros del ledger que no tienen match contra claims.
    """
    where_conditions = []
    params = {}
    
    # Verificar que no tiene match contra claims
    where_conditions.append("""
        NOT EXISTS (
            SELECT 1 FROM ops.v_yango_payments_claims_cabinet_14d c
            WHERE c.driver_id = l.driver_id_final
               OR c.person_key = l.person_key_original
        )
    """)
    
    if is_paid is not None:
        where_conditions.append("l.is_paid = :is_paid")
        params["is_paid"] = is_paid
    
    if driver_id:
        where_conditions.append("l.driver_id_final = :driver_id")
        params["driver_id"] = driver_id
    
    if identity_status:
        where_conditions.append("l.identity_status = :identity_status")
        params["identity_status"] = identity_status
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Query para contar total
    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM ops.v_yango_payments_ledger_latest_enriched l
        {where_clause}
    """
    
    # Query para obtener datos
    sql = f"""
        SELECT 
            l.payment_key,
            l.pay_date,
            l.is_paid,
            l.milestone_value,
            l.driver_id_final AS driver_id,
            l.person_key_original AS person_key,
            l.raw_driver_name,
            l.driver_name_normalized,
            l.match_rule,
            l.match_confidence,
            l.latest_snapshot_at,
            l.source_pk,
            l.identity_source,
            l.identity_enriched,
            l.driver_id_final,
            l.person_key_final,
            l.identity_status
        FROM ops.v_yango_payments_ledger_latest_enriched l
        {where_clause}
        ORDER BY l.pay_date DESC, l.payment_key
        LIMIT :limit OFFSET :offset
    """
    
    params["limit"] = limit
    params["offset"] = offset
    
    try:
        # Obtener total
        count_result = db.execute(text(count_sql), params).fetchone()
        total = count_result.total if count_result else 0
        
        # Obtener datos
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        rows = [YangoLedgerUnmatchedRow(**dict(row)) for row in rows_data]
        
        filters = {
            "is_paid": is_paid,
            "driver_id": driver_id,
            "identity_status": identity_status,
            "limit": limit,
            "offset": offset
        }
        
        return YangoLedgerUnmatchedResponse(
            status="ok",
            count=len(rows),
            total=total,
            filters={k: v for k, v in filters.items() if v is not None},
            rows=rows
        )
    except Exception as e:
        logger.error(f"Error en ledger unmatched: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar ledger sin match: {str(e)}"
        )


@router.get("/payments/reconciliation/ledger/matched", response_model=YangoLedgerUnmatchedResponse)
def get_ledger_matched(
    db: Session = Depends(get_db),
    is_paid: Optional[bool] = Query(None, description="Filtra por is_paid"),
    driver_id: Optional[str] = Query(None, description="Filtra por driver_id"),
    limit: int = Query(1000, ge=1, le=10000, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación")
):
    """
    Obtiene registros del ledger que tienen match contra claims.
    """
    where_conditions = []
    params = {}
    
    # Verificar que tiene match contra claims
    where_conditions.append("""
        EXISTS (
            SELECT 1 FROM ops.v_yango_payments_claims_cabinet_14d c
            WHERE c.driver_id = l.driver_id_final
               OR c.person_key = l.person_key_original
        )
    """)
    
    if is_paid is not None:
        where_conditions.append("l.is_paid = :is_paid")
        params["is_paid"] = is_paid
    
    if driver_id:
        where_conditions.append("l.driver_id_final = :driver_id")
        params["driver_id"] = driver_id
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Query para contar total
    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM ops.v_yango_payments_ledger_latest_enriched l
        {where_clause}
    """
    
    # Query para obtener datos
    sql = f"""
        SELECT 
            l.payment_key,
            l.pay_date,
            l.is_paid,
            l.milestone_value,
            l.driver_id_final AS driver_id,
            l.person_key_original AS person_key,
            l.raw_driver_name,
            l.driver_name_normalized,
            l.match_rule,
            l.match_confidence,
            l.latest_snapshot_at,
            l.source_pk,
            l.identity_source,
            l.identity_enriched,
            l.driver_id_final,
            l.person_key_final,
            l.identity_status
        FROM ops.v_yango_payments_ledger_latest_enriched l
        {where_clause}
        ORDER BY l.pay_date DESC, l.payment_key
        LIMIT :limit OFFSET :offset
    """
    
    params["limit"] = limit
    params["offset"] = offset
    
    try:
        # Obtener total
        count_result = db.execute(text(count_sql), params).fetchone()
        total = count_result.total if count_result else 0
        
        # Obtener datos
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        rows = [YangoLedgerUnmatchedRow(**dict(row)) for row in rows_data]
        
        filters = {
            "is_paid": is_paid,
            "driver_id": driver_id,
            "limit": limit,
            "offset": offset
        }
        
        return YangoLedgerUnmatchedResponse(
            status="ok",
            count=len(rows),
            total=total,
            filters={k: v for k, v in filters.items() if v is not None},
            rows=rows
        )
    except Exception as e:
        logger.error(f"Error en ledger matched: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar ledger con match: {str(e)}"
        )


@router.get("/payments/reconciliation/driver/{driver_id}", response_model=YangoDriverDetailResponse)
def get_driver_detail(
    driver_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtiene detalle de claims y pagos para un conductor específico.
    """
    try:
        # Obtener claims del conductor
        claims_sql = text("""
            SELECT 
                milestone_value,
                expected_amount,
                currency,
                lead_date,
                lead_date + INTERVAL '14 days' AS due_date,
                pay_week_start_monday,
                paid_status,
                paid_payment_key,
                paid_date,
                is_paid_effective,
                match_method,
                identity_status,
                match_rule,
                match_confidence
            FROM ops.v_yango_payments_claims_cabinet_14d
            WHERE driver_id = :driver_id
            ORDER BY pay_week_start_monday DESC, milestone_value ASC, lead_date DESC
        """)
        
        claims_result = db.execute(claims_sql, {"driver_id": driver_id})
        claims_data = claims_result.mappings().all()
        
        claims = [ClaimDetailRow(**dict(row)) for row in claims_data]
        
        # Calcular resumen
        total_expected = sum(c.expected_amount or 0 for c in claims)
        total_paid = sum(c.expected_amount or 0 for c in claims if c.is_paid_effective)
        count_paid = sum(1 for c in claims if c.is_paid_effective)
        count_pending_active = sum(1 for c in claims if c.paid_status == 'pending_active')
        count_pending_expired = sum(1 for c in claims if c.paid_status == 'pending_expired')
        
        # Obtener person_key si existe
        person_key_sql = text("""
            SELECT DISTINCT person_key
            FROM ops.v_yango_payments_claims_cabinet_14d
            WHERE driver_id = :driver_id
            LIMIT 1
        """)
        person_key_result = db.execute(person_key_sql, {"driver_id": driver_id}).fetchone()
        person_key = person_key_result.person_key if person_key_result else None
        
        summary = {
            "total_expected": total_expected,
            "total_paid": total_paid,
            "count_paid": count_paid,
            "count_pending_active": count_pending_active,
            "count_pending_expired": count_pending_expired
        }
        
        return YangoDriverDetailResponse(
            status="ok",
            driver_id=driver_id,
            person_key=person_key,
            claims=claims,
            summary=summary
        )
    except Exception as e:
        logger.error(f"Error en driver detail: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar detalle del conductor: {str(e)}"
        )


@router.get("/payments/claims_14d", response_model=Claims14dResponse)
def get_claims_14d(
    db: Session = Depends(get_db),
    week_start: Optional[date] = Query(None, description="Filtra por semana (pay_week_start_monday)"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone (1, 5, 25)"),
    paid_status: Optional[str] = Query(None, description="Filtra por paid_status (paid_confirmed, paid_enriched, pending_active, pending_expired)"),
    window_status: Optional[str] = Query(None, description="Filtra por window_status (active, expired)"),
    limit: int = Query(1000, ge=1, le=10000, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación")
):
    """
    Obtiene claims desde ops.v_yango_payments_claims_cabinet_14d.
    Fuente única: vista SQL, sin inferencias en frontend.
    """
    where_conditions = []
    params = {}
    
    if week_start:
        where_conditions.append("pay_week_start_monday = :week_start")
        params["week_start"] = week_start
    
    if milestone_value:
        where_conditions.append("milestone_value = :milestone_value")
        params["milestone_value"] = milestone_value
    
    if paid_status:
        where_conditions.append("paid_status = :paid_status")
        params["paid_status"] = paid_status
    
    if window_status:
        where_conditions.append("window_status = :window_status")
        params["window_status"] = window_status
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Query para contar total
    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM ops.v_yango_payments_claims_cabinet_14d
        {where_clause}
    """
    
    # Query para obtener datos
    sql = f"""
        SELECT 
            driver_id,
            person_key,
            lead_date,
            pay_week_start_monday,
            milestone_value,
            expected_amount,
            currency,
            due_date,
            window_status,
            paid_status,
            is_paid_confirmed,
            is_paid_enriched,
            paid_date,
            identity_status,
            match_rule,
            match_confidence,
            paid_payment_key,
            paid_payment_key_confirmed,
            paid_payment_key_enriched
        FROM ops.v_yango_payments_claims_cabinet_14d
        {where_clause}
        ORDER BY pay_week_start_monday DESC, milestone_value ASC, lead_date DESC
        LIMIT :limit OFFSET :offset
    """
    
    params["limit"] = limit
    params["offset"] = offset
    
    try:
        # Obtener total
        count_result = db.execute(text(count_sql), params).fetchone()
        total = count_result.total if count_result else 0
        
        # Obtener datos
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        # Convertir filas y manejar tipos (person_key puede venir como string desde SQL)
        rows = []
        for row_dict in rows_data:
            row_data = dict(row_dict)
            # Convertir person_key de string a UUID si existe
            if row_data.get('person_key') and isinstance(row_data['person_key'], str):
                try:
                    from uuid import UUID
                    row_data['person_key'] = UUID(row_data['person_key'])
                except (ValueError, TypeError):
                    row_data['person_key'] = None
            rows.append(Claims14dRow(**row_data))
        
        filters = {
            "week_start": str(week_start) if week_start else None,
            "milestone_value": milestone_value,
            "paid_status": paid_status,
            "window_status": window_status,
            "limit": limit,
            "offset": offset
        }
        
        return Claims14dResponse(
            status="ok",
            count=len(rows),
            total=total,
            filters={k: v for k, v in filters.items() if v is not None},
            rows=rows
        )
    except Exception as e:
        logger.error(f"Error en claims 14d: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar claims 14d: {str(e)}"
        )


@router.get("/payments/claims_14d/summary", response_model=Claims14dSummaryResponse)
def get_claims_14d_summary(
    db: Session = Depends(get_db),
    week_start: Optional[date] = Query(None, description="Filtra por semana (pay_week_start_monday)"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone (1, 5, 25)"),
    paid_status: Optional[str] = Query(None, description="Filtra por paid_status"),
    window_status: Optional[str] = Query(None, description="Filtra por window_status"),
    limit: int = Query(1000, ge=1, le=10000, description="Límite de resultados")
):
    """
    Obtiene resumen agregado de claims 14d por semana y milestone.
    """
    where_conditions = []
    params = {}
    
    if week_start:
        where_conditions.append("pay_week_start_monday = :week_start")
        params["week_start"] = week_start
    
    if milestone_value:
        where_conditions.append("milestone_value = :milestone_value")
        params["milestone_value"] = milestone_value
    
    if paid_status:
        where_conditions.append("paid_status = :paid_status")
        params["paid_status"] = paid_status
    
    if window_status:
        where_conditions.append("window_status = :window_status")
        params["window_status"] = window_status
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    sql = f"""
        SELECT 
            pay_week_start_monday,
            milestone_value,
            COALESCE(SUM(expected_amount), 0) AS expected_amount_sum,
            COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'paid_confirmed'), 0) AS paid_confirmed_amount_sum,
            COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'paid_enriched'), 0) AS paid_enriched_amount_sum,
            COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'pending_active'), 0) AS pending_active_amount_sum,
            COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'pending_expired'), 0) AS pending_expired_amount_sum,
            COUNT(*) AS expected_count,
            COUNT(*) FILTER (WHERE paid_status = 'paid_confirmed') AS paid_confirmed_count,
            COUNT(*) FILTER (WHERE paid_status = 'paid_enriched') AS paid_enriched_count,
            COUNT(*) FILTER (WHERE paid_status = 'pending_active') AS pending_active_count,
            COUNT(*) FILTER (WHERE paid_status = 'pending_expired') AS pending_expired_count
        FROM ops.v_yango_payments_claims_cabinet_14d
        {where_clause}
        GROUP BY pay_week_start_monday, milestone_value
        ORDER BY pay_week_start_monday DESC, milestone_value ASC
        LIMIT :limit
    """
    
    params["limit"] = limit
    
    try:
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        # Convertir filas y manejar tipos
        rows = []
        for row_dict in rows_data:
            row_data = dict(row_dict)
            # Asegurar que los valores NULL de SUM sean 0
            for key in ['expected_amount_sum', 'paid_confirmed_amount_sum', 'paid_enriched_amount_sum', 
                       'pending_active_amount_sum', 'pending_expired_amount_sum']:
                if row_data.get(key) is None:
                    row_data[key] = 0.0
            rows.append(Claims14dSummaryRow(**row_data))
        
        filters = {
            "week_start": str(week_start) if week_start else None,
            "milestone_value": milestone_value,
            "paid_status": paid_status,
            "window_status": window_status,
            "limit": limit
        }
        
        return Claims14dSummaryResponse(
            status="ok",
            count=len(rows),
            filters={k: v for k, v in filters.items() if v is not None},
            rows=rows
        )
    except Exception as e:
        logger.error(f"Error en claims 14d summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar resumen de claims 14d: {str(e)}"
        )


@router.get("/payments/claims_cabinet", response_model=ClaimsCabinetResponse)
def get_claims_cabinet(
    db: Session = Depends(get_db),
    week_start: Optional[date] = Query(None, description="Filtra por semana (pay_week_start_monday derivada de lead_date)"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone (1, 5, 25)"),
    payment_status: Optional[str] = Query(None, description="Filtra por payment_status ('paid' o 'not_paid')"),
    limit: int = Query(1000, ge=1, le=10000, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación")
):
    """
    Obtiene claims desde ops.v_claims_payment_status_cabinet.
    Fuente única: vista SQL, sin inferencias en frontend.
    Responde: "Para cada conductor que entró por cabinet y alcanzó un milestone, ¿nos pagaron o no?"
    """
    where_conditions = []
    params = {}
    
    if week_start:
        # Calcular pay_week_start_monday desde lead_date
        where_conditions.append("date_trunc('week', lead_date)::date = :week_start")
        params["week_start"] = week_start
    
    if milestone_value:
        where_conditions.append("milestone_value = :milestone_value")
        params["milestone_value"] = milestone_value
    
    if payment_status:
        where_conditions.append("payment_status = :payment_status")
        params["payment_status"] = payment_status
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Query para contar total
    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM ops.v_claims_payment_status_cabinet
        {where_clause}
    """
    
    # Query para obtener datos
    sql = f"""
        SELECT 
            driver_id,
            person_key,
            milestone_value,
            lead_date,
            due_date,
            expected_amount,
            paid_flag,
            paid_date,
            payment_key,
            payment_identity_status,
            payment_match_rule,
            payment_match_confidence,
            payment_status,
            payment_reason
        FROM ops.v_claims_payment_status_cabinet
        {where_clause}
        ORDER BY lead_date DESC, milestone_value ASC
        LIMIT :limit OFFSET :offset
    """
    
    params["limit"] = limit
    params["offset"] = offset
    
    try:
        # Obtener total
        count_result = db.execute(text(count_sql), params).fetchone()
        total = count_result.total if count_result else 0
        
        # Obtener datos
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        # Convertir filas y manejar tipos (person_key puede venir como string desde SQL)
        rows = []
        for row_dict in rows_data:
            row_data = dict(row_dict)
            # Convertir person_key de string a UUID si existe
            if row_data.get('person_key') and isinstance(row_data['person_key'], str):
                try:
                    from uuid import UUID
                    row_data['person_key'] = UUID(row_data['person_key'])
                except (ValueError, TypeError):
                    row_data['person_key'] = None
            rows.append(ClaimsCabinetRow(**row_data))
        
        filters = {
            "week_start": str(week_start) if week_start else None,
            "milestone_value": milestone_value,
            "payment_status": payment_status,
            "limit": limit,
            "offset": offset
        }
        
        return ClaimsCabinetResponse(
            status="ok",
            count=len(rows),
            total=total,
            filters={k: v for k, v in filters.items() if v is not None},
            rows=rows
        )
    except Exception as e:
        logger.error(f"Error en claims cabinet: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar claims cabinet: {str(e)}"
        )


@router.get("/payments/claims_cabinet/summary", response_model=ClaimsCabinetSummaryResponse)
def get_claims_cabinet_summary(
    db: Session = Depends(get_db),
    week_start: Optional[date] = Query(None, description="Filtra por semana (pay_week_start_monday derivada de lead_date)"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone (1, 5, 25)"),
    payment_status: Optional[str] = Query(None, description="Filtra por payment_status ('paid' o 'not_paid')"),
    limit: int = Query(1000, ge=1, le=10000, description="Límite de resultados")
):
    """
    Obtiene resumen agregado de claims cabinet por semana y milestone.
    Agregación basada en ops.v_claims_payment_status_cabinet.
    """
    where_conditions = []
    params = {}
    
    if week_start:
        # Calcular pay_week_start_monday desde lead_date
        where_conditions.append("date_trunc('week', lead_date)::date = :week_start")
        params["week_start"] = week_start
    
    if milestone_value:
        where_conditions.append("milestone_value = :milestone_value")
        params["milestone_value"] = milestone_value
    
    if payment_status:
        where_conditions.append("payment_status = :payment_status")
        params["payment_status"] = payment_status
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    sql = f"""
        SELECT 
            date_trunc('week', lead_date)::date AS pay_week_start_monday,
            milestone_value,
            COALESCE(SUM(expected_amount), 0) AS expected_amount_sum,
            COALESCE(SUM(expected_amount) FILTER (WHERE paid_flag = true), 0) AS paid_amount_sum,
            COALESCE(SUM(expected_amount) FILTER (WHERE paid_flag = false), 0) AS not_paid_amount_sum,
            COUNT(*) AS expected_count,
            COUNT(*) FILTER (WHERE paid_flag = true) AS paid_count,
            COUNT(*) FILTER (WHERE paid_flag = false) AS not_paid_count
        FROM ops.v_claims_payment_status_cabinet
        {where_clause}
        GROUP BY date_trunc('week', lead_date)::date, milestone_value
        ORDER BY pay_week_start_monday DESC, milestone_value ASC
        LIMIT :limit
    """
    
    params["limit"] = limit
    
    try:
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        # Convertir filas y manejar tipos
        rows = []
        for row_dict in rows_data:
            row_data = dict(row_dict)
            # Asegurar que los valores NULL de SUM sean 0
            for key in ['expected_amount_sum', 'paid_amount_sum', 'not_paid_amount_sum']:
                if row_data.get(key) is None:
                    row_data[key] = 0.0
            rows.append(ClaimsCabinetSummaryRow(**row_data))
        
        filters = {
            "week_start": str(week_start) if week_start else None,
            "milestone_value": milestone_value,
            "payment_status": payment_status,
            "limit": limit
        }
        
        return ClaimsCabinetSummaryResponse(
            status="ok",
            count=len(rows),
            filters={k: v for k, v in filters.items() if v is not None},
            rows=rows
        )
    except Exception as e:
        logger.error(f"Error en claims cabinet summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar resumen de claims cabinet: {str(e)}"
        )


@router.get("/payments/cabinet/evidence-pack", response_model=CabinetPaymentEvidencePackResponse)
def get_cabinet_payment_evidence_pack(
    db: Session = Depends(get_db),
    week_start: Optional[date] = Query(None, description="Filtra por semana (pay_week_start_monday derivada de lead_date)"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone (1, 5, 25)"),
    payment_status: Optional[str] = Query(None, description="Filtra por payment_status ('paid' o 'not_paid')"),
    reason_code: Optional[str] = Query(None, description="Filtra por reason_code"),
    action_priority: Optional[str] = Query(None, description="Filtra por action_priority"),
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000, description="Límite de resultados")
):
    """
    Obtiene Evidence Pack para responder a Yango con evidencia clara de la relación claim-payment.
    Combina claims canónicos con datos del ledger para proporcionar trazabilidad completa.
    """
    where_conditions = []
    params = {}
    
    if week_start:
        # Calcular pay_week_start_monday desde lead_date
        where_conditions.append("date_trunc('week', lead_date)::date = :week_start")
        params["week_start"] = week_start
    
    if milestone_value:
        where_conditions.append("claim_milestone_value = :milestone_value")
        params["milestone_value"] = milestone_value
    
    if payment_status:
        where_conditions.append("payment_status = :payment_status")
        params["payment_status"] = payment_status
    
    if reason_code:
        where_conditions.append("reason_code = :reason_code")
        params["reason_code"] = reason_code
    
    if action_priority:
        where_conditions.append("action_priority = :action_priority")
        params["action_priority"] = action_priority
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Query para obtener total
    count_sql = f"""
        SELECT COUNT(*) 
        FROM ops.v_cabinet_payment_evidence_pack
        {where_clause}
    """
    
    params_for_count = {k: v for k, v in params.items()}
    total_result = db.execute(text(count_sql), params_for_count)
    total = total_result.scalar() or 0
    
    # Query para obtener datos
    sql = f"""
        SELECT 
            claim_driver_id,
            claim_person_key,
            claim_milestone_value,
            lead_date,
            due_date,
            expected_amount,
            payment_status,
            reason_code,
            action_priority,
            paid_flag,
            payment_key,
            pay_date,
            ledger_driver_id_final,
            ledger_person_key_original,
            ledger_milestone_value,
            match_rule,
            match_confidence,
            identity_status,
            milestone_paid,
            evidence_level
        FROM ops.v_cabinet_payment_evidence_pack
        {where_clause}
        ORDER BY lead_date DESC, claim_milestone_value ASC
        LIMIT :limit OFFSET :offset
    """
    
    params["limit"] = limit
    params["offset"] = skip
    
    # Query para agregados
    aggregates_sql = f"""
        SELECT 
            evidence_level,
            reason_code,
            COUNT(*) AS count,
            SUM(expected_amount) AS amount_sum
        FROM ops.v_cabinet_payment_evidence_pack
        {where_clause}
        GROUP BY evidence_level, reason_code
        ORDER BY evidence_level, reason_code
    """
    
    try:
        # Obtener rows
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        rows = []
        for row_dict in rows_data:
            row_data = dict(row_dict)
            rows.append(CabinetPaymentEvidencePackRow(**row_data))
        
        # Obtener agregados
        aggregates_result = db.execute(text(aggregates_sql), params_for_count)
        aggregates_data = aggregates_result.mappings().all()
        
        aggregates = {
            "by_evidence_level": {},
            "by_reason_code": {},
            "by_evidence_level_and_reason_code": []
        }
        
        for agg_dict in aggregates_data:
            agg_data = dict(agg_dict)
            evidence_level = agg_data.get("evidence_level")
            reason_code_agg = agg_data.get("reason_code")
            count = agg_data.get("count", 0)
            amount_sum = float(agg_data.get("amount_sum", 0))
            
            # Por evidence_level
            if evidence_level not in aggregates["by_evidence_level"]:
                aggregates["by_evidence_level"][evidence_level] = {"count": 0, "amount_sum": 0.0}
            aggregates["by_evidence_level"][evidence_level]["count"] += count
            aggregates["by_evidence_level"][evidence_level]["amount_sum"] += amount_sum
            
            # Por reason_code
            if reason_code_agg not in aggregates["by_reason_code"]:
                aggregates["by_reason_code"][reason_code_agg] = {"count": 0, "amount_sum": 0.0}
            aggregates["by_reason_code"][reason_code_agg]["count"] += count
            aggregates["by_reason_code"][reason_code_agg]["amount_sum"] += amount_sum
            
            # Combinado
            aggregates["by_evidence_level_and_reason_code"].append({
                "evidence_level": evidence_level,
                "reason_code": reason_code_agg,
                "count": count,
                "amount_sum": amount_sum
            })
        
        filters = {
            "week_start": str(week_start) if week_start else None,
            "milestone_value": milestone_value,
            "payment_status": payment_status,
            "reason_code": reason_code,
            "action_priority": action_priority,
            "skip": skip,
            "limit": limit
        }
        
        return CabinetPaymentEvidencePackResponse(
            status="ok",
            count=len(rows),
            total=total,
            filters={k: v for k, v in filters.items() if v is not None},
            aggregates=aggregates,
            rows=rows
        )
    except Exception as e:
        logger.error(f"Error en evidence pack: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar evidence pack: {str(e)}"
        )


@router.get("/payments/cabinet/drivers", response_model=CabinetDriversResponse)
def get_cabinet_drivers(
    db: Session = Depends(get_db),
    week_start: Optional[date] = Query(None, description="Filtra por semana (pay_week_start_monday derivada de lead_date)"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone (1, 5, 25)"),
    payment_status_driver: Optional[str] = Query(None, description="Filtra por payment_status_driver ('paid', 'partial', 'not_paid')"),
    action_priority: Optional[str] = Query(None, description="Filtra por action_priority_driver ('P0', 'P1', 'P2')"),
    skip: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000, description="Límite de resultados")
):
    """
    Obtiene drivers agrupados desde claims cabinet (driver-first view).
    Agrupa por driver_id (o person_key si driver_id es null).
    """
    where_conditions = []
    params = {}
    
    if week_start:
        where_conditions.append("date_trunc('week', lead_date)::date = :week_start")
        params["week_start"] = week_start
    
    if milestone_value:
        where_conditions.append("milestone_value = :milestone_value")
        params["milestone_value"] = milestone_value
    
    where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
    
    # Query principal: agrupar por driver_id/person_key
    sql = f"""
        WITH driver_claims AS (
            SELECT 
                COALESCE(driver_id, 'person_' || person_key::text) AS driver_key,
                driver_id,
                person_key,
                lead_date,
                milestone_value,
                expected_amount,
                paid_flag,
                bucket_overdue,
                reason_code,
                action_priority
            FROM ops.v_claims_payment_status_cabinet
            {where_clause}
        ),
        driver_agg AS (
            SELECT 
                driver_key,
                MAX(driver_id) AS driver_id,
                (array_agg(DISTINCT person_key) FILTER (WHERE person_key IS NOT NULL))[1] AS person_key,
                MIN(lead_date) AS lead_date_min,
                MAX(lead_date) AS lead_date_max,
                SUM(expected_amount) AS expected_total,
                SUM(CASE WHEN paid_flag THEN expected_amount ELSE 0 END) AS paid_total,
                SUM(CASE WHEN NOT paid_flag THEN expected_amount ELSE 0 END) AS not_paid_total,
                COUNT(*) AS claims_total,
                SUM(CASE WHEN paid_flag THEN 1 ELSE 0 END) AS claims_paid,
                SUM(CASE WHEN NOT paid_flag THEN 1 ELSE 0 END) AS claims_not_paid,
                BOOL_OR(milestone_value = 1) AS milestone_1_reached,
                BOOL_OR(milestone_value = 5) AS milestone_5_reached,
                BOOL_OR(milestone_value = 25) AS milestone_25_reached,
                BOOL_OR(milestone_value = 1 AND paid_flag) AS milestone_1_paid,
                BOOL_OR(milestone_value = 5 AND paid_flag) AS milestone_5_paid,
                BOOL_OR(milestone_value = 25 AND paid_flag) AS milestone_25_paid,
                BOOL_OR(bucket_overdue IN ('3_15_30', '4_31_60', '5_60_plus') AND NOT paid_flag) AS has_p0_priority,
                BOOL_OR(reason_code = 'payment_found_other_milestone') AS has_p1_priority
            FROM driver_claims
            GROUP BY driver_key
        ),
        driver_names AS (
            SELECT DISTINCT ON (da.driver_id)
                da.driver_id,
                COALESCE(
                    -- Prioridad 1: nombre del ledger
                    (SELECT l.raw_driver_name 
                     FROM ops.v_yango_payments_ledger_latest_enriched l 
                     WHERE l.driver_id_final = da.driver_id 
                       AND l.raw_driver_name IS NOT NULL 
                     LIMIT 1),
                    -- Prioridad 2: nombre de tabla drivers
                    (SELECT d.full_name 
                     FROM public.drivers d 
                     WHERE d.driver_id = da.driver_id 
                       AND d.full_name IS NOT NULL 
                     LIMIT 1),
                    -- Fallback
                    'Sin Nombre (' || LEFT(da.driver_id, 8) || '...)'
                ) AS driver_name_display
            FROM driver_agg da
            WHERE da.driver_id IS NOT NULL
        )
        SELECT 
            da.driver_id,
            da.person_key,
            COALESCE(dn.driver_name_display, 'Sin Nombre') AS driver_name_display,
            da.lead_date_min,
            da.lead_date_max,
            da.expected_total,
            da.paid_total,
            da.not_paid_total,
            jsonb_build_object(
                'm1', da.milestone_1_reached,
                'm5', da.milestone_5_reached,
                'm25', da.milestone_25_reached
            ) AS milestones_reached,
            jsonb_build_object(
                'paid_m1', da.milestone_1_paid,
                'paid_m5', da.milestone_5_paid,
                'paid_m25', da.milestone_25_paid
            ) AS milestones_paid,
            CASE 
                WHEN da.claims_not_paid = 0 THEN 'paid'
                WHEN da.claims_paid > 0 THEN 'partial'
                ELSE 'not_paid'
            END AS payment_status_driver,
            CASE 
                WHEN da.has_p0_priority THEN 'P0'
                WHEN da.has_p1_priority THEN 'P1'
                ELSE 'P2'
            END AS action_priority_driver,
            jsonb_build_object(
                'claims_total', da.claims_total,
                'claims_paid', da.claims_paid,
                'claims_not_paid', da.claims_not_paid
            ) AS counts
        FROM driver_agg da
        LEFT JOIN driver_names dn ON dn.driver_id = da.driver_id
        ORDER BY da.lead_date_min DESC
        LIMIT :limit OFFSET :offset
    """
    
    params["limit"] = limit
    params["offset"] = skip
    
    # Filtros adicionales después de la agregación
    filter_conditions = []
    if payment_status_driver:
        filter_conditions.append("payment_status_driver = :payment_status_driver")
        params["payment_status_driver"] = payment_status_driver
    
    if action_priority:
        filter_conditions.append("action_priority_driver = :action_priority")
        params["action_priority"] = action_priority
    
    if filter_conditions:
        sql = f"SELECT * FROM ({sql}) sub WHERE {' AND '.join(filter_conditions)}"
    
    # Query para obtener total (aplicar mismos filtros)
    count_base_sql = f"""
        WITH driver_claims AS (
            SELECT 
                COALESCE(driver_id, 'person_' || person_key::text) AS driver_key,
                driver_id,
                milestone_value,
                expected_amount,
                paid_flag,
                bucket_overdue,
                reason_code
            FROM ops.v_claims_payment_status_cabinet
            {where_clause}
        ),
        driver_agg AS (
            SELECT 
                driver_key,
                COUNT(*) AS claims_total,
                SUM(CASE WHEN paid_flag THEN 1 ELSE 0 END) AS claims_paid,
                SUM(CASE WHEN NOT paid_flag THEN 1 ELSE 0 END) AS claims_not_paid,
                BOOL_OR(bucket_overdue IN ('3_15_30', '4_31_60', '5_60_plus') AND NOT paid_flag) AS has_p0_priority,
                BOOL_OR(reason_code = 'payment_found_other_milestone') AS has_p1_priority,
                CASE 
                    WHEN SUM(CASE WHEN NOT paid_flag THEN 1 ELSE 0 END) = 0 THEN 'paid'
                    WHEN SUM(CASE WHEN paid_flag THEN 1 ELSE 0 END) > 0 THEN 'partial'
                    ELSE 'not_paid'
                END AS payment_status_driver,
                CASE 
                    WHEN BOOL_OR(bucket_overdue IN ('3_15_30', '4_31_60', '5_60_plus') AND NOT paid_flag) THEN 'P0'
                    WHEN BOOL_OR(reason_code = 'payment_found_other_milestone') THEN 'P1'
                    ELSE 'P2'
                END AS action_priority_driver
            FROM driver_claims
            GROUP BY driver_key
        )
        SELECT * FROM driver_agg
    """
    
    count_sql = f"SELECT COUNT(*) FROM ({count_base_sql}) sub"
    if filter_conditions:
        count_sql = f"SELECT COUNT(*) FROM ({count_base_sql}) sub WHERE {' AND '.join(filter_conditions)}"
    
    try:
        # #region agent log - Diagnóstico: ver datos RAW de la vista antes de agregación
        try:
            debug_drivers = ['b264635aea6c41c7b14b481b02d8cb09', '88881990913f4b8181ff342c99635452', '3d809fc2cca64071a46dabe3223e314c']
            debug_sql = """
                SELECT 
                    driver_id,
                    milestone_value,
                    COUNT(*) AS n_rows,
                    SUM(expected_amount) AS sum_expected,
                    ARRAY_AGG(expected_amount ORDER BY lead_date) AS expected_amounts,
                    ARRAY_AGG(lead_date ORDER BY lead_date) AS lead_dates
                FROM ops.v_claims_payment_status_cabinet
                WHERE driver_id = ANY(:driver_ids)
                GROUP BY driver_id, milestone_value
                ORDER BY driver_id, milestone_value
            """
            debug_result = db.execute(text(debug_sql), {"driver_ids": debug_drivers})
            debug_rows = debug_result.mappings().all()
            import json
            from datetime import datetime
            log_path = r'c:\Users\Pc\Documents\Cursor Proyectos\ct4\.cursor\debug.log'
            with open(log_path, 'a', encoding='utf-8') as f:
                for row in debug_rows:
                    log_entry = {
                        'location': 'yango_payments.py:1340',
                        'message': 'Debug: vista raw data por milestone',
                        'data': {
                            'driver_id': str(row.driver_id),
                            'milestone_value': int(row.milestone_value),
                            'n_rows': int(row.n_rows),
                            'sum_expected': float(row.sum_expected),
                            'expected_amounts': [float(x) for x in row.expected_amounts],
                            'lead_dates': [str(d) for d in row.lead_dates]
                        },
                        'timestamp': int(datetime.now().timestamp() * 1000),
                        'sessionId': 'debug-session',
                        'hypothesisId': 'A'
                    }
                    f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            pass  # Ignorar errores en debug
        # #endregion
        
        # Obtener total
        count_params = {k: v for k, v in params.items() if k in ['week_start', 'milestone_value', 'payment_status_driver', 'action_priority']}
        total_result = db.execute(text(count_sql), count_params)
        total = total_result.scalar() or 0
        
        # Obtener rows
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        # #region agent log - Diagnóstico: ver expected_total después de agregación
        try:
            import json
            from datetime import datetime
            debug_drivers = ['b264635aea6c41c7b14b481b02d8cb09', '88881990913f4b8181ff342c99635452', '3d809fc2cca64071a46dabe3223e314c']
            log_path = r'c:\Users\Pc\Documents\Cursor Proyectos\ct4\.cursor\debug.log'
            with open(log_path, 'a', encoding='utf-8') as f:
                for row_dict in rows_data:
                    row_data = dict(row_dict)
                    driver_id_val = row_data.get('driver_id')
                    if driver_id_val in debug_drivers:
                        counts_dict = row_data.get('counts', {}) if isinstance(row_data.get('counts'), dict) else {}
                        log_entry = {
                            'location': 'yango_payments.py:1365',
                            'message': 'Debug: expected_total después de agregación',
                            'data': {
                                'driver_id': str(driver_id_val),
                                'expected_total': float(row_data.get('expected_total', 0)),
                                'claims_total': int(counts_dict.get('claims_total', 0))
                            },
                            'timestamp': int(datetime.now().timestamp() * 1000),
                            'sessionId': 'debug-session',
                            'hypothesisId': 'B'
                        }
                        f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            pass  # Ignorar errores en debug
        # #endregion
        
        rows = []
        for row_dict in rows_data:
            row_data = dict(row_dict)
            # Convertir JSONB a dict
            row_data['milestones_reached'] = dict(row_data.get('milestones_reached', {}))
            row_data['milestones_paid'] = dict(row_data.get('milestones_paid', {}))
            row_data['counts'] = dict(row_data.get('counts', {}))
            rows.append(CabinetDriverRow(**row_data))
        
        filters = {
            "week_start": str(week_start) if week_start else None,
            "milestone_value": milestone_value,
            "payment_status_driver": payment_status_driver,
            "action_priority": action_priority,
            "skip": skip,
            "limit": limit
        }
        
        return CabinetDriversResponse(
            status="ok",
            count=len(rows),
            total=total,
            filters={k: v for k, v in filters.items() if v is not None},
            rows=rows
        )
    except Exception as e:
        logger.error(f"Error en cabinet drivers: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar drivers cabinet: {str(e)}"
        )


@router.get("/payments/cabinet/driver/{driver_id}/timeline", response_model=DriverTimelineResponse)
def get_driver_timeline(
    driver_id: str,
    db: Session = Depends(get_db),
    include_evidence: bool = Query(False, description="Incluir campos de evidencia")
):
    """
    Obtiene timeline de claims para un driver específico, ordenado por lead_date.
    """
    # Obtener nombre del driver
    name_sql = text("""
        SELECT COALESCE(
            (SELECT l.raw_driver_name 
             FROM ops.v_yango_payments_ledger_latest_enriched l 
             WHERE l.driver_id_final = :driver_id 
               AND l.raw_driver_name IS NOT NULL 
             LIMIT 1),
            (SELECT d.full_name 
             FROM public.drivers d 
             WHERE d.driver_id = :driver_id 
               AND d.full_name IS NOT NULL 
             LIMIT 1),
            'Sin Nombre (' || LEFT(:driver_id, 8) || '...)'
        ) AS driver_name_display
    """)
    
    try:
        name_result = db.execute(name_sql, {"driver_id": driver_id})
        name_row = name_result.fetchone()
        driver_name_display = name_row[0] if name_row else f'Sin Nombre ({driver_id[:8]}...)'
    except:
        driver_name_display = f'Sin Nombre ({driver_id[:8]}...)'
    
    # Query para timeline
    if include_evidence:
        sql = """
            SELECT 
                c.lead_date,
                c.milestone_value,
                c.expected_amount,
                c.paid_flag,
                c.paid_date AS pay_date,
                c.payment_key,
                c.reason_code,
                c.bucket_overdue,
                e.evidence_level,
                e.ledger_driver_id_final,
                e.ledger_person_key_original,
                e.match_rule,
                e.match_confidence,
                e.identity_status
            FROM ops.v_claims_payment_status_cabinet c
            LEFT JOIN ops.v_cabinet_payment_evidence_pack e
                ON e.claim_driver_id = c.driver_id
                AND e.claim_milestone_value = c.milestone_value
            WHERE c.driver_id = :driver_id
            ORDER BY c.lead_date ASC, c.milestone_value ASC
        """
    else:
        sql = """
            SELECT 
                lead_date,
                milestone_value,
                expected_amount,
                paid_flag,
                paid_date AS pay_date,
                payment_key,
                reason_code,
                bucket_overdue,
                NULL AS evidence_level,
                NULL AS ledger_driver_id_final,
                NULL AS ledger_person_key_original,
                NULL AS match_rule,
                NULL AS match_confidence,
                NULL AS identity_status
            FROM ops.v_claims_payment_status_cabinet
            WHERE driver_id = :driver_id
            ORDER BY lead_date ASC, milestone_value ASC
        """
    
    try:
        result = db.execute(text(sql), {"driver_id": driver_id})
        rows_data = result.mappings().all()
        
        rows = []
        for row_dict in rows_data:
            row_data = dict(row_dict)
            rows.append(DriverTimelineRow(**row_data))
        
        return DriverTimelineResponse(
            status="ok",
            count=len(rows),
            driver_id=driver_id,
            driver_name_display=driver_name_display,
            rows=rows
        )
    except Exception as e:
        logger.error(f"Error en driver timeline: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar timeline del driver: {str(e)}"
        )


@router.get("/payments/yango/cabinet/claims", response_model=YangoCabinetClaimsForCollectionResponse)
def get_yango_cabinet_claims_for_collection(
    db: Session = Depends(get_db),
    payment_status: Optional[str] = Query(None, description="Filtra por payment_status (UNPAID,PAID_MISAPPLIED,PAID). Default: UNPAID,PAID_MISAPPLIED"),
    overdue_bucket: Optional[str] = Query(None, description="Filtra por overdue_bucket_yango"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone_value (1, 5, 25)"),
    date_from: Optional[date] = Query(None, description="Filtra por lead_date desde"),
    date_to: Optional[date] = Query(None, description="Filtra por lead_date hasta"),
    search: Optional[str] = Query(None, description="Busca en driver_name o driver_id"),
    limit: int = Query(10000, ge=1, le=50000, description="Límite de resultados")
):
    """
    Obtiene claims desde ops.v_yango_cabinet_claims_for_collection para cobro a Yango.
    Por defecto muestra UNPAID y PAID_MISAPPLIED.
    """
    try:
        # Construir WHERE conditions
        where_conditions = []
        params = {}
        
        # Filtro por payment_status (default: UNPAID,PAID_MISAPPLIED)
        if payment_status:
            status_list = [s.strip() for s in payment_status.split(',')]
            where_conditions.append("yango_payment_status = ANY(:payment_status)")
            params["payment_status"] = status_list
        else:
            # Default: UNPAID,PAID_MISAPPLIED
            where_conditions.append("yango_payment_status = ANY(:payment_status)")
            params["payment_status"] = ['UNPAID', 'PAID_MISAPPLIED']
        
        if overdue_bucket:
            where_conditions.append("overdue_bucket_yango = :overdue_bucket")
            params["overdue_bucket"] = overdue_bucket
        
        if milestone_value:
            where_conditions.append("milestone_value = :milestone_value")
            params["milestone_value"] = milestone_value
        
        if date_from:
            where_conditions.append("lead_date >= :date_from")
            params["date_from"] = date_from
        
        if date_to:
            where_conditions.append("lead_date <= :date_to")
            params["date_to"] = date_to
        
        if search:
            where_conditions.append("(driver_name ILIKE :search OR driver_id::text ILIKE :search)")
            params["search"] = f"%{search}%"
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Query para obtener datos
        sql = f"""
            SELECT 
                driver_id,
                person_key,
                driver_name,
                milestone_value,
                lead_date,
                expected_amount,
                yango_due_date,
                days_overdue_yango,
                overdue_bucket_yango,
                yango_payment_status,
                payment_key,
                pay_date,
                reason_code,
                match_rule,
                match_confidence
            FROM ops.v_yango_cabinet_claims_for_collection
            {where_clause}
            ORDER BY days_overdue_yango DESC, lead_date DESC
            LIMIT :limit
        """
        
        params["limit"] = limit
        
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        # Calcular agregados
        aggregates = {
            "total_rows": len(rows_data),
            "total_amount": sum(float(row.expected_amount) for row in rows_data),
            "unpaid_rows": sum(1 for row in rows_data if row.yango_payment_status == 'UNPAID'),
            "unpaid_amount": sum(float(row.expected_amount) for row in rows_data if row.yango_payment_status == 'UNPAID'),
            "misapplied_rows": sum(1 for row in rows_data if row.yango_payment_status == 'PAID_MISAPPLIED'),
            "misapplied_amount": sum(float(row.expected_amount) for row in rows_data if row.yango_payment_status == 'PAID_MISAPPLIED'),
            "paid_rows": sum(1 for row in rows_data if row.yango_payment_status == 'PAID'),
            "paid_amount": sum(float(row.expected_amount) for row in rows_data if row.yango_payment_status == 'PAID'),
        }
        
        # Convertir a modelos
        rows = []
        for row in rows_data:
            rows.append(YangoCabinetClaimsForCollectionRow(**dict(row)))
        
        return YangoCabinetClaimsForCollectionResponse(
            rows=rows,
            aggregates=aggregates
        )
    
    except Exception as e:
        logger.error(f"Error en yango cabinet claims for collection: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar claims for collection: {str(e)}"
        )


@router.get("/payments/yango/cabinet/claims.csv")
def get_yango_cabinet_claims_for_collection_csv(
    db: Session = Depends(get_db),
    payment_status: Optional[str] = Query(None, description="Filtra por payment_status (UNPAID,PAID_MISAPPLIED,PAID). Default: UNPAID,PAID_MISAPPLIED"),
    overdue_bucket: Optional[str] = Query(None, description="Filtra por overdue_bucket_yango"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone_value (1, 5, 25)"),
    date_from: Optional[date] = Query(None, description="Filtra por lead_date desde"),
    date_to: Optional[date] = Query(None, description="Filtra por lead_date hasta"),
    search: Optional[str] = Query(None, description="Busca en driver_name o driver_id"),
    limit: int = Query(100000, ge=1, le=500000, description="Límite de resultados")
):
    """
    Exporta claims desde ops.v_yango_cabinet_claims_for_collection como CSV.
    Por defecto muestra UNPAID y PAID_MISAPPLIED.
    """
    try:
        # Construir WHERE conditions (mismo código que el endpoint JSON)
        where_conditions = []
        params = {}
        
        if payment_status:
            status_list = [s.strip() for s in payment_status.split(',')]
            where_conditions.append("yango_payment_status = ANY(:payment_status)")
            params["payment_status"] = status_list
        else:
            where_conditions.append("yango_payment_status = ANY(:payment_status)")
            params["payment_status"] = ['UNPAID', 'PAID_MISAPPLIED']
        
        if overdue_bucket:
            where_conditions.append("overdue_bucket_yango = :overdue_bucket")
            params["overdue_bucket"] = overdue_bucket
        
        if milestone_value:
            where_conditions.append("milestone_value = :milestone_value")
            params["milestone_value"] = milestone_value
        
        if date_from:
            where_conditions.append("lead_date >= :date_from")
            params["date_from"] = date_from
        
        if date_to:
            where_conditions.append("lead_date <= :date_to")
            params["date_to"] = date_to
        
        if search:
            where_conditions.append("(driver_name ILIKE :search OR driver_id::text ILIKE :search)")
            params["search"] = f"%{search}%"
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        sql = f"""
            SELECT 
                driver_name,
                driver_id,
                person_key,
                lead_date,
                yango_due_date,
                days_overdue_yango,
                overdue_bucket_yango,
                milestone_value,
                expected_amount,
                yango_payment_status,
                reason_code,
                payment_key,
                pay_date,
                match_rule,
                match_confidence
            FROM ops.v_yango_cabinet_claims_for_collection
            {where_clause}
            ORDER BY days_overdue_yango DESC, lead_date DESC
            LIMIT :limit
        """
        
        params["limit"] = limit
        
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        # Crear CSV en memoria
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'driver_name', 'driver_id', 'person_key',
            'lead_date', 'yango_due_date', 'days_overdue_yango', 'overdue_bucket_yango',
            'milestone_value', 'expected_amount',
            'yango_payment_status', 'reason_code',
            'payment_key', 'pay_date', 'match_rule', 'match_confidence'
        ])
        
        # Filas
        for row in rows_data:
            writer.writerow([
                row.driver_name or '',
                row.driver_id or '',
                str(row.person_key) if row.person_key else '',
                row.lead_date.isoformat() if row.lead_date else '',
                row.yango_due_date.isoformat() if row.yango_due_date else '',
                row.days_overdue_yango or 0,
                row.overdue_bucket_yango or '',
                row.milestone_value or 0,
                row.expected_amount or 0,
                row.yango_payment_status or '',
                row.reason_code or '',
                row.payment_key or '',
                row.pay_date.isoformat() if row.pay_date else '',
                row.match_rule or '',
                row.match_confidence or ''
            ])
        
        output.seek(0)
        
        # Retornar como CSV
        return Response(
            content=output.getvalue(),
            media_type='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename="yango_cabinet_claims.csv"'
            }
        )
    
    except Exception as e:
        logger.error(f"Error en yango cabinet claims CSV export: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al exportar claims CSV: {str(e)}"
        )
