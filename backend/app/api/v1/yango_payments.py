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

from app.db import get_db
from app.schemas.payments import (
    YangoPaymentIngestResponse,
    YangoReconciliationSummaryRow,
    YangoReconciliationSummaryResponse,
    YangoReconciliationItemRow,
    YangoReconciliationItemsResponse
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
    status: Optional[str] = Query(None, description="Filtra por reconciliation_status: paid, pending, anomaly_paid_without_expected"),
    limit: int = Query(1000, ge=1, le=10000, description="Límite de resultados (máx 10000)")
):
    """
    Consulta el resumen agregado semanal de reconciliación Yango.
    
    Retorna agregados por pay_week_start_monday, milestone_value y reconciliation_status
    desde ops.v_yango_reconciliation_summary.
    
    Todos los parámetros de filtro son opcionales.
    """
    # Validar milestone_value si se proporciona
    if milestone_value is not None and milestone_value not in [1, 5, 25]:
        raise HTTPException(
            status_code=400,
            detail=f"milestone_value debe ser 1, 5 o 25, recibido: {milestone_value}"
        )
    
    # Validar status si se proporciona
    if status is not None and status not in ['paid', 'pending', 'anomaly_paid_without_expected']:
        raise HTTPException(
            status_code=400,
            detail=f"status debe ser 'paid', 'pending' o 'anomaly_paid_without_expected', recibido: {status}"
        )
    
    # Construir WHERE dinámico
    where_conditions = []
    params = {}
    
    if week_start is not None:
        where_conditions.append("pay_week_start_monday = :week_start")
        params["week_start"] = week_start
    
    if milestone_value is not None:
        where_conditions.append("milestone_value = :milestone_value")
        params["milestone_value"] = milestone_value
    
    if status is not None:
        where_conditions.append("reconciliation_status = :status")
        params["status"] = status
    
    # Construir query SQL
    # Intentar usar summary_ui primero, si no existe usar summary
    try:
        check_ui = db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.views 
                WHERE table_schema = 'ops' AND table_name = 'v_yango_reconciliation_summary_ui'
            )
        """))
        has_ui = check_ui.scalar()
        if has_ui:
            sql = "SELECT * FROM ops.v_yango_reconciliation_summary_ui"
        else:
            sql = "SELECT * FROM ops.v_yango_reconciliation_summary"
    except Exception as e:
        logger.warning(f"Error checking for summary_ui view, using summary: {e}")
        # Fallback a summary original
        sql = "SELECT * FROM ops.v_yango_reconciliation_summary"
    
    if where_conditions:
        sql += " WHERE " + " AND ".join(where_conditions)
    
    sql += " ORDER BY pay_week_start_monday DESC, milestone_value, reconciliation_status"
    sql += " LIMIT :limit"
    params["limit"] = limit
    
    # Logging
    log_filters = {
        "week_start": str(week_start) if week_start else None,
        "milestone_value": milestone_value,
        "status": status,
        "limit": limit
    }
    logger.info(f"Yango reconciliation summary query: {log_filters}")
    
    # Ejecutar query
    try:
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        # Convertir a listas de dicts para Pydantic
        rows = [dict(row) for row in rows_data]
        
        # Construir respuesta
        filters_dict = {k: v for k, v in log_filters.items() if v is not None}
        
        return YangoReconciliationSummaryResponse(
            status="ok",
            count=len(rows),
            filters=filters_dict,
            rows=[YangoReconciliationSummaryRow(**row) for row in rows]
        )
    except Exception as e:
        logger.error(f"Error executing Yango reconciliation summary query: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar resumen de reconciliación Yango: {str(e)}"
        )


@router.get("/payments/reconciliation/items", response_model=YangoReconciliationItemsResponse)
def get_yango_reconciliation_items(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None, description="Filtra por reconciliation_status: paid, pending, anomaly_paid_without_expected"),
    week_start: Optional[date] = Query(None, description="Filtra por pay_week_start_monday"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone_value (1, 5, 25)"),
    driver_id: Optional[str] = Query(None, description="Filtra por driver_id"),
    person_key: Optional[str] = Query(None, description="Filtra por person_key (UUID)"),
    limit: int = Query(200, ge=1, le=1000, description="Límite de resultados (máx 1000)"),
    offset: int = Query(0, ge=0, description="Offset para paginación")
):
    """
    Consulta items detallados de reconciliación Yango.
    
    Retorna items desde ops.v_yango_reconciliation_detail con filtros opcionales.
    Incluye información completa de expected y paid para cada item.
    
    Todos los parámetros de filtro son opcionales.
    """
    # Validar milestone_value si se proporciona
    if milestone_value is not None and milestone_value not in [1, 5, 25]:
        raise HTTPException(
            status_code=400,
            detail=f"milestone_value debe ser 1, 5 o 25, recibido: {milestone_value}"
        )
    
    # Validar status si se proporciona
    if status is not None and status not in ['paid', 'pending', 'anomaly_paid_without_expected']:
        raise HTTPException(
            status_code=400,
            detail=f"status debe ser 'paid', 'pending' o 'anomaly_paid_without_expected', recibido: {status}"
        )
    
    # Construir WHERE dinámico
    where_conditions = []
    params = {}
    
    if status is not None:
        where_conditions.append("reconciliation_status = :status")
        params["status"] = status
    
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
    
    # Construir query SQL
    sql = "SELECT * FROM ops.v_yango_reconciliation_detail"
    
    if where_conditions:
        sql += " WHERE " + " AND ".join(where_conditions)
    
    sql += " ORDER BY COALESCE(payable_date, paid_date) DESC NULLS LAST, milestone_value, reconciliation_status"
    sql += " LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset
    
    # Logging
    log_filters = {
        "status": status,
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

