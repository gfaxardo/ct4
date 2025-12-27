"""
Endpoints para Conciliación de Pagos Yango

Endpoints:
- POST /api/v1/yango/payments/ingest_snapshot: Ejecuta ingest idempotente de pagos Yango al ledger
- GET  /api/v1/yango/payments/reconciliation/summary: Resumen agregado semanal de reconciliación
- GET  /api/v1/yango/payments/reconciliation/items: Items detallados de reconciliación con filtros
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import date, datetime
from pathlib import Path
import logging
import json
import time
import traceback

from app.db import get_db
from app.schemas.payments import (
    YangoPaymentIngestResponse,
    YangoReconciliationSummaryRow,
    YangoReconciliationSummaryResponse,
    YangoReconciliationItemRow,
    YangoReconciliationItemsResponse,
    YangoLedgerUnmatchedRow,
    YangoLedgerUnmatchedResponse,
    YangoDriverDetailResponse,
    ClaimDetailRow
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/payments/ingest_snapshot", response_model=YangoPaymentIngestResponse)
def ingest_yango_payments_snapshot(db: Session = Depends(get_db)):
    """
    Ejecuta ingest idempotente de pagos Yango al ledger.
    
    Inserta snapshots desde ops.v_yango_payments_raw_current a 
    ops.yango_payment_status_ledger usando la función 
    ops.ingest_yango_payments_snapshot().
    
    Retorna el número de filas insertadas y el timestamp del snapshot.
    
    La ingest es idempotente: si no hay cambios, retorna 0 filas insertadas.
    """
    try:
        # Ejecutar función de ingest
        result = db.execute(text("SELECT ops.ingest_yango_payments_snapshot()"))
        rows_inserted = result.scalar()
        
        # Obtener timestamp del snapshot (último insertado en esta corrida)
        snapshot_result = db.execute(text("""
            SELECT MAX(snapshot_at) 
            FROM ops.yango_payment_status_ledger
            WHERE snapshot_at >= NOW() - INTERVAL '1 minute'
        """))
        snapshot_at = snapshot_result.scalar()
        
        if snapshot_at is None:
            # Si no hay snapshot reciente, usar NOW()
            snapshot_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Yango payments ingest completed: {rows_inserted} rows inserted")
        
        return YangoPaymentIngestResponse(
            status="ok",
            rows_inserted=rows_inserted,
            snapshot_at=snapshot_at
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error executing Yango payments ingest: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al ejecutar ingest de pagos Yango: {str(e)}"
        )


@router.get("/payments/reconciliation/summary", response_model=YangoReconciliationSummaryResponse)
def get_yango_reconciliation_summary(
    db: Session = Depends(get_db),
    week_start: Optional[date] = Query(None, description="Filtra por pay_week_start_monday"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone_value (1, 5, 25)"),
    status: Optional[str] = Query(None, description="Filtra por paid_status: paid, pending_active, pending_expired"),
    mode: str = Query("real", description="Modo: 'real' (pagos reales) o 'assumed' (pagos estimados por pending_active)"),
    limit: int = Query(1000, ge=1, le=10000, description="Límite de resultados (máx 10000)")
):
    """
    Consulta el resumen agregado semanal de reclamos Yango - Cabinet.
    
    Retorna agregados por pay_week_start_monday y milestone_value
    desde ops.v_yango_payments_claims_cabinet_14d.
    
    Todos los parámetros de filtro son opcionales.
    """
    # #region agent log
    try:
        with open('c:\\Users\\Pc\\Documents\\Cursor Proyectos\\ct4\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "A",
                "location": "yango_payments.py:get_yango_reconciliation_summary:entry",
                "message": "Endpoint entry with params",
                "data": {
                    "week_start": str(week_start) if week_start else None,
                    "milestone_value": milestone_value,
                    "status": status,
                    "limit": limit
                },
                "timestamp": int(time.time() * 1000)
            }) + '\n')
    except: pass
    # #endregion
    
    # Validar milestone_value si se proporciona
    if milestone_value is not None and milestone_value not in [1, 5, 25]:
        raise HTTPException(
            status_code=400,
            detail=f"milestone_value debe ser 1, 5 o 25, recibido: {milestone_value}"
        )
    
    # Traducir status antiguos y aceptar múltiples valores (comma-separated)
    paid_status_filter = None
    if status is not None and status.strip():
        # Aceptar múltiples valores separados por coma
        status_values = [s.strip() for s in status.split(',')]
        # Traducir status antiguos
        translated_statuses = []
        for s in status_values:
            if s == 'pending':
                # 'pending' se traduce a ambos pending_active y pending_expired
                translated_statuses.extend(['pending_active', 'pending_expired'])
            elif s == 'paid':
                translated_statuses.append('paid')
            elif s in ['pending_active', 'pending_expired']:
                translated_statuses.append(s)
            elif s.startswith('anomaly_'):
                # Status de anomalía antiguos se traducen a pending_expired
                translated_statuses.append('pending_expired')
            else:
                # Status desconocido, mantener tal cual (validación fallará si es inválido)
                translated_statuses.append(s)
        
        # Eliminar duplicados manteniendo orden
        translated_statuses = list(dict.fromkeys(translated_statuses))
        
        if translated_statuses:
            paid_status_filter = translated_statuses
    
    # Construir WHERE dinámico
    where_conditions = []
    params = {}
    
    if week_start is not None:
        where_conditions.append("pay_week_start_monday = :week_start")
        params["week_start"] = week_start
    
    if milestone_value is not None:
        where_conditions.append("milestone_value = :milestone_value")
        params["milestone_value"] = milestone_value
    
    if paid_status_filter is not None:
        # Filtrar por múltiples valores de paid_status usando IN
        placeholders = [f":status_{i}" for i in range(len(paid_status_filter))]
        where_conditions.append(f"paid_status IN ({','.join(placeholders)})")
        for i, s in enumerate(paid_status_filter):
            params[f"status_{i}"] = s
    
    # Preparar log_filters para uso posterior
    log_filters = {
        "week_start": str(week_start) if week_start else None,
        "milestone_value": milestone_value,
        "status": status,
        "paid_status_filter": paid_status_filter,
        "mode": mode,
        "limit": limit
    }
    
    # Validación SQL: ejecutar query de validación y loguear
    validation_info = {}
    try:
        validation_query = text("""
            SELECT 
                COALESCE(SUM(expected_amount), 0) AS expected_total,
                COALESCE(SUM(expected_amount) FILTER (WHERE paid_status='paid_confirmed'), 0) AS paid_confirmed_total,
                COALESCE(SUM(expected_amount) FILTER (WHERE paid_status='paid_enriched'), 0) AS paid_enriched_total,
                COALESCE(COUNT(*) FILTER (WHERE paid_status='pending_expired'), 0) AS anomalies_count,
                COUNT(*) FILTER (WHERE paid_status='paid_confirmed') AS count_paid_confirmed,
                COUNT(*) FILTER (WHERE paid_status='paid_enriched') AS count_paid_enriched,
                COUNT(*) FILTER (WHERE paid_status='pending_active') AS count_pending_active,
                COUNT(*) FILTER (WHERE paid_status='pending_expired') AS count_pending_expired
            FROM ops.v_yango_payments_claims_cabinet_14d
        """)
        validation_result = db.execute(validation_query)
        validation_row = validation_result.fetchone()
        if validation_row:
            validation_info = {
                'expected_total': float(validation_row.expected_total) if validation_row.expected_total else 0,
                'paid_confirmed_total': float(validation_row.paid_confirmed_total) if validation_row.paid_confirmed_total else 0,
                'paid_enriched_total': float(validation_row.paid_enriched_total) if validation_row.paid_enriched_total else 0,
                'paid_total': float(validation_row.paid_confirmed_total or 0) + float(validation_row.paid_enriched_total or 0),  # Total visible
                'anomalies_count': int(validation_row.anomalies_count) if validation_row.anomalies_count else 0,
                'count_paid_confirmed': int(validation_row.count_paid_confirmed) if validation_row.count_paid_confirmed else 0,
                'count_paid_enriched': int(validation_row.count_paid_enriched) if validation_row.count_paid_enriched else 0,
                'count_paid': int(validation_row.count_paid_confirmed or 0) + int(validation_row.count_paid_enriched or 0),  # Total para compatibilidad
                'count_pending_active': int(validation_row.count_pending_active) if validation_row.count_pending_active else 0,
                'count_pending_expired': int(validation_row.count_pending_expired) if validation_row.count_pending_expired else 0
            }
            logger.info(f"Yango claims validation - {validation_info}")
        
        # Contar registros en ledger con métricas extendidas (usando vista enriquecida HARDENED)
        ledger_metrics_query = text("""
            SELECT 
                COUNT(*) AS ledger_total_rows,
                COUNT(*) FILTER (WHERE is_paid = true) AS ledger_rows_is_paid_true,
                COUNT(*) FILTER (WHERE driver_id_final IS NULL) AS ledger_rows_driver_id_final_null,
                COUNT(*) FILTER (WHERE person_key_final IS NULL) AS ledger_rows_person_key_final_null,
                COUNT(*) FILTER (WHERE driver_id_final IS NULL AND person_key_final IS NULL) AS ledger_rows_both_identity_null,
                COUNT(*) FILTER (WHERE identity_status = 'confirmed') AS identity_confirmed_rows,
                COUNT(*) FILTER (WHERE identity_status = 'enriched') AS identity_enriched_rows,
                COUNT(*) FILTER (WHERE identity_status = 'ambiguous') AS identity_ambiguous_rows,
                COUNT(*) FILTER (WHERE identity_status = 'no_match') AS identity_no_match_rows,
                COUNT(*) FILTER (WHERE match_confidence = 'high') AS confidence_high_count,
                COUNT(*) FILTER (WHERE match_confidence = 'medium') AS confidence_medium_count,
                COUNT(*) FILTER (WHERE match_confidence = 'low') AS confidence_low_count,
                COUNT(*) FILTER (WHERE is_paid = true AND driver_id_final IS NULL) AS ledger_rows_is_paid_true_and_driver_id_null,
                COUNT(*) FILTER (WHERE identity_enriched = true) AS ledger_rows_identity_enriched,
                COUNT(*) FILTER (WHERE is_paid = true AND identity_status = 'confirmed') AS ledger_is_paid_true_confirmed,
                COUNT(*) FILTER (WHERE is_paid = true AND identity_status = 'enriched') AS ledger_is_paid_true_enriched,
                COUNT(*) FILTER (WHERE is_paid = true AND identity_status = 'ambiguous') AS ledger_is_paid_true_ambiguous,
                COUNT(*) FILTER (WHERE is_paid = true AND identity_status = 'no_match') AS ledger_is_paid_true_no_match,
                COUNT(DISTINCT payment_key) AS ledger_distinct_payment_keys
            FROM ops.v_yango_payments_ledger_latest_enriched
        """)
        ledger_metrics_result = db.execute(ledger_metrics_query)
        ledger_metrics_row = ledger_metrics_result.fetchone()
        if ledger_metrics_row:
            validation_info['ledger_total_rows'] = int(ledger_metrics_row.ledger_total_rows) if ledger_metrics_row.ledger_total_rows else 0
            validation_info['ledger_rows_is_paid_true'] = int(ledger_metrics_row.ledger_rows_is_paid_true) if ledger_metrics_row.ledger_rows_is_paid_true else 0
            validation_info['ledger_rows_driver_id_null'] = int(ledger_metrics_row.ledger_rows_driver_id_final_null) if ledger_metrics_row.ledger_rows_driver_id_final_null else 0  # Mantener compatibilidad
            validation_info['ledger_rows_person_key_null'] = int(ledger_metrics_row.ledger_rows_person_key_final_null) if ledger_metrics_row.ledger_rows_person_key_final_null else 0
            validation_info['ledger_rows_both_identity_null'] = int(ledger_metrics_row.ledger_rows_both_identity_null) if ledger_metrics_row.ledger_rows_both_identity_null else 0
            validation_info['identity_confirmed_rows'] = int(ledger_metrics_row.identity_confirmed_rows) if ledger_metrics_row.identity_confirmed_rows else 0
            validation_info['identity_enriched_rows'] = int(ledger_metrics_row.identity_enriched_rows) if ledger_metrics_row.identity_enriched_rows else 0
            validation_info['identity_ambiguous_rows'] = int(ledger_metrics_row.identity_ambiguous_rows) if ledger_metrics_row.identity_ambiguous_rows else 0
            validation_info['identity_no_match_rows'] = int(ledger_metrics_row.identity_no_match_rows) if ledger_metrics_row.identity_no_match_rows else 0
            validation_info['confidence_high_count'] = int(ledger_metrics_row.confidence_high_count) if ledger_metrics_row.confidence_high_count else 0
            validation_info['confidence_medium_count'] = int(ledger_metrics_row.confidence_medium_count) if ledger_metrics_row.confidence_medium_count else 0
            validation_info['confidence_low_count'] = int(ledger_metrics_row.confidence_low_count) if ledger_metrics_row.confidence_low_count else 0
            validation_info['distribution_confidence'] = {
                'high': validation_info['confidence_high_count'],
                'medium': validation_info['confidence_medium_count'],
                'low': validation_info['confidence_low_count']
            }
            validation_info['ledger_rows_is_paid_true_and_driver_id_null'] = int(ledger_metrics_row.ledger_rows_is_paid_true_and_driver_id_null) if ledger_metrics_row.ledger_rows_is_paid_true_and_driver_id_null else 0
            validation_info['ledger_rows_identity_enriched'] = int(ledger_metrics_row.ledger_rows_identity_enriched) if ledger_metrics_row.ledger_rows_identity_enriched else 0
            validation_info['ledger_distinct_payment_keys'] = int(ledger_metrics_row.ledger_distinct_payment_keys) if ledger_metrics_row.ledger_distinct_payment_keys else 0
            validation_info['ledger_is_paid_true_confirmed'] = int(ledger_metrics_row.ledger_is_paid_true_confirmed) if ledger_metrics_row.ledger_is_paid_true_confirmed else 0
            validation_info['ledger_is_paid_true_enriched'] = int(ledger_metrics_row.ledger_is_paid_true_enriched) if ledger_metrics_row.ledger_is_paid_true_enriched else 0
            validation_info['ledger_is_paid_true_ambiguous'] = int(ledger_metrics_row.ledger_is_paid_true_ambiguous) if ledger_metrics_row.ledger_is_paid_true_ambiguous else 0
            validation_info['ledger_is_paid_true_no_match'] = int(ledger_metrics_row.ledger_is_paid_true_no_match) if ledger_metrics_row.ledger_is_paid_true_no_match else 0
            # Mantener compatibilidad con nombre anterior
            validation_info['ledger_count'] = validation_info['ledger_total_rows']
            
            logger.info(f"Yango ledger metrics (HARDENED): {validation_info}")
    except Exception as e:
        logger.warning(f"Error executing validation query: {e}")
        # Asegurar que validation_info siempre existe como dict
        if not validation_info:
            validation_info = {}
    
    # Construir query SQL desde claims view
    # Agrupar por pay_week_start_monday y milestone_value
    # Incluir campos reales y assumed (estimados)
    sql = """
        SELECT
            pay_week_start_monday,
            milestone_value,
            COALESCE(SUM(expected_amount), 0) AS amount_expected_sum,
            COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'paid_confirmed'), 0) AS amount_paid_confirmed_sum,
            COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'paid_enriched'), 0) AS amount_paid_enriched_sum,
            COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'paid_confirmed'), 0) + 
            COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'paid_enriched'), 0) AS amount_paid_total_visible,
            COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'pending_active'), 0) AS amount_paid_assumed,
            COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'pending_active'), 0) AS amount_pending_active_sum,
            COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'pending_expired'), 0) AS amount_pending_expired_sum,
            COALESCE(SUM(expected_amount), 0) - 
            (COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'paid_confirmed'), 0) + 
             COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'paid_enriched'), 0)) AS amount_diff,
            COALESCE(SUM(expected_amount), 0) - COALESCE(SUM(expected_amount) FILTER (WHERE paid_status = 'pending_active'), 0) AS amount_diff_assumed,
            COALESCE(COUNT(*) FILTER (WHERE paid_status = 'pending_expired'), 0) AS anomalies_total,
            COALESCE(COUNT(*), 0) AS count_expected,
            COALESCE(COUNT(*) FILTER (WHERE paid_status = 'paid_confirmed'), 0) AS count_paid_confirmed,
            COALESCE(COUNT(*) FILTER (WHERE paid_status = 'paid_enriched'), 0) AS count_paid_enriched,
            COALESCE(COUNT(*) FILTER (WHERE paid_status = 'paid_confirmed'), 0) + 
            COALESCE(COUNT(*) FILTER (WHERE paid_status = 'paid_enriched'), 0) AS count_paid,
            COALESCE(COUNT(*) FILTER (WHERE paid_status = 'pending_active'), 0) AS count_pending_active,
            COALESCE(COUNT(*) FILTER (WHERE paid_status = 'pending_expired'), 0) AS count_pending_expired,
            COALESCE(COUNT(DISTINCT CASE WHEN driver_id IS NOT NULL THEN driver_id END), 0) AS count_drivers
        FROM ops.v_yango_payments_claims_cabinet_14d
    """
    
    if where_conditions:
        sql += " WHERE " + " AND ".join(where_conditions)
    
    sql += " GROUP BY pay_week_start_monday, milestone_value"
    sql += " ORDER BY pay_week_start_monday DESC, milestone_value"
    sql += " LIMIT :limit"
    params["limit"] = limit
    
    # Logging
    logger.info(f"Yango reconciliation summary query: {log_filters}")
    
    # #region agent log
    try:
        with open('c:\\Users\\Pc\\Documents\\Cursor Proyectos\\ct4\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
            f.write(json.dumps({
                "sessionId": "debug-session",
                "runId": "run1",
                "hypothesisId": "C",
                "location": "yango_payments.py:get_yango_reconciliation_summary:before_query",
                "message": "SQL query before execution",
                "data": {"sql": sql, "params": {k: str(v) for k, v in params.items()}},
                "timestamp": int(time.time() * 1000)
            }) + '\n')
    except: pass
    # #endregion
    
    # Ejecutar query
    try:
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        # #region agent log
        try:
            with open('c:\\Users\\Pc\\Documents\\Cursor Proyectos\\ct4\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "C",
                    "location": "yango_payments.py:get_yango_reconciliation_summary:after_query",
                    "message": "Query executed successfully",
                    "data": {"rows_count": len(rows_data), "first_row_keys": list(rows_data[0].keys()) if rows_data else []},
                    "timestamp": int(time.time() * 1000)
                }) + '\n')
        except: pass
        # #endregion
        
        # Convertir a listas de dicts para Pydantic
        rows = [dict(row) for row in rows_data]
        
        # Si mode=assumed, reemplazar amount_paid_total_visible y amount_diff con los valores assumed
        # Mantener amount_paid_confirmed_sum y amount_paid_enriched_sum siempre separados
        if mode == 'assumed':
            for row in rows:
                if 'amount_paid_assumed' in row and row['amount_paid_assumed'] is not None:
                    row['amount_paid_total_visible'] = row['amount_paid_assumed']
                if 'amount_diff_assumed' in row and row['amount_diff_assumed'] is not None:
                    row['amount_diff'] = row['amount_diff_assumed']
        else:
            # mode=real: amount_paid_total_visible ya está calculado como confirmed+enriched
            pass
        
        # #region agent log
        try:
            with open('c:\\Users\\Pc\\Documents\\Cursor Proyectos\\ct4\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "D",
                    "location": "yango_payments.py:get_yango_reconciliation_summary:before_pydantic",
                    "message": "Before Pydantic conversion",
                    "data": {"rows_count": len(rows), "mode": mode, "first_row_sample": {k: str(v)[:50] for k, v in list(rows[0].items())[:5]} if rows else {}},
                    "timestamp": int(time.time() * 1000)
                }) + '\n')
        except: pass
        # #endregion
        
        # Construir respuesta
        filters_dict = {k: v for k, v in log_filters.items() if v is not None}
        
        # Agregar información de validación a filters para debug panel
        if validation_info:
            filters_dict['_validation'] = validation_info
        
        return YangoReconciliationSummaryResponse(
            status="ok",
            count=len(rows),
            filters=filters_dict,
            rows=[YangoReconciliationSummaryRow(**row) for row in rows]
        )
    except Exception as e:
        # #region agent log
        try:
            with open('c:\\Users\\Pc\\Documents\\Cursor Proyectos\\ct4\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "run1",
                    "hypothesisId": "E",
                    "location": "yango_payments.py:get_yango_reconciliation_summary:error",
                    "message": "Error caught in exception handler",
                    "data": {
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "traceback": traceback.format_exc()
                    },
                    "timestamp": int(time.time() * 1000)
                }) + '\n')
        except: pass
        # #endregion
        
        logger.error(f"Error executing Yango reconciliation summary query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar resumen de reconciliación Yango: {str(e)}"
        )


@router.get("/payments/reconciliation/items", response_model=YangoReconciliationItemsResponse)
def get_yango_reconciliation_items(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filtra por paid_status: paid, pending_active, pending_expired. Por defecto muestra pending_expired (reclamos)"),
    week_start: Optional[date] = Query(None, description="Filtra por pay_week_start_monday"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone_value (1, 5, 25)"),
    driver_id: Optional[str] = Query(None, description="Filtra por driver_id"),
    person_key: Optional[str] = Query(None, description="Filtra por person_key (UUID)"),
    limit: int = Query(200, ge=1, le=1000, description="Límite de resultados (máx 1000)"),
    offset: int = Query(0, ge=0, description="Offset para paginación")
):
    """
    Consulta items detallados de reclamos Yango - Cabinet.
    
    Retorna items desde ops.v_yango_payments_claims_cabinet_14d con filtros opcionales.
    Por defecto muestra solo pending_expired (reclamos vencidos que deben reclamarse).
    
    Todos los parámetros de filtro son opcionales.
    """
    # Validar milestone_value si se proporciona
    if milestone_value is not None and milestone_value not in [1, 5, 25]:
        raise HTTPException(
            status_code=400,
            detail=f"milestone_value debe ser 1, 5 o 25, recibido: {milestone_value}"
        )
    
    # Traducir status antiguos y aceptar múltiples valores (comma-separated)
    paid_status_filter = None
    if status is not None and status.strip():
        # Aceptar múltiples valores separados por coma
        status_values = [s.strip() for s in status.split(',')]
        # Traducir status antiguos
        translated_statuses = []
        for s in status_values:
            if s == 'pending':
                # 'pending' se traduce a ambos pending_active y pending_expired
                translated_statuses.extend(['pending_active', 'pending_expired'])
            elif s == 'paid':
                translated_statuses.append('paid')
            elif s in ['pending_active', 'pending_expired']:
                translated_statuses.append(s)
            elif s.startswith('anomaly_'):
                # Status de anomalía antiguos se traducen a pending_expired
                translated_statuses.append('pending_expired')
            else:
                # Status desconocido, mantener tal cual
                translated_statuses.append(s)
        
        # Eliminar duplicados manteniendo orden
        translated_statuses = list(dict.fromkeys(translated_statuses))
        
        if translated_statuses:
            paid_status_filter = translated_statuses
    else:
        # Por defecto, si no se especifica status, mostrar solo pending_expired (reclamos)
        paid_status_filter = ['pending_expired']
    
    # Construir WHERE dinámico
    where_conditions = []
    params = {}
    
    # Filtrar por paid_status (múltiples valores si aplica)
    if paid_status_filter:
        placeholders = [f":status_{i}" for i in range(len(paid_status_filter))]
        where_conditions.append(f"paid_status IN ({','.join(placeholders)})")
        for i, s in enumerate(paid_status_filter):
            params[f"status_{i}"] = s
    
    if week_start is not None:
        where_conditions.append("pay_week_start_monday = :week_start")
        params["week_start"] = week_start
    
    if milestone_value is not None:
        where_conditions.append("milestone_value = :milestone_value")
        params["milestone_value"] = milestone_value
    
    if driver_id is not None:
        where_conditions.append("driver_id = :driver_id")
        params["driver_id"] = driver_id
    
    if person_key is not None:
        where_conditions.append("person_key::text = :person_key")
        params["person_key"] = person_key
    
    # Construir query SQL desde claims view
    # Incluir campos de identity enrichment desde el ledger enriquecido
    sql = """
        SELECT
            c.person_key,
            c.driver_id,
            c.lead_date,
            c.pay_week_start_monday,
            c.milestone_value,
            c.expected_amount,
            c.currency,
            c.due_date,
            c.window_status,
            c.paid_payment_key,
            c.paid_payment_key_confirmed,
            c.paid_payment_key_enriched,
            c.paid_date,
            c.paid_date_confirmed,
            c.paid_date_enriched,
            c.paid_is_paid,
            c.is_paid_confirmed,
            c.is_paid_enriched,
            c.is_paid_effective,
            c.match_method,
            c.paid_status,
            -- Campos de identity enrichment (desde ledger enriquecido, usar el que matchea según paid_status)
            CASE 
                WHEN c.paid_status = 'paid_confirmed' THEN l_confirmed.identity_status
                WHEN c.paid_status = 'paid_enriched' THEN l_enriched.identity_status
                ELSE NULL
            END AS identity_status,
            CASE 
                WHEN c.paid_status = 'paid_confirmed' THEN l_confirmed.match_rule
                WHEN c.paid_status = 'paid_enriched' THEN l_enriched.match_rule
                ELSE NULL
            END AS match_rule,
            CASE 
                WHEN c.paid_status = 'paid_confirmed' THEN l_confirmed.match_confidence
                WHEN c.paid_status = 'paid_enriched' THEN l_enriched.match_confidence
                ELSE NULL
            END AS match_confidence,
            -- Mapear paid_status a reconciliation_status para compatibilidad
            CASE 
                WHEN c.paid_status IN ('paid_confirmed', 'paid_enriched') THEN 'paid'
                WHEN c.paid_status IN ('pending_active', 'pending_expired') THEN 'pending'
                ELSE c.paid_status
            END AS reconciliation_status,
            c.lead_date AS sort_date
        FROM ops.v_yango_payments_claims_cabinet_14d c
        LEFT JOIN ops.v_yango_payments_ledger_latest_enriched l_confirmed
            ON (
                (c.driver_id IS NOT NULL AND l_confirmed.driver_id_final = c.driver_id)
                OR (c.driver_id IS NULL AND c.person_key IS NOT NULL AND l_confirmed.person_key_final = c.person_key AND l_confirmed.driver_id_final IS NULL)
            )
            AND l_confirmed.milestone_value = c.milestone_value
            AND l_confirmed.identity_status = 'confirmed'
            AND l_confirmed.is_paid = true
        LEFT JOIN ops.v_yango_payments_ledger_latest_enriched l_enriched
            ON (
                (c.driver_id IS NOT NULL AND l_enriched.driver_id_final = c.driver_id)
                OR (c.driver_id IS NULL AND c.person_key IS NOT NULL AND l_enriched.person_key_final = c.person_key AND l_enriched.driver_id_final IS NULL)
            )
            AND l_enriched.milestone_value = c.milestone_value
            AND l_enriched.identity_status = 'enriched'
            AND l_enriched.is_paid = true
    """
    
    if where_conditions:
        sql += " WHERE " + " AND ".join(where_conditions)
    
    sql += " ORDER BY pay_week_start_monday DESC, lead_date DESC, milestone_value"
    sql += " LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset
    
    # Logging
    log_filters = {
        "status": status,
        "paid_status_filter": paid_status_filter,
        "week_start": str(week_start) if week_start else None,
        "milestone_value": milestone_value,
        "driver_id": driver_id,
        "person_key": person_key,
        "limit": limit,
        "offset": offset
    }
    logger.info(f"Yango reconciliation items query: {log_filters}")
    
    # Ejecutar query
    try:
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        # Convertir a listas de dicts para Pydantic
        rows = [dict(row) for row in rows_data]
        
        # Construir respuesta
        filters_dict = {k: v for k, v in log_filters.items() if v is not None}
        
        return YangoReconciliationItemsResponse(
            status="ok",
            count=len(rows),
            filters=filters_dict,
            rows=[YangoReconciliationItemRow(**row) for row in rows]
        )
    except Exception as e:
        logger.error(f"Error executing Yango reconciliation items query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar items de reconciliación Yango: {str(e)}"
        )


@router.get("/payments/reconciliation/ledger/unmatched", response_model=YangoLedgerUnmatchedResponse)
def get_yango_ledger_unmatched(
    db: Session = Depends(get_db),
    is_paid: Optional[bool] = Query(None, description="Filtrar por is_paid (true/false). Si no se especifica, muestra todos"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone_value (1, 5, 25)"),
    limit: int = Query(200, ge=1, le=1000, description="Límite de resultados (máx 1000)"),
    offset: int = Query(0, ge=0, description="Offset para paginación")
):
    """
    Consulta registros del ledger que no tienen match contra claims.
    
    Un registro del ledger se considera "unmatched" si:
    - driver_id IS NULL, O
    - No existe un claim correspondiente (por driver_id + milestone_value o person_key + milestone_value)
    
    Retorna registros paginados del ledger que no están reconciliados con claims.
    """
    # Validar milestone_value si se proporciona
    if milestone_value is not None and milestone_value not in [1, 5, 25]:
        raise HTTPException(
            status_code=400,
            detail=f"milestone_value debe ser 1, 5 o 25, recibido: {milestone_value}"
        )
    
    # Construir WHERE dinámico
    where_conditions = []
    params = {}
    
    # Filtrar por milestone_value
    if milestone_value is not None:
        where_conditions.append("l.milestone_value = :milestone_value")
        params["milestone_value"] = milestone_value
    
    # Filtrar por is_paid
    if is_paid is not None:
        where_conditions.append("l.is_paid = :is_paid")
        params["is_paid"] = is_paid
    
    # Query principal: ledger rows que NO tienen match en claims
    # Unmatched significa:
    # 1. driver_id IS NULL, O
    # 2. No existe claim por driver_id + milestone_value, O
    # 3. No existe claim por person_key + milestone_value (si person_key no es NULL)
    sql = """
        SELECT 
            l.payment_key,
            l.pay_date,
            l.is_paid,
            l.milestone_value,
            l.driver_id,
            l.person_key,
            l.raw_driver_name,
            l.driver_name_normalized,
            l.match_rule,
            l.match_confidence,
            l.latest_snapshot_at,
            l.source_pk,
            l.identity_enriched
        FROM ops.v_yango_payments_ledger_latest_enriched l
        WHERE (
            -- Condición 1: driver_id_final IS NULL
            l.driver_id_final IS NULL
            OR
            -- Condición 2: No existe match por driver_id_final + milestone_value
            NOT EXISTS (
                SELECT 1 
                FROM ops.v_yango_payments_claims_cabinet_14d c
                WHERE c.driver_id = l.driver_id_final
                    AND c.milestone_value = l.milestone_value
            )
        )
        AND (
            -- Si person_key_final no es NULL, también verificar que no haya match por person_key_final
            l.person_key_final IS NULL
            OR NOT EXISTS (
                SELECT 1 
                FROM ops.v_yango_payments_claims_cabinet_14d c
                WHERE c.person_key = l.person_key_final
                    AND c.milestone_value = l.milestone_value
            )
        )
    """
    
    if where_conditions:
        sql += " AND " + " AND ".join(where_conditions)
    
    # Contar total antes de aplicar LIMIT/OFFSET
    count_sql = f"SELECT COUNT(*) FROM ({sql}) AS unmatched_subquery"
    try:
        count_result = db.execute(text(count_sql), params)
        total_count = count_result.scalar() or 0
    except Exception as e:
        logger.error(f"Error counting unmatched ledger rows: {e}")
        total_count = 0
    
    # Aplicar paginación y ordenamiento
    sql += " ORDER BY l.pay_date DESC NULLS LAST, l.latest_snapshot_at DESC"
    sql += " LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset
    
    # Logging
    log_filters = {
        "is_paid": is_paid,
        "milestone_value": milestone_value,
        "limit": limit,
        "offset": offset
    }
    logger.info(f"Yango ledger unmatched query: {log_filters}, total_count: {total_count}")
    
    # Ejecutar query
    try:
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        # Convertir a listas de dicts para Pydantic
        rows = [dict(row) for row in rows_data]
        
        # Construir respuesta
        filters_dict = {k: v for k, v in log_filters.items() if v is not None}
        
        return YangoLedgerUnmatchedResponse(
            status="ok",
            count=len(rows),
            total=total_count,
            filters=filters_dict,
            rows=[YangoLedgerUnmatchedRow(**row) for row in rows]
        )
    except Exception as e:
        logger.error(f"Error executing Yango ledger unmatched query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar ledger sin match: {str(e)}"
        )

