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
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError, OperationalError
from typing import Optional, Literal
from datetime import date, datetime
from uuid import UUID
import logging
import hashlib
import csv
import io

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
    YangoCabinetClaimRow,
    YangoCabinetClaimsResponse,
    YangoCabinetClaimDrilldownResponse,
    LeadCabinetInfo,
    PaymentInfo,
    ReconciliationInfo,
    YangoCabinetMvHealthRow,
    CabinetReconciliationRow,
    CabinetReconciliationResponse
)
from app.schemas.cabinet_recovery import (
    CabinetRecoveryImpactResponse,
    CabinetRecoveryImpactTotals,
    CabinetRecoveryImpactSeriesItem
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
        # Nota: driver_id_final puede no existir en todas las versiones de la vista
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
        
        # Convertir UUIDs a strings y datetime a date si es necesario
        def convert_uuids_to_strings(row_dict):
            """Convierte UUIDs a strings y datetime a date para compatibilidad con Pydantic"""
            converted = {}
            for key, value in row_dict.items():
                if isinstance(value, UUID):
                    converted[key] = str(value)
                elif isinstance(value, datetime):
                    # Si el campo debería ser date, convertir
                    converted[key] = value.date() if hasattr(value, 'date') else value
                else:
                    converted[key] = value
            return converted
        
        rows = [YangoReconciliationItemRow(**convert_uuids_to_strings(dict(row))) for row in rows_data]
        
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


@router.get("/cabinet/collection-with-scout")
def get_collection_with_scout(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    scout_missing_only: bool = Query(False, description="Solo missing scout"),
    conflicts_only: bool = Query(False, description="Solo conflicts"),
    scout_id: Optional[int] = Query(None, description="Filtrar por scout_id"),
):
    """
    Cobranza Yango con información de scout
    """
    try:
        offset = (page - 1) * page_size
        
        where_conditions = []
        params = {"page_size": page_size, "offset": offset}
        
        if scout_missing_only:
            where_conditions.append("is_scout_resolved = false")
        if conflicts_only:
            # Requiere join con conflicts view
            where_conditions.append("person_key IN (SELECT person_key FROM ops.v_scout_attribution_conflicts)")
        if scout_id:
            where_conditions.append("scout_id = :scout_id")
            params["scout_id"] = scout_id
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        query = text(f"""
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
                match_confidence,
                identity_status,
                scout_id,
                scout_name,
                scout_type,
                scout_quality_bucket,
                is_scout_resolved
            FROM ops.v_yango_collection_with_scout
            {where_clause}
            ORDER BY lead_date DESC, milestone_value DESC
            LIMIT :page_size OFFSET :offset
        """)
        
        count_query = text(f"""
            SELECT COUNT(*) 
            FROM ops.v_yango_collection_with_scout
            {where_clause}
        """)
        
        result = db.execute(query, params)
        count_result = db.execute(count_query, {k: v for k, v in params.items() if k != "page_size" and k != "offset"})
        total = count_result.scalar()
        
        return {
            "items": [
                {
                    "driver_id": row.driver_id,
                    "person_key": str(row.person_key) if row.person_key else None,
                    "driver_name": row.driver_name,
                    "milestone_value": row.milestone_value,
                    "lead_date": str(row.lead_date) if row.lead_date else None,
                    "expected_amount": float(row.expected_amount) if row.expected_amount else 0,
                    "yango_due_date": str(row.yango_due_date) if row.yango_due_date else None,
                    "days_overdue_yango": row.days_overdue_yango,
                    "overdue_bucket_yango": row.overdue_bucket_yango,
                    "yango_payment_status": row.yango_payment_status,
                    "payment_key": row.payment_key,
                    "pay_date": str(row.pay_date) if row.pay_date else None,
                    "reason_code": row.reason_code,
                    "match_rule": row.match_rule,
                    "match_confidence": row.match_confidence,
                    "identity_status": row.identity_status,
                    "scout_id": row.scout_id,
                    "scout_name": row.scout_name,
                    "scout_type": row.scout_type,
                    "scout_quality_bucket": row.scout_quality_bucket,
                    "is_scout_resolved": row.is_scout_resolved,
                }
                for row in result.fetchall()
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        }
    except Exception as e:
        logger.error(f"Error obteniendo collection with scout: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo collection with scout: {str(e)}")


@router.get("/cabinet/claims-to-collect", response_model=YangoCabinetClaimsResponse)
def get_cabinet_claims_to_collect(
    db: Session = Depends(get_db),
    date_from: Optional[date] = Query(None, description="Filtra por fecha lead desde"),
    date_to: Optional[date] = Query(None, description="Filtra por fecha lead hasta"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone (1, 5, 25)"),
    search: Optional[str] = Query(None, description="Búsqueda en driver_name o driver_id"),
    limit: int = Query(50, ge=1, le=200, description="Límite de resultados por página"),
    offset: int = Query(0, ge=0, description="Offset para paginación")
):
    """
    Obtiene lista de claims exigibles a Yango (EXIGIMOS).
    
    Basado en QUERY 3.1 de docs/ops/yango_cabinet_claims_to_collect.sql
    Fuente: ops.v_yango_cabinet_claims_exigimos (ya filtra UNPAID)
    
    READ-ONLY: No recalcula estados, solo consume la vista existente.
    """
    # Construir query base (QUERY 3.1)
    where_conditions = []
    params = {}
    
    # Filtros opcionales
    if date_from:
        where_conditions.append("lead_date >= :date_from")
        params["date_from"] = date_from
    
    if date_to:
        where_conditions.append("lead_date <= :date_to")
        params["date_to"] = date_to
    
    if milestone_value:
        where_conditions.append("milestone_value = :milestone_value")
        params["milestone_value"] = milestone_value
    
    if search:
        # Búsqueda en driver_name o driver_id
        where_conditions.append("(driver_name ILIKE :search OR driver_id ILIKE :search)")
        params["search"] = f"%{search}%"
    
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)
    
    # Query para contar total
    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM ops.v_yango_cabinet_claims_exigimos
        {where_clause}
    """
    
    # Query para obtener datos (QUERY 3.1)
    sql = f"""
        SELECT 
            claim_key,
            driver_id,
            driver_name,
            person_key,
            milestone_value,
            expected_amount,
            lead_date,
            yango_due_date,
            days_overdue_yango,
            overdue_bucket_yango,
            yango_payment_status,
            reason_code,
            identity_status,
            match_rule,
            match_confidence,
            is_reconcilable_enriched,
            payment_key,
            pay_date,
            suggested_driver_id
        FROM ops.v_yango_cabinet_claims_exigimos
        {where_clause}
        ORDER BY 
            days_overdue_yango DESC,
            expected_amount DESC,
            driver_id,
            milestone_value
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
        
        # Convertir UUID a string para person_key (si existe)
        rows = []
        for row in rows_data:
            row_dict = dict(row)
            # Convertir person_key de UUID a string si existe
            if 'person_key' in row_dict and row_dict['person_key'] is not None:
                # PostgreSQL devuelve UUID como objeto UUID, convertir a string
                row_dict['person_key'] = str(row_dict['person_key'])
            rows.append(YangoCabinetClaimRow(**row_dict))
        
        filters = {
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "milestone_value": milestone_value,
            "search": search,
            "limit": limit,
            "offset": offset
        }
        
        return YangoCabinetClaimsResponse(
            status="ok",
            count=len(rows),
            total=total,
            filters={k: v for k, v in filters.items() if v is not None},
            rows=rows
        )
    except OperationalError as e:
        # Error de conexión a BD
        logger.exception(f"Error de conexion a BD en cabinet claims to collect: {e}")
        raise HTTPException(
            status_code=503,
            detail="DB no disponible / revisa DATABASE_URL"
        )
    except ProgrammingError as e:
        # Error de SQL (vista no existe, etc.)
        error_code = getattr(e.orig, 'pgcode', None) if hasattr(e, 'orig') else None
        error_message = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        # SQLSTATE 42P01 = undefined_table
        if error_code == '42P01' or 'does not exist' in error_message.lower() or 'v_yango_cabinet_claims_exigimos' in error_message:
            logger.exception(f"Vista no existe en cabinet claims to collect: {e}")
            raise HTTPException(
                status_code=404,
                detail="Falta vista ops.v_yango_cabinet_claims_exigimos. Aplica backend/sql/ops/v_yango_cabinet_claims_exigimos.sql"
            )
        # Otro error de PostgreSQL
        logger.exception(f"Error SQL en cabinet claims to collect: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error SQL: {error_message[:200]}"  # Limitar longitud, sin exponer credenciales
        )
    except Exception as e:
        logger.exception(f"Error inesperado en cabinet claims to collect: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar claims exigibles: {str(e)[:200]}"
        )


@router.get("/cabinet/claims/{driver_id}/{milestone_value}/drilldown", response_model=YangoCabinetClaimDrilldownResponse)
def get_cabinet_claim_drilldown(
    driver_id: str,
    milestone_value: int,
    db: Session = Depends(get_db),
    lead_date: Optional[date] = Query(None, description="Fecha lead opcional para desambiguar si hay múltiples claims")
):
    """
    Obtiene drilldown completo de un claim específico (evidencia para defensa del cobro).
    
    Basado en QUERY 4.4 de docs/ops/yango_cabinet_claims_drilldown.sql
    Fuente: ops.mv_yango_cabinet_claims_for_collection
    
    Identificadores: driver_id + milestone_value (+ lead_date opcional si hay ambigüedad)
    
    READ-ONLY: Solo agrega bloques de evidencia, sin lógica adicional.
    """
    try:
        # Construir filtro para claim_base
        claim_filter = "c.driver_id = :driver_id AND c.milestone_value = :milestone_value"
        params = {
            "driver_id": driver_id,
            "milestone_value": milestone_value
        }
        
        if lead_date:
            claim_filter += " AND c.lead_date = :lead_date"
            params["lead_date"] = lead_date
        
        # Verificar si hay múltiples claims para driver_id+milestone_value
        count_claims_sql = f"""
            SELECT COUNT(*) AS count
            FROM ops.mv_yango_cabinet_claims_for_collection c
            WHERE {claim_filter}
        """
        count_result = db.execute(text(count_claims_sql), params).fetchone()
        claim_count = count_result.count if count_result else 0
        
        if claim_count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Claim no encontrado para driver_id={driver_id}, milestone_value={milestone_value}"
            )
        
        if claim_count > 1 and not lead_date:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Ambigüedad: existen {claim_count} claims para driver_id={driver_id}, "
                    f"milestone_value={milestone_value}. "
                    f"Proporcione el parámetro 'lead_date' para desambiguar."
                )
            )
        
        # QUERY 4.4: Drilldown genérico
        sql = f"""
            WITH claim_base AS (
                SELECT 
                    c.*
                FROM ops.mv_yango_cabinet_claims_for_collection c
                WHERE {claim_filter}
                LIMIT 1
            ),
            lead_cabinet AS (
                SELECT 
                    il.source_pk,
                    il.match_rule,
                    il.match_score,
                    il.confidence_level,
                    il.linked_at
                FROM canon.identity_links il
                WHERE il.source_table = 'module_ct_cabinet_leads'
                    AND il.person_key = (SELECT person_key FROM claim_base LIMIT 1)
                LIMIT 1
            ),
            payment_exact AS (
                SELECT 
                    p.payment_key,
                    p.pay_date,
                    p.milestone_value,
                    p.identity_status,
                    p.match_rule
                FROM ops.v_yango_payments_ledger_latest_enriched p
                WHERE p.driver_id_final = (SELECT driver_id FROM claim_base LIMIT 1)
                    AND p.milestone_value = (SELECT milestone_value FROM claim_base LIMIT 1)
                    AND p.is_paid = true
                ORDER BY p.pay_date DESC
                LIMIT 1
            ),
            payments_other_milestones AS (
                SELECT 
                    p.milestone_value,
                    p.payment_key,
                    p.pay_date,
                    p.identity_status,
                    p.match_rule
                FROM ops.v_yango_payments_ledger_latest_enriched p
                WHERE p.driver_id_final = (SELECT driver_id FROM claim_base LIMIT 1)
                    AND p.milestone_value != (SELECT milestone_value FROM claim_base LIMIT 1)
                    AND p.is_paid = true
            ),
            reconciliation AS (
                SELECT 
                    r.reconciliation_status,
                    r.expected_amount,
                    r.paid_payment_key,
                    r.paid_date,
                    r.match_method
                FROM ops.v_yango_reconciliation_detail r
                WHERE r.driver_id = (SELECT driver_id FROM claim_base LIMIT 1)
                    AND r.milestone_value = (SELECT milestone_value FROM claim_base LIMIT 1)
                LIMIT 1
            )
            SELECT 
                -- Información del claim
                cb.driver_id,
                cb.driver_name,
                cb.person_key,
                cb.milestone_value,
                cb.expected_amount,
                cb.lead_date,
                cb.yango_due_date,
                cb.days_overdue_yango,
                cb.yango_payment_status,
                cb.reason_code,
                cb.identity_status,
                cb.match_rule,
                cb.match_confidence,
                cb.is_reconcilable_enriched,
                cb.payment_key,
                cb.pay_date,
                cb.suggested_driver_id,
                
                -- Información del lead cabinet
                lc.source_pk AS lead_cabinet_source_pk,
                lc.match_rule AS lead_cabinet_match_rule,
                lc.match_score AS lead_cabinet_match_score,
                lc.confidence_level AS lead_cabinet_confidence_level,
                lc.linked_at AS lead_cabinet_linked_at,
                
                -- Pago exacto (si existe)
                pe.payment_key AS payment_exact_key,
                pe.pay_date AS payment_exact_date,
                pe.milestone_value AS payment_exact_milestone,
                pe.identity_status AS payment_exact_identity_status,
                pe.match_rule AS payment_exact_match_rule,
                
                -- Estado de reconciliación
                rec.reconciliation_status,
                rec.expected_amount AS reconciliation_expected_amount,
                rec.paid_payment_key AS reconciliation_paid_payment_key,
                rec.paid_date AS reconciliation_paid_date,
                rec.match_method AS reconciliation_match_method
            FROM claim_base cb
            LEFT JOIN lead_cabinet lc ON lc.source_pk IS NOT NULL
            LEFT JOIN payment_exact pe ON pe.payment_key IS NOT NULL
            LEFT JOIN reconciliation rec ON rec.reconciliation_status IS NOT NULL
        """
        
        result = db.execute(text(sql), params)
        row_data = result.mappings().first()
        
        if not row_data:
            raise HTTPException(
                status_code=404,
                detail=f"Claim no encontrado para driver_id={driver_id}, milestone_value={milestone_value}"
            )
        
        row_dict = dict(row_data)
        
        # Calcular claim_key (MD5 de driver_id|milestone_value|lead_date)
        claim_key_str = f"{row_dict.get('driver_id') or 'NULL'}|{row_dict.get('milestone_value') or 'NULL'}|{row_dict.get('lead_date') or 'NULL'}"
        claim_key = hashlib.md5(claim_key_str.encode()).hexdigest()
        
        # Construir claim_row
        claim_row = YangoCabinetClaimRow(
            claim_key=claim_key,
            driver_id=row_dict.get("driver_id"),
            driver_name=row_dict.get("driver_name"),
            person_key=row_dict.get("person_key"),
            milestone_value=row_dict.get("milestone_value"),
            expected_amount=row_dict.get("expected_amount"),
            lead_date=row_dict.get("lead_date"),
            yango_due_date=row_dict.get("yango_due_date"),
            days_overdue_yango=row_dict.get("days_overdue_yango"),
            yango_payment_status=row_dict.get("yango_payment_status"),
            reason_code=row_dict.get("reason_code"),
            identity_status=row_dict.get("identity_status"),
            match_rule=row_dict.get("match_rule"),
            match_confidence=row_dict.get("match_confidence"),
            is_reconcilable_enriched=row_dict.get("is_reconcilable_enriched"),
            payment_key=row_dict.get("payment_key"),
            pay_date=row_dict.get("pay_date"),
            suggested_driver_id=row_dict.get("suggested_driver_id")
        )
        
        # Construir lead_cabinet
        lead_cabinet = None
        if row_dict.get("lead_cabinet_source_pk"):
            lead_cabinet = LeadCabinetInfo(
                source_pk=row_dict.get("lead_cabinet_source_pk"),
                match_rule=row_dict.get("lead_cabinet_match_rule"),
                match_score=row_dict.get("lead_cabinet_match_score"),
                confidence_level=row_dict.get("lead_cabinet_confidence_level"),
                linked_at=row_dict.get("lead_cabinet_linked_at")
            )
        
        # Construir payment_exact
        payment_exact = None
        if row_dict.get("payment_exact_key"):
            payment_exact = PaymentInfo(
                payment_key=row_dict.get("payment_exact_key"),
                pay_date=row_dict.get("payment_exact_date"),
                milestone_value=row_dict.get("payment_exact_milestone"),
                identity_status=row_dict.get("payment_exact_identity_status"),
                match_rule=row_dict.get("payment_exact_match_rule")
            )
        
        # Obtener payments_other_milestones (query separada)
        payments_other_sql = text("""
            SELECT 
                p.milestone_value,
                p.payment_key,
                p.pay_date,
                p.identity_status,
                p.match_rule
            FROM ops.v_yango_payments_ledger_latest_enriched p
            WHERE p.driver_id_final = :driver_id
                AND p.milestone_value != :milestone_value
                AND p.is_paid = true
            ORDER BY p.pay_date DESC
        """)
        payments_other_result = db.execute(payments_other_sql, {"driver_id": driver_id, "milestone_value": milestone_value})
        payments_other_data = payments_other_result.mappings().all()
        payments_other_milestones = [PaymentInfo(**dict(row)) for row in payments_other_data]
        
        # Construir reconciliation
        reconciliation = None
        if row_dict.get("reconciliation_status"):
            reconciliation = ReconciliationInfo(
                reconciliation_status=row_dict.get("reconciliation_status"),
                expected_amount=row_dict.get("reconciliation_expected_amount"),
                paid_payment_key=row_dict.get("reconciliation_paid_payment_key"),
                paid_date=row_dict.get("reconciliation_paid_date"),
                match_method=row_dict.get("reconciliation_match_method")
            )
        
        # Construir misapplied_explanation si aplica
        misapplied_explanation = None
        if row_dict.get("yango_payment_status") == "PAID_MISAPPLIED":
            reason = row_dict.get("reason_code", "")
            if reason == "payment_found_other_milestone":
                misapplied_explanation = (
                    f"PAID_MISAPPLIED: Se encontró un pago para este driver pero en otro milestone. "
                    f"Milestone esperado: {milestone_value}, Payment key encontrado: {row_dict.get('payment_key', 'N/A')}. "
                    f"Ver payments_other_milestones para detalles."
                )
            else:
                misapplied_explanation = (
                    f"PAID_MISAPPLIED: {reason}. "
                    f"Estado identidad: {row_dict.get('identity_status', 'N/A')}, "
                    f"Confianza: {row_dict.get('match_confidence', 'N/A')}"
                )
        
        return YangoCabinetClaimDrilldownResponse(
            status="ok",
            claim=claim_row,
            lead_cabinet=lead_cabinet,
            payment_exact=payment_exact,
            payments_other_milestones=payments_other_milestones,
            reconciliation=reconciliation,
            misapplied_explanation=misapplied_explanation
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en cabinet claim drilldown: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar drilldown del claim: {str(e)}"
        )


@router.get("/cabinet/claims/export")
def export_cabinet_claims_csv(
    db: Session = Depends(get_db),
    date_from: Optional[date] = Query(None, description="Filtra por fecha lead desde"),
    date_to: Optional[date] = Query(None, description="Filtra por fecha lead hasta"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone (1, 5, 25)"),
    search: Optional[str] = Query(None, description="Búsqueda en driver_name o driver_id")
):
    """
    Exporta lista de claims exigibles a Yango (EXIGIMOS) a CSV.
    
    Basado en QUERY 3.2 de docs/ops/yango_cabinet_claims_to_collect.sql
    Fuente: ops.v_yango_cabinet_claims_exigimos (ya filtra UNPAID)
    
    Columnas: Usa nombres amigables para Excel según QUERY 3.2
    Orden: days_overdue_yango DESC, expected_amount DESC
    
    READ-ONLY: No recalcula estados, solo consume la vista existente.
    Hard cap: 200,000 filas máximo (error 413 si excede).
    """
    # Construir query base (QUERY 3.2)
    where_conditions = []
    params = {}
    
    # Filtros opcionales (mismos que claims-to-collect)
    if date_from:
        where_conditions.append("lead_date >= :date_from")
        params["date_from"] = date_from
    
    if date_to:
        where_conditions.append("lead_date <= :date_to")
        params["date_to"] = date_to
    
    if milestone_value:
        where_conditions.append("milestone_value = :milestone_value")
        params["milestone_value"] = milestone_value
    
    if search:
        # Búsqueda en driver_name o driver_id
        where_conditions.append("(driver_name ILIKE :search OR driver_id ILIKE :search)")
        params["search"] = f"%{search}%"
    
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)
    
    try:
        # Verificar conteo antes de exportar (hard cap defensivo)
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM ops.v_yango_cabinet_claims_exigimos
            {where_clause}
        """
        count_result = db.execute(text(count_sql), params).fetchone()
        total = count_result.total if count_result else 0
        
        if total > 200000:
            raise HTTPException(
                status_code=413,
                detail=f"Export excede límite de 200,000 filas. Total filtrado: {total}. Aplique filtros más restrictivos."
            )
        
        # Query para obtener datos (QUERY 3.2 - columnas exportables con nombres amigables)
        sql = f"""
        SELECT 
            -- Identificación
            driver_id AS "Driver ID",
            driver_name AS "Nombre Conductor",
            milestone_value AS "Milestone",
            
            -- Monto
            expected_amount AS "Monto Exigible (S/)",
            
            -- Fechas
            lead_date AS "Fecha Lead",
            yango_due_date AS "Fecha Vencimiento",
            days_overdue_yango AS "Días Vencidos",
            overdue_bucket_yango AS "Bucket Vencimiento",
            
            -- Estado
            yango_payment_status AS "Estado Pago",
            reason_code AS "Razón",
            identity_status AS "Estado Identidad",
            match_rule AS "Regla Matching",
            match_confidence AS "Confianza Matching",
            is_reconcilable_enriched AS "Reconciliable",
            
            -- Campos adicionales para contexto
            payment_key AS "Payment Key",
            pay_date AS "Fecha Pago Encontrado",
            suggested_driver_id AS "Driver ID Sugerido",
            person_key AS "Person Key"
            
        FROM ops.v_yango_cabinet_claims_exigimos
        {where_clause}
        ORDER BY 
            days_overdue_yango DESC,
            expected_amount DESC,
            driver_id,
            milestone_value
        """
        
        # Obtener datos
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        # Generar CSV en memoria
        output = io.StringIO()
        
        # Obtener nombres de columnas del primer row (ya vienen con alias de SQL)
        if rows_data:
            fieldnames = list(rows_data[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            
            for row in rows_data:
                # Convertir valores None a string vacío para CSV
                # Mitigar CSV injection: prefijar celdas que empiezan con (=,+,-,@) con '
                row_dict = {}
                for k, v in dict(row).items():
                    if v is None:
                        row_dict[k] = ''
                    elif isinstance(v, str) and v and v[0] in ('=', '+', '-', '@'):
                        # Prefijar con ' para prevenir ejecución de fórmulas en Excel
                        row_dict[k] = "'" + v
                    else:
                        row_dict[k] = v
                writer.writerow(row_dict)
        else:
            # CSV vacío con headers
            fieldnames = [
                "Driver ID", "Nombre Conductor", "Milestone",
                "Monto Exigible (S/)", "Fecha Lead", "Fecha Vencimiento",
                "Días Vencidos", "Bucket Vencimiento", "Estado Pago",
                "Razón", "Estado Identidad", "Regla Matching",
                "Confianza Matching", "Reconciliable", "Payment Key",
                "Fecha Pago Encontrado", "Driver ID Sugerido", "Person Key"
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
        
        csv_content = output.getvalue()
        output.close()
        
        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"yango_cabinet_claims_{timestamp}.csv"
        
        # Codificar CSV a bytes UTF-8 (sin BOM aún)
        csv_bytes = csv_content.encode('utf-8')
        
        # Agregar BOM UTF-8-SIG (EF BB BF) al inicio de los bytes
        # BOM: b'\xef\xbb\xbf' = bytes EF BB BF en hexadecimal
        bom_bytes = b'\xef\xbb\xbf'
        csv_content_with_bom = bom_bytes + csv_bytes
        
        # Retornar CSV como respuesta con UTF-8 BOM
        # NOTA: El BOM está en los bytes del contenido, no solo en el charset del header
        # Verificación manual:
        #   $r = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/yango/cabinet/claims/export?limit=1"
        #   $b = $r.Content; $h = ($b[0..2] | ForEach-Object { "{0:X2}" -f $_ }) -join ' '
        #   # Debe mostrar: "EF BB BF"
        return Response(
            content=csv_content_with_bom,
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "text/csv; charset=utf-8"
            }
        )
    except HTTPException:
        raise
    except OperationalError as e:
        # Error de conexión a BD
        logger.exception(f"Error de conexion a BD en export cabinet claims CSV: {e}")
        raise HTTPException(
            status_code=503,
            detail="DB no disponible / revisa DATABASE_URL"
        )
    except ProgrammingError as e:
        # Error de SQL (vista no existe, etc.)
        error_code = getattr(e.orig, 'pgcode', None) if hasattr(e, 'orig') else None
        error_message = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        # SQLSTATE 42P01 = undefined_table
        if error_code == '42P01' or 'does not exist' in error_message.lower() or 'v_yango_cabinet_claims_exigimos' in error_message:
            logger.exception(f"Vista no existe en export cabinet claims CSV: {e}")
            raise HTTPException(
                status_code=404,
                detail="Falta vista ops.v_yango_cabinet_claims_exigimos. Aplica backend/sql/ops/v_yango_cabinet_claims_exigimos.sql"
            )
        # Otro error de PostgreSQL
        logger.exception(f"Error SQL en export cabinet claims CSV: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error SQL: {error_message[:200]}"  # Limitar longitud, sin exponer credenciales
        )
    except Exception as e:
        logger.exception(f"Error inesperado en export cabinet claims CSV: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al exportar claims a CSV: {str(e)[:200]}"
        )


@router.get("/cabinet/mv-health", response_model=YangoCabinetMvHealthRow)
def get_cabinet_mv_health(
    db: Session = Depends(get_db)
):
    """
    Obtiene el estado de salud de la MV ops.mv_yango_cabinet_claims_for_collection.
    
    Fuente: ops.v_yango_cabinet_claims_mv_health
    READ-ONLY: No recalcula lógica, solo lee la vista existente.
    
    Retorna:
    - 200: Health check disponible
    - 404: Vista no existe o no hay datos
    - 500: Invariante roto (más de 1 fila en la vista)
    """
    try:
        # Leer de la vista (READ-ONLY, no recalcular)
        # Usar text() para todas las queries
        sql = text("SELECT * FROM ops.v_yango_cabinet_claims_mv_health")
        result = db.execute(sql)
        rows_data = result.mappings().all()
        
        if len(rows_data) == 0:
            raise HTTPException(
                status_code=404,
                detail="Vista ops.v_yango_cabinet_claims_mv_health no retorna datos. Verificar que ops.mv_refresh_log tiene registros."
            )
        
        if len(rows_data) > 1:
            raise HTTPException(
                status_code=500,
                detail=f"Invariante roto: vista ops.v_yango_cabinet_claims_mv_health retorna {len(rows_data)} filas (esperado: 1). Revisar definición de la vista."
            )
        
        # Retornar la única fila
        row = rows_data[0]
        return YangoCabinetMvHealthRow(**dict(row))
        
    except ProgrammingError as e:
        # Capturar error de PostgreSQL cuando la vista no existe
        # SQLSTATE 42P01 = undefined_table
        error_code = getattr(e.orig, 'pgcode', None) if hasattr(e, 'orig') else None
        error_message = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        if error_code == '42P01' or 'does not exist' in error_message.lower() or 'v_yango_cabinet_claims_mv_health' in error_message:
            raise HTTPException(
                status_code=404,
                detail="Aplica docs/ops/yango_cabinet_claims_mv_health.sql"
            )
        # Si es otro error de PostgreSQL, re-raise como 500
        logger.error(f"Error de PostgreSQL en get_cabinet_mv_health: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar health check de MV: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en get_cabinet_mv_health: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar health check de MV: {str(e)}"
        )


@router.get("/payments/cabinet/reconciliation", response_model=CabinetReconciliationResponse)
def get_cabinet_reconciliation(
    db: Session = Depends(get_db),
    driver_id: Optional[str] = Query(None, description="Filtra por driver_id (exact match)"),
    reconciliation_status: Optional[str] = Query(None, description="Filtra por reconciliation_status (OK, ACHIEVED_NOT_PAID, PAID_WITHOUT_ACHIEVEMENT, NOT_APPLICABLE)"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone_value (1, 5, 25)"),
    date_from: Optional[date] = Query(None, description="Fecha inicio (filtra por pay_date si existe, si no por achieved_date)"),
    date_to: Optional[date] = Query(None, description="Fecha fin (filtra por pay_date si existe, si no por achieved_date)"),
    limit: int = Query(100, ge=1, le=10000, description="Límite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación")
):
    """
    Obtiene datos de reconciliación canónica de milestones Cabinet.
    
    Fuente: ops.v_cabinet_milestones_reconciled (vista canónica FASE 1)
    
    Criterio de filtrado por fechas (date_from/date_to):
    - Si pay_date existe (NOT NULL): filtra por pay_date
    - Si pay_date es NULL: filtra por achieved_date
    - Usa COALESCE(pay_date, achieved_date) para determinar la fecha de referencia
    
    READ-ONLY: Solo SELECT, no modifica datos ni recalcula reglas.
    """
    where_conditions = []
    params = {}
    
    if driver_id:
        where_conditions.append("driver_id = :driver_id")
        params["driver_id"] = driver_id
    
    if reconciliation_status:
        where_conditions.append("reconciliation_status = :reconciliation_status")
        params["reconciliation_status"] = reconciliation_status
    
    if milestone_value:
        where_conditions.append("milestone_value = :milestone_value")
        params["milestone_value"] = milestone_value
    
    if date_from:
        # Filtro por fecha: COALESCE(pay_date, achieved_date) >= date_from
        where_conditions.append("COALESCE(pay_date, achieved_date) >= :date_from")
        params["date_from"] = date_from
    
    if date_to:
        # Filtro por fecha: COALESCE(pay_date, achieved_date) <= date_to
        where_conditions.append("COALESCE(pay_date, achieved_date) <= :date_to")
        params["date_to"] = date_to
    
    where_clause = ""
    if where_conditions:
        where_clause = "WHERE " + " AND ".join(where_conditions)
    
    # Query para contar total
    count_sql = f"""
        SELECT COUNT(*) AS total
        FROM ops.v_cabinet_milestones_reconciled
        {where_clause}
    """
    
    # Query para obtener datos
    sql = f"""
        SELECT 
            driver_id,
            milestone_value,
            achieved_flag,
            achieved_person_key,
            achieved_lead_date,
            achieved_date,
            achieved_trips_in_window,
            window_days,
            expected_amount,
            achieved_currency,
            rule_id,
            paid_flag,
            paid_person_key,
            pay_date,
            payment_key,
            identity_status,
            match_rule,
            match_confidence,
            latest_snapshot_at,
            reconciliation_status
        FROM ops.v_cabinet_milestones_reconciled
        {where_clause}
        ORDER BY driver_id, milestone_value
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
        
        # Convertir UUID a string para person_key (si existe) y datetime
        rows = []
        for row in rows_data:
            row_dict = dict(row)
            # Convertir UUIDs a strings
            for key in ['achieved_person_key', 'paid_person_key']:
                if key in row_dict and row_dict[key] is not None:
                    row_dict[key] = str(row_dict[key])
            # Convertir datetime a date si es necesario (latest_snapshot_at se mantiene como datetime)
            rows.append(CabinetReconciliationRow(**row_dict))
        
        filters = {
            "driver_id": driver_id,
            "reconciliation_status": reconciliation_status,
            "milestone_value": milestone_value,
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "limit": limit,
            "offset": offset
        }
        
        return CabinetReconciliationResponse(
            status="ok",
            count=len(rows),
            total=total,
            filters={k: v for k, v in filters.items() if v is not None},
            rows=rows
        )
    except OperationalError as e:
        # Error de conexión a BD
        logger.exception(f"Error de conexion a BD en cabinet reconciliation: {e}")
        raise HTTPException(
            status_code=503,
            detail="DB no disponible / revisa DATABASE_URL"
        )
    except ProgrammingError as e:
        # Error de SQL (vista no existe, etc.)
        error_code = getattr(e.orig, 'pgcode', None) if hasattr(e, 'orig') else None
        error_message = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        # SQLSTATE 42P01 = undefined_table
        if error_code == '42P01' or 'does not exist' in error_message.lower() or 'v_cabinet_milestones_reconciled' in error_message:
            logger.exception(f"Vista no existe en cabinet reconciliation: {e}")
            raise HTTPException(
                status_code=404,
                detail="Falta vista ops.v_cabinet_milestones_reconciled. Aplica backend/sql/ops/v_cabinet_milestones_reconciled.sql"
            )
        # Otro error de PostgreSQL
        logger.exception(f"Error SQL en cabinet reconciliation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error SQL: {error_message[:200]}"  # Limitar longitud, sin exponer credenciales
        )
    except Exception as e:
        logger.exception(f"Error inesperado en cabinet reconciliation: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar reconciliación: {str(e)[:200]}"
        )


@router.get("/cabinet/identity-recovery-impact-14d", response_model=CabinetRecoveryImpactResponse)
def get_cabinet_identity_recovery_impact_14d(
    db: Session = Depends(get_db),
    include_series: bool = Query(False, description="Incluir serie temporal (últimos 30 días)")
):
    """
    Obtiene el impacto de recovery sobre Cobranza Cabinet 14d.
    
    Retorna:
    - totals: Totales de impacto (total_leads, unidentified_count, etc.)
    - series (opcional): Serie temporal de los últimos 30 días
    - top_reasons (opcional): Top razones de fallo (si existen)
    """
    try:
        # Query para obtener totales
        totals_query = text("""
            SELECT 
                COUNT(*) AS total_leads,
                COUNT(*) FILTER (WHERE impact_bucket = 'still_unidentified') AS still_unidentified_count,
                COUNT(*) FILTER (WHERE impact_bucket = 'identified_but_missing_origin') AS identified_but_missing_origin_count,
                COUNT(*) FILTER (WHERE impact_bucket = 'recovered_within_14d_but_no_claim') AS recovered_within_14d_but_no_claim_count,
                COUNT(*) FILTER (WHERE impact_bucket = 'recovered_within_14d_and_claim') AS recovered_within_14d_and_claim_count,
                COUNT(*) FILTER (WHERE impact_bucket = 'recovered_late') AS recovered_late_count,
                COUNT(*) FILTER (WHERE claim_status_bucket = 'unidentified') AS unidentified_count,
                COUNT(*) FILTER (WHERE claim_status_bucket = 'identified_no_origin') AS identified_no_origin_count,
                COUNT(*) FILTER (WHERE claim_status_bucket = 'identified_origin_no_claim') AS identified_origin_no_claim_count
            FROM ops.v_cabinet_identity_recovery_impact_14d
        """)
        
        totals_result = db.execute(totals_query)
        totals_row = totals_result.fetchone()
        
        totals = CabinetRecoveryImpactTotals(
            total_leads=totals_row.total_leads if totals_row else 0,
            unidentified_count=totals_row.unidentified_count if totals_row else 0,
            identified_no_origin_count=totals_row.identified_no_origin_count if totals_row else 0,
            recovered_within_14d_count=(totals_row.recovered_within_14d_but_no_claim_count if totals_row else 0) + (totals_row.recovered_within_14d_and_claim_count if totals_row else 0),
            recovered_late_count=totals_row.recovered_late_count if totals_row else 0,
            recovered_within_14d_and_claim_count=totals_row.recovered_within_14d_and_claim_count if totals_row else 0,
            still_unidentified_count=totals_row.still_unidentified_count if totals_row else 0,
            identified_but_missing_origin_count=totals_row.identified_but_missing_origin_count if totals_row else 0,
            identified_origin_no_claim_count=totals_row.identified_origin_no_claim_count if totals_row else 0
        )
        
        # Serie temporal (si se solicita)
        series = None
        if include_series:
            series_query = text("""
                SELECT 
                    lead_date AS date,
                    COUNT(*) FILTER (WHERE claim_status_bucket = 'unidentified') AS unidentified,
                    COUNT(*) FILTER (WHERE recovered_within_14d = true) AS recovered_within_14d,
                    COUNT(*) FILTER (WHERE recovered_within_14d = false AND recovered_at IS NOT NULL) AS recovered_late,
                    COUNT(*) FILTER (WHERE has_claim = true) AS claims
                FROM ops.v_cabinet_identity_recovery_impact_14d
                WHERE lead_date >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY lead_date
                ORDER BY lead_date DESC
                LIMIT 30
            """)
            
            series_result = db.execute(series_query)
            series_rows = series_result.fetchall()
            
            series = [
                CabinetRecoveryImpactSeriesItem(
                    event_date=row.date,
                    unidentified=row.unidentified or 0,
                    recovered_within_14d=row.recovered_within_14d or 0,
                    recovered_late=row.recovered_late or 0,
                    claims=row.claims or 0
                )
                for row in series_rows
            ]
        
        return CabinetRecoveryImpactResponse(
            totals=totals,
            series=series,
            top_reasons=None  # TODO: Implementar si hay tabla de fail_reason
        )
        
    except ProgrammingError as e:
        error_code = getattr(e.orig, 'pgcode', None) if hasattr(e, 'orig') else None
        error_message = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        if error_code == '42P01' or 'does not exist' in error_message.lower() or 'v_cabinet_identity_recovery_impact_14d' in error_message:
            logger.exception(f"Vista no existe: {e}")
            raise HTTPException(
                status_code=404,
                detail="Vista ops.v_cabinet_identity_recovery_impact_14d no existe. Aplicar backend/sql/ops/v_cabinet_identity_recovery_impact_14d.sql"
            )
        
        logger.exception(f"Error SQL en identity recovery impact: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error SQL: {error_message[:200]}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error inesperado en identity recovery impact: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar impacto de recovery: {str(e)[:200]}"
        )
