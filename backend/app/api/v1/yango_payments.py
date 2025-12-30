"""
Endpoints para reconciliación de pagos Yango

Endpoints:
- GET /payments/reconciliation/summary - Resumen agregado por semana y milestone
- GET /payments/reconciliation/items - Items detallados de claims
- GET /payments/reconciliation/ledger/unmatched - Ledger sin match contra claims
- GET /payments/reconciliation/ledger/matched - Ledger con match contra claims
- GET /payments/reconciliation/driver/{driver_id} - Detalle de un conductor
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Literal
from datetime import date
import logging

from app.db import get_db
from app.schemas.payments import (
    YangoReconciliationSummaryRow,
    YangoReconciliationSummaryResponse,
    YangoReconciliationItemRow,
    YangoReconciliationItemsResponse,
    YangoLedgerUnmatchedRow,
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
    ClaimsCabinetSummaryResponse
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
