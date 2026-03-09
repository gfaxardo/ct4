"""
Endpoints para operaciones de payments dentro del módulo ops.

El controller solo registra rutas y delega en app.services.ops_payments.
Toda la lógica de negocio está en los servicios.
"""
import io
import csv
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.db_utils import row_to_dict
from app.services.mv_cache import get_best_view, mv_exists
from app.services.ops_payments import (
    get_driver_matrix as service_get_driver_matrix,
    OrderByOption as ServiceOrderByOption,
    get_funnel_gap_metrics as service_get_funnel_gap_metrics,
    get_kpi_red_recovery_metrics as service_get_kpi_red_recovery_metrics,
    get_claims_audit_summary as service_get_claims_audit_summary,
)
from app.schemas.payments import (
    DriverMatrixRow,
    OpsDriverMatrixResponse,
    OpsDriverMatrixMeta
)
from app.schemas.cabinet_financial import (
    CabinetFinancialRow,
    CabinetFinancialResponse,
    CabinetFinancialSummary,
    CabinetFinancialSummaryTotal,
    CabinetFinancialMeta,
    ScoutAttributionMetrics,
    ScoutAttributionMetricsResponse,
    WeeklyKpiRow,
    WeeklyKpisResponse,
    CabinetLimboRow,
    CabinetLimboResponse,
    CabinetLimboSummary,
    CabinetLimboMeta,
    CabinetClaimsGapRow,
    CabinetClaimsGapResponse,
    CabinetClaimsGapSummary,
    CabinetClaimsGapMeta
)
from app.schemas.kpi_red_recovery import (
    KpiRedRecoveryMetricsResponse,
    KpiRedRecoveryMetricsDaily,
)
from time import time

logger = logging.getLogger(__name__)
router = APIRouter()

# Cache para cobranza_yango y weekly_kpis (solo en controller mientras no se migren a servicio)
CACHE_TTL = 60
CACHE_TTL_WEEKLY = 180
_scout_metrics_cache: Dict[Tuple, Tuple[float, ScoutAttributionMetrics]] = {}
_weekly_kpis_cache: Dict[Tuple, Tuple[float, dict]] = {}

# Re-exportar para Query()
OrderByOption = ServiceOrderByOption


@router.get("/driver-matrix", response_model=OpsDriverMatrixResponse)
def get_driver_matrix(
    db: Session = Depends(get_db),
    week_start_from: Optional[date] = Query(None, description="Filtra por week_start >= week_start_from (inclusive)"),
    week_start_to: Optional[date] = Query(None, description="Filtra por week_start <= week_start_to (inclusive)"),
    origin_tag: Optional[str] = Query(None, description="Filtra por origin_tag: 'cabinet', 'fleet_migration', 'unknown' o 'All'"),
    funnel_status: Optional[str] = Query(None, description="Filtra por funnel_status"),
    only_pending: bool = Query(False, description="Si true, solo drivers con al menos 1 milestone pendiente"),
    limit: int = Query(200, ge=1, le=1000, description="Límite de resultados (máx 1000). Default: 200."),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    order: ServiceOrderByOption = Query(ServiceOrderByOption.week_start_desc, description="Ordenamiento"),
):
    """Obtiene la matriz de drivers con milestones M1/M5/M25 y estados Yango/window."""
    return service_get_driver_matrix(
        db,
        week_start_from=week_start_from,
        week_start_to=week_start_to,
        origin_tag=origin_tag,
        funnel_status=funnel_status,
        only_pending=only_pending,
        limit=limit,
        offset=offset,
        order=order,
    )


@router.get("/cabinet-financial-14d", response_model=CabinetFinancialResponse)
def get_cabinet_financial_14d(
    db: Session = Depends(get_db),
    only_with_debt: bool = Query(False, description="Si true, solo drivers con deuda pendiente (amount_due_yango > 0)"),
    min_debt: Optional[float] = Query(None, ge=0, description="Filtra por deuda mínima (amount_due_yango >= min_debt)"),
    reached_milestone: Optional[str] = Query(None, description="Filtra por milestone alcanzado: 'm1', 'm5', 'm25'"),
    scout_id: Optional[int] = Query(None, description="Filtra por Scout ID (atribución canónica)"),
    week_start: Optional[date] = Query(None, description="Filtra por semana (lunes de la semana ISO)"),
    limit: int = Query(200, ge=1, le=1000, description="Límite de resultados (máx 1000). Default: 200."),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    include_summary: bool = Query(True, description="Incluir resumen ejecutivo en la respuesta"),
    use_materialized: bool = Query(True, description="Usar vista materializada para mejor rendimiento")
):
    """
    Obtiene la fuente de verdad financiera para CABINET (ventana de 14 días).
    
    Esta vista permite determinar con exactitud qué conductores generan pago de Yango
    y detectar deudas por milestones no pagados.
    
    Filtros:
    - only_with_debt: Solo drivers con deuda pendiente (amount_due_yango > 0)
    - min_debt: Filtra por deuda mínima
    - reached_milestone: Filtra por milestone alcanzado ('m1', 'm5', 'm25')
    - limit/offset: Paginación
    - include_summary: Incluir resumen ejecutivo
    - use_materialized: Usar vista materializada (mejor rendimiento, datos pueden estar desactualizados)
    
    Respuesta incluye:
    - meta: Metadatos de paginación
    - summary: Resumen ejecutivo (total esperado, pagado, deuda, porcentaje de cobranza)
    - data: Lista de drivers con información financiera
    
    Ejemplo curl:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d?only_with_debt=true&limit=50"
    ```
    """
    try:
        # Seleccionar vista (materializada enriched o fallback) - con caché para mejor rendimiento
        # Prioridad: MV enriched > MV legacy > vista normal
        if use_materialized:
            if mv_exists(db, "ops", "mv_yango_cabinet_cobranza_enriched_14d"):
                view_name = "ops.mv_yango_cabinet_cobranza_enriched_14d"
                has_scout_fields = True
            elif mv_exists(db, "ops", "mv_cabinet_financial_14d"):
                view_name = "ops.mv_cabinet_financial_14d"
                has_scout_fields = False
            else:
                view_name = "ops.v_cabinet_financial_14d"
                has_scout_fields = False
        else:
            view_name = "ops.v_cabinet_financial_14d"
            has_scout_fields = False
        
        # Construir WHERE dinámico
        where_conditions = []
        params = {}
        
        if only_with_debt:
            where_conditions.append("amount_due_yango > 0")
        
        if min_debt is not None:
            where_conditions.append("amount_due_yango >= :min_debt")
            params["min_debt"] = min_debt
        
        if reached_milestone:
            milestone_lower = reached_milestone.lower()
            if milestone_lower == 'm1':
                # M1: alcanzó M1 pero NO alcanzó M5 (solo M1)
                where_conditions.append("reached_m1_14d = true AND reached_m5_14d = false")
            elif milestone_lower == 'm5':
                # M5: alcanzó M5 pero NO alcanzó M25 (solo M5, o M1+M5)
                where_conditions.append("reached_m5_14d = true AND reached_m25_14d = false")
            elif milestone_lower == 'm25':
                # M25: alcanzó M25 (puede haber alcanzado M1 y M5 también)
                where_conditions.append("reached_m25_14d = true")
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"reached_milestone debe ser 'm1', 'm5' o 'm25', recibido: {reached_milestone}"
                )
        
        # Agregar filtro por scout_id si se proporciona
        if scout_id is not None:
            params["scout_id"] = scout_id
            where_conditions.append("scout_id = :scout_id")
        
        # Agregar filtro por week_start si se proporciona
        if week_start is not None:
            params["week_start"] = week_start
            where_conditions.append("week_start = :week_start")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Verificar si la vista tiene campos de scout (MV enriched vs legacy)
        has_scout_fields = "mv_yango_cabinet_cobranza_enriched_14d" in view_name
        
        if has_scout_fields:
            # Query para MV enriched (ya incluye campos scout)
            query_sql = f"""
                SELECT 
                    driver_id,
                    driver_name,
                    lead_date,
                    iso_week,
                    week_start,
                    connected_flag,
                    connected_date,
                    total_trips_14d,
                    reached_m1_14d,
                    reached_m5_14d,
                    reached_m25_14d,
                    expected_amount_m1,
                    expected_amount_m5,
                    expected_amount_m25,
                    expected_total_yango,
                    claim_m1_exists,
                    claim_m1_paid,
                    claim_m5_exists,
                    claim_m5_paid,
                    claim_m25_exists,
                    claim_m25_paid,
                    paid_amount_m1,
                    paid_amount_m5,
                    paid_amount_m25,
                    total_paid_yango,
                    amount_due_yango,
                    scout_id,
                    scout_name,
                    scout_quality_bucket,
                    is_scout_resolved,
                    scout_source_table,
                    scout_attribution_date,
                    scout_priority,
                    person_key
                FROM {view_name}
                WHERE {where_clause}
                ORDER BY week_start DESC NULLS LAST, lead_date DESC NULLS LAST, driver_id
                LIMIT :limit OFFSET :offset
            """
        else:
            # Query para MV legacy o vista normal (SIN JOIN de scout - campos scout solo disponibles en MV enriched)
            # OPTIMIZACIÓN: Omitir JOIN costoso con v_yango_collection_with_scout cuando no se usa MV enriched
            query_sql = f"""
                SELECT 
                    cf.driver_id,
                    cf.driver_name,
                    cf.lead_date,
                    cf.iso_week,
                    COALESCE(cf.week_start, DATE_TRUNC('week', cf.lead_date)::date) AS week_start,
                    cf.connected_flag,
                    cf.connected_date,
                    cf.total_trips_14d,
                    cf.reached_m1_14d,
                    cf.reached_m5_14d,
                    cf.reached_m25_14d,
                    cf.expected_amount_m1,
                    cf.expected_amount_m5,
                    cf.expected_amount_m25,
                    cf.expected_total_yango,
                    cf.claim_m1_exists,
                    cf.claim_m1_paid,
                    cf.claim_m5_exists,
                    cf.claim_m5_paid,
                    cf.claim_m25_exists,
                    cf.claim_m25_paid,
                    cf.paid_amount_m1,
                    cf.paid_amount_m5,
                    cf.paid_amount_m25,
                    cf.total_paid_yango,
                    cf.amount_due_yango,
                    NULL::INTEGER AS scout_id,
                    NULL::TEXT AS scout_name,
                    NULL::TEXT AS scout_quality_bucket,
                    NULL::BOOLEAN AS is_scout_resolved,
                    NULL::TEXT AS scout_source_table,
                    NULL::DATE AS scout_attribution_date,
                    NULL::INTEGER AS scout_priority,
                    NULL::UUID AS person_key
                FROM {view_name} cf
                WHERE {where_clause}
                ORDER BY COALESCE(cf.week_start, DATE_TRUNC('week', cf.lead_date)::date) DESC NULLS LAST, cf.lead_date DESC NULLS LAST, cf.driver_id
                LIMIT :limit OFFSET :offset
            """
        
        params["limit"] = limit
        params["offset"] = offset
        
        # Ejecutar query
        result = db.execute(text(query_sql), params)
        rows = result.fetchall()
        
        # Convertir a schemas (incluyendo campos de scout)
        data = [CabinetFinancialRow(
            driver_id=row.driver_id,
            driver_name=getattr(row, 'driver_name', None),
            lead_date=row.lead_date,
            iso_week=getattr(row, 'iso_week', None),
            week_start=getattr(row, 'week_start', None),
            connected_flag=row.connected_flag,
            connected_date=row.connected_date,
            total_trips_14d=row.total_trips_14d,
            reached_m1_14d=row.reached_m1_14d,
            reached_m5_14d=row.reached_m5_14d,
            reached_m25_14d=row.reached_m25_14d,
            expected_amount_m1=row.expected_amount_m1,
            expected_amount_m5=row.expected_amount_m5,
            expected_amount_m25=row.expected_amount_m25,
            expected_total_yango=row.expected_total_yango,
            claim_m1_exists=row.claim_m1_exists,
            claim_m1_paid=row.claim_m1_paid,
            claim_m5_exists=row.claim_m5_exists,
            claim_m5_paid=row.claim_m5_paid,
            claim_m25_exists=row.claim_m25_exists,
            claim_m25_paid=row.claim_m25_paid,
            paid_amount_m1=row.paid_amount_m1,
            paid_amount_m5=row.paid_amount_m5,
            paid_amount_m25=row.paid_amount_m25,
            total_paid_yango=row.total_paid_yango,
            amount_due_yango=row.amount_due_yango,
            scout_id=getattr(row, 'scout_id', None),
            scout_name=getattr(row, 'scout_name', None),
            scout_quality_bucket=getattr(row, 'scout_quality_bucket', None),
            is_scout_resolved=bool(getattr(row, 'is_scout_resolved', None) or False),
            scout_source_table=getattr(row, 'scout_source_table', None),
            scout_attribution_date=getattr(row, 'scout_attribution_date', None),
            scout_priority=getattr(row, 'scout_priority', None)
        ) for row in rows]
        
        # COUNT para total
        count_sql = f"SELECT COUNT(*) FROM {view_name} WHERE {where_clause}"
        count_result = db.execute(text(count_sql), {k: v for k, v in params.items() if k not in ['limit', 'offset']})
        total = count_result.scalar() or 0
        
        # Resumen ejecutivo (si se solicita)
        summary = None
        summary_total = None
        if include_summary:
            # Resumen con filtros aplicados
            summary_params = {k: v for k, v in params.items() if k not in ['limit', 'offset']}
            
            if has_scout_fields:
                # Query para MV enriched (campos scout ya incluidos)
                summary_sql = f"""
                    SELECT 
                        COUNT(*) AS total_drivers,
                        COUNT(CASE WHEN expected_total_yango > 0 THEN 1 END) AS drivers_with_expected,
                        COUNT(CASE WHEN amount_due_yango > 0 THEN 1 END) AS drivers_with_debt,
                        COALESCE(SUM(expected_total_yango), 0) AS total_expected_yango,
                        COALESCE(SUM(total_paid_yango), 0) AS total_paid_yango,
                        COALESCE(SUM(amount_due_yango), 0) AS total_debt_yango,
                        CASE 
                            WHEN SUM(expected_total_yango) > 0 
                            THEN ROUND((SUM(total_paid_yango) / SUM(expected_total_yango)) * 100, 2)
                            ELSE 0
                        END AS collection_percentage,
                        COUNT(CASE WHEN reached_m1_14d = true THEN 1 END) AS drivers_m1,
                        COUNT(CASE WHEN reached_m5_14d = true THEN 1 END) AS drivers_m5,
                        COUNT(CASE WHEN reached_m25_14d = true THEN 1 END) AS drivers_m25,
                        COUNT(CASE WHEN scout_id IS NOT NULL THEN 1 END) AS drivers_with_scout,
                        COUNT(CASE WHEN scout_id IS NULL THEN 1 END) AS drivers_without_scout,
                        CASE 
                            WHEN COUNT(*) > 0 
                            THEN ROUND((COUNT(CASE WHEN scout_id IS NOT NULL THEN 1 END)::NUMERIC / COUNT(*)) * 100, 2)
                            ELSE 0
                        END AS pct_with_scout
                    FROM {view_name}
                    WHERE {where_clause}
                """
            else:
                # Query para MV legacy o vista normal (SIN JOIN de scout - campos scout solo disponibles en MV enriched)
                summary_sql = f"""
                    SELECT 
                        COUNT(*) AS total_drivers,
                        COUNT(CASE WHEN cf.expected_total_yango > 0 THEN 1 END) AS drivers_with_expected,
                        COUNT(CASE WHEN cf.amount_due_yango > 0 THEN 1 END) AS drivers_with_debt,
                        COALESCE(SUM(cf.expected_total_yango), 0) AS total_expected_yango,
                        COALESCE(SUM(cf.total_paid_yango), 0) AS total_paid_yango,
                        COALESCE(SUM(cf.amount_due_yango), 0) AS total_debt_yango,
                        CASE 
                            WHEN SUM(cf.expected_total_yango) > 0 
                            THEN ROUND((SUM(cf.total_paid_yango) / SUM(cf.expected_total_yango)) * 100, 2)
                            ELSE 0
                        END AS collection_percentage,
                        COUNT(CASE WHEN cf.reached_m1_14d = true THEN 1 END) AS drivers_m1,
                        COUNT(CASE WHEN cf.reached_m5_14d = true THEN 1 END) AS drivers_m5,
                        COUNT(CASE WHEN cf.reached_m25_14d = true THEN 1 END) AS drivers_m25,
                        0 AS drivers_with_scout,
                        COUNT(*) AS drivers_without_scout,
                        0.0 AS pct_with_scout
                    FROM {view_name} cf
                    WHERE {where_clause}
                """
            
            summary_result = db.execute(text(summary_sql), summary_params)
            summary_row = summary_result.fetchone()
            
            if summary_row:
                summary = CabinetFinancialSummary(
                    total_drivers=summary_row.total_drivers,
                    drivers_with_expected=summary_row.drivers_with_expected,
                    drivers_with_debt=summary_row.drivers_with_debt,
                    total_expected_yango=summary_row.total_expected_yango,
                    total_paid_yango=summary_row.total_paid_yango,
                    total_debt_yango=summary_row.total_debt_yango,
                    collection_percentage=float(summary_row.collection_percentage),
                    drivers_m1=summary_row.drivers_m1,
                    drivers_m5=summary_row.drivers_m5,
                    drivers_m25=summary_row.drivers_m25,
                    drivers_with_scout=summary_row.drivers_with_scout,
                    drivers_without_scout=summary_row.drivers_without_scout,
                    pct_with_scout=float(summary_row.pct_with_scout)
                )
            
            # Resumen total sin filtros (siempre calcular para contexto)
            if has_scout_fields:
                # Query para MV enriched (campos scout ya incluidos)
                summary_total_sql = f"""
                    SELECT 
                        COUNT(*) AS total_drivers,
                        COUNT(CASE WHEN cf.expected_total_yango > 0 THEN 1 END) AS drivers_with_expected,
                        COUNT(CASE WHEN cf.amount_due_yango > 0 THEN 1 END) AS drivers_with_debt,
                        COALESCE(SUM(cf.expected_total_yango), 0) AS total_expected_yango,
                        COALESCE(SUM(cf.total_paid_yango), 0) AS total_paid_yango,
                        COALESCE(SUM(cf.amount_due_yango), 0) AS total_debt_yango,
                        CASE 
                            WHEN SUM(cf.expected_total_yango) > 0 
                            THEN ROUND((SUM(cf.total_paid_yango) / SUM(cf.expected_total_yango)) * 100, 2)
                            ELSE 0
                        END AS collection_percentage,
                        COUNT(CASE WHEN cf.reached_m1_14d = true THEN 1 END) AS drivers_m1,
                        COUNT(CASE WHEN cf.reached_m5_14d = true THEN 1 END) AS drivers_m5,
                        COUNT(CASE WHEN cf.reached_m25_14d = true THEN 1 END) AS drivers_m25,
                        COUNT(CASE WHEN cf.scout_id IS NOT NULL THEN 1 END) AS drivers_with_scout,
                        COUNT(CASE WHEN cf.scout_id IS NULL THEN 1 END) AS drivers_without_scout,
                        CASE 
                            WHEN COUNT(*) > 0 
                            THEN ROUND((COUNT(CASE WHEN cf.scout_id IS NOT NULL THEN 1 END)::NUMERIC / COUNT(*)) * 100, 2)
                            ELSE 0
                        END AS pct_with_scout
                    FROM {view_name} cf
                """
            else:
                # Query para MV legacy o vista normal (SIN JOIN de scout - campos scout solo disponibles en MV enriched)
                summary_total_sql = f"""
                    SELECT 
                        COUNT(*) AS total_drivers,
                        COUNT(CASE WHEN cf.expected_total_yango > 0 THEN 1 END) AS drivers_with_expected,
                        COUNT(CASE WHEN cf.amount_due_yango > 0 THEN 1 END) AS drivers_with_debt,
                        COALESCE(SUM(cf.expected_total_yango), 0) AS total_expected_yango,
                        COALESCE(SUM(cf.total_paid_yango), 0) AS total_paid_yango,
                        COALESCE(SUM(cf.amount_due_yango), 0) AS total_debt_yango,
                        CASE 
                            WHEN SUM(cf.expected_total_yango) > 0 
                            THEN ROUND((SUM(cf.total_paid_yango) / SUM(cf.expected_total_yango)) * 100, 2)
                            ELSE 0
                        END AS collection_percentage,
                        COUNT(CASE WHEN cf.reached_m1_14d = true THEN 1 END) AS drivers_m1,
                        COUNT(CASE WHEN cf.reached_m5_14d = true THEN 1 END) AS drivers_m5,
                        COUNT(CASE WHEN cf.reached_m25_14d = true THEN 1 END) AS drivers_m25,
                        0 AS drivers_with_scout,
                        COUNT(*) AS drivers_without_scout,
                        0.0 AS pct_with_scout
                    FROM {view_name} cf
                """
            summary_total_result = db.execute(text(summary_total_sql))
            summary_total_row = summary_total_result.fetchone()
            
            if summary_total_row:
                summary_total = CabinetFinancialSummaryTotal(
                    total_drivers=summary_total_row.total_drivers,
                    drivers_with_expected=summary_total_row.drivers_with_expected,
                    drivers_with_debt=summary_total_row.drivers_with_debt,
                    total_expected_yango=summary_total_row.total_expected_yango,
                    total_paid_yango=summary_total_row.total_paid_yango,
                    total_debt_yango=summary_total_row.total_debt_yango,
                    collection_percentage=float(summary_total_row.collection_percentage),
                    drivers_m1=summary_total_row.drivers_m1,
                    drivers_m5=summary_total_row.drivers_m5,
                    drivers_m25=summary_total_row.drivers_m25,
                    drivers_with_scout=summary_total_row.drivers_with_scout,
                    drivers_without_scout=summary_total_row.drivers_without_scout,
                    pct_with_scout=float(summary_total_row.pct_with_scout)
                )
        
        # Metadatos
        meta = CabinetFinancialMeta(
            limit=limit,
            offset=offset,
            returned=len(data),
            total=total
        )
        
        return CabinetFinancialResponse(
            meta=meta,
            summary=summary,
            summary_total=summary_total,
            data=data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Hacer rollback si hay una transacción fallida
        try:
            db.rollback()
        except Exception:
            pass
        logger.error(f"Error en get_cabinet_financial_14d: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error interno: {str(e)}"
        )


@router.get("/cabinet-financial-14d/export")
def export_cabinet_financial_14d_csv(
    db: Session = Depends(get_db),
    only_with_debt: bool = Query(False, description="Si true, solo drivers con deuda pendiente"),
    min_debt: Optional[float] = Query(None, ge=0, description="Filtra por deuda mínima"),
    reached_milestone: Optional[str] = Query(None, description="Filtra por milestone: 'm1', 'm5', 'm25'"),
    week_start: Optional[date] = Query(None, description="Filtra por semana (lunes de la semana ISO)"),
    use_materialized: bool = Query(True, description="Usar vista materializada")
):
    """
    Exporta datos de Cabinet Financial 14d a CSV.
    
    Aplica los mismos filtros que el endpoint GET /cabinet-financial-14d
    pero exporta todos los resultados (sin límite de paginación).
    
    Hard cap: 200,000 filas máximo.
    """
    try:
        # Seleccionar vista (prioridad: MV enriched > MV legacy > vista normal)
        if use_materialized:
            check_mv_enriched = db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_matviews 
                    WHERE schemaname = 'ops' 
                    AND matviewname = 'mv_yango_cabinet_cobranza_enriched_14d'
                )
            """))
            mv_enriched_exists = check_mv_enriched.scalar()
            
            if mv_enriched_exists:
                view_name = "ops.mv_yango_cabinet_cobranza_enriched_14d"
                has_scout_fields = True
            else:
                check_mv_legacy = db.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_matviews 
                        WHERE schemaname = 'ops' 
                        AND matviewname = 'mv_cabinet_financial_14d'
                    )
                """))
                mv_legacy_exists = check_mv_legacy.scalar()
                view_name = "ops.mv_cabinet_financial_14d" if mv_legacy_exists else "ops.v_cabinet_financial_14d"
                has_scout_fields = False
        else:
            view_name = "ops.v_cabinet_financial_14d"
            has_scout_fields = False
        
        # Construir WHERE dinámico (mismo que get_cabinet_financial_14d)
        where_conditions = []
        params = {}
        
        if only_with_debt:
            where_conditions.append("amount_due_yango > 0")
        
        if min_debt is not None:
            where_conditions.append("amount_due_yango >= :min_debt")
            params["min_debt"] = min_debt
        
        if reached_milestone:
            milestone_lower = reached_milestone.lower()
            prefix = "" if has_scout_fields else "cf."
            if milestone_lower == 'm1':
                where_conditions.append(f"{prefix}reached_m1_14d = true AND {prefix}reached_m5_14d = false")
            elif milestone_lower == 'm5':
                where_conditions.append(f"{prefix}reached_m5_14d = true AND {prefix}reached_m25_14d = false")
            elif milestone_lower == 'm25':
                where_conditions.append(f"{prefix}reached_m25_14d = true")
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"reached_milestone debe ser 'm1', 'm5' o 'm25', recibido: {reached_milestone}"
                )
        
        if week_start is not None:
            params["week_start"] = week_start
            if has_scout_fields:
                where_conditions.append("week_start = :week_start")
            else:
                where_conditions.append("DATE_TRUNC('week', cf.lead_date)::date = :week_start")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Verificar conteo antes de exportar (hard cap defensivo)
        count_sql = f"""
            SELECT COUNT(*) AS total
            FROM {view_name}
            WHERE {where_clause}
        """
        count_result = db.execute(text(count_sql), params).fetchone()
        total = count_result.total if count_result else 0
        
        if total > 200000:
            raise HTTPException(
                status_code=413,
                detail=f"Export excede límite de 200,000 filas. Total filtrado: {total}. Aplique filtros más restrictivos."
            )
        
        # Query para exportar (todas las columnas con nombres amigables, incluyendo scout)
        if has_scout_fields:
            sql = f"""
            SELECT 
                driver_id AS "Driver ID",
                driver_name AS "Conductor",
                lead_date AS "Lead Date",
                iso_week AS "Semana ISO",
                week_start AS "Semana Inicio",
                connected_flag AS "Conectado",
                connected_date AS "Fecha Conexion",
                total_trips_14d AS "Viajes 14D",
                reached_m1_14d AS "M1 Alcanzado",
                reached_m5_14d AS "M5 Alcanzado",
                reached_m25_14d AS "M25 Alcanzado",
                expected_amount_m1 AS "Esperado M1 (S/)",
                expected_amount_m5 AS "Esperado M5 (S/)",
                expected_amount_m25 AS "Esperado M25 (S/)",
                expected_total_yango AS "Esperado Total (S/)",
                claim_m1_exists AS "Claim M1 Existe",
                claim_m1_paid AS "Claim M1 Pagado",
                claim_m5_exists AS "Claim M5 Existe",
                claim_m5_paid AS "Claim M5 Pagado",
                claim_m25_exists AS "Claim M25 Existe",
                claim_m25_paid AS "Claim M25 Pagado",
                paid_amount_m1 AS "Pagado M1 (S/)",
                paid_amount_m5 AS "Pagado M5 (S/)",
                paid_amount_m25 AS "Pagado M25 (S/)",
                total_paid_yango AS "Pagado Total (S/)",
                amount_due_yango AS "Deuda (S/)",
                scout_id AS "Scout ID",
                scout_name AS "Scout Nombre",
                scout_quality_bucket AS "Calidad Scout",
                scout_source_table AS "Scout Fuente",
                scout_attribution_date AS "Scout Fecha Atribución",
                scout_priority AS "Scout Prioridad"
            FROM {view_name}
            WHERE {where_clause}
            ORDER BY lead_date DESC NULLS LAST, driver_id
            """
        else:
            sql = f"""
            SELECT 
                cf.driver_id AS "Driver ID",
                cf.driver_name AS "Conductor",
                cf.lead_date AS "Lead Date",
                cf.iso_week AS "Semana ISO",
                DATE_TRUNC('week', cf.lead_date)::date AS "Semana Inicio",
                cf.connected_flag AS "Conectado",
                cf.connected_date AS "Fecha Conexion",
                cf.total_trips_14d AS "Viajes 14D",
                cf.reached_m1_14d AS "M1 Alcanzado",
                cf.reached_m5_14d AS "M5 Alcanzado",
                cf.reached_m25_14d AS "M25 Alcanzado",
                cf.expected_amount_m1 AS "Esperado M1 (S/)",
                cf.expected_amount_m5 AS "Esperado M5 (S/)",
                cf.expected_amount_m25 AS "Esperado M25 (S/)",
                cf.expected_total_yango AS "Esperado Total (S/)",
                cf.claim_m1_exists AS "Claim M1 Existe",
                cf.claim_m1_paid AS "Claim M1 Pagado",
                cf.claim_m5_exists AS "Claim M5 Existe",
                cf.claim_m5_paid AS "Claim M5 Pagado",
                cf.claim_m25_exists AS "Claim M25 Existe",
                cf.claim_m25_paid AS "Claim M25 Pagado",
                cf.paid_amount_m1 AS "Pagado M1 (S/)",
                cf.paid_amount_m5 AS "Pagado M5 (S/)",
                cf.paid_amount_m25 AS "Pagado M25 (S/)",
                cf.total_paid_yango AS "Pagado Total (S/)",
                cf.amount_due_yango AS "Deuda (S/)",
                scout.scout_id AS "Scout ID",
                scout.scout_name AS "Scout Nombre",
                scout.scout_quality_bucket AS "Calidad Scout",
                scout.scout_source_table AS "Scout Fuente",
                scout.scout_attribution_date AS "Scout Fecha Atribución",
                scout.scout_priority AS "Scout Prioridad"
            FROM {view_name} cf
            LEFT JOIN LATERAL (
                SELECT DISTINCT ON (driver_id, lead_date)
                    scout_id,
                    scout_name,
                    scout_quality_bucket,
                    scout_source_table,
                    scout_attribution_date,
                    scout_priority
                FROM ops.v_yango_collection_with_scout
                WHERE driver_id = cf.driver_id
                    AND lead_date = cf.lead_date
                    AND scout_id IS NOT NULL
                ORDER BY driver_id, lead_date, 
                    CASE scout_quality_bucket
                        WHEN 'SATISFACTORY_LEDGER' THEN 1
                        WHEN 'EVENTS_ONLY' THEN 2
                        WHEN 'SCOUTING_DAILY_ONLY' THEN 3
                        ELSE 4
                    END,
                    milestone_value
                LIMIT 1
            ) scout ON true
            WHERE {where_clause}
            ORDER BY cf.lead_date DESC NULLS LAST, cf.driver_id
            """
        
        # Obtener datos
        result = db.execute(text(sql), params)
        rows_data = result.mappings().all()
        
        # Generar CSV en memoria
        output = io.StringIO()
        
        if rows_data:
            fieldnames = list(rows_data[0].keys())
            writer = csv.DictWriter(output, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
            writer.writeheader()
            
            for row in rows_data:
                # Convertir valores None a string vacío y prevenir CSV injection
                row_dict = {}
                for k, v in dict(row).items():
                    if v is None:
                        row_dict[k] = ''
                    elif isinstance(v, bool):
                        row_dict[k] = 'Sí' if v else 'No'
                    elif isinstance(v, str) and v and v[0] in ('=', '+', '-', '@'):
                        # Prefijar con ' para prevenir ejecución de fórmulas en Excel
                        row_dict[k] = "'" + v
                    else:
                        row_dict[k] = v
                writer.writerow(row_dict)
        else:
            # CSV vacío con headers (incluyendo scout)
            fieldnames = [
                "Driver ID", "Conductor", "Lead Date", "Semana ISO", "Conectado",
                "Fecha Conexion", "Viajes 14D", "M1 Alcanzado", "M5 Alcanzado", "M25 Alcanzado",
                "Esperado M1 (S/)", "Esperado M5 (S/)", "Esperado M25 (S/)", "Esperado Total (S/)",
                "Claim M1 Existe", "Claim M1 Pagado", "Claim M5 Existe", "Claim M5 Pagado",
                "Claim M25 Existe", "Claim M25 Pagado", "Pagado M1 (S/)", "Pagado M5 (S/)",
                "Pagado M25 (S/)", "Pagado Total (S/)", "Deuda (S/)",
                "Scout ID", "Scout Nombre", "Calidad Scout", "Scout Fuente", "Scout Fecha Atribución", "Scout Prioridad"
            ]
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
        
        csv_content = output.getvalue()
        output.close()
        
        # Generar nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"cabinet_financial_14d_{timestamp}.csv"
        
        # Codificar CSV a bytes UTF-8 con BOM
        csv_bytes = csv_content.encode('utf-8')
        bom_bytes = b'\xef\xbb\xbf'
        csv_content_with_bom = bom_bytes + csv_bytes
        
        # Retornar CSV como respuesta
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
        logger.exception(f"Error de conexion a BD en export cabinet financial CSV: {e}")
        raise HTTPException(
            status_code=503,
            detail="DB no disponible / revisa DATABASE_URL"
        )
    except ProgrammingError as e:
        error_code = getattr(e.orig, 'pgcode', None) if hasattr(e, 'orig') else None
        error_message = str(e.orig) if hasattr(e, 'orig') else str(e)
        
        if error_code == '42P01' or 'does not exist' in error_message.lower():
            logger.exception(f"Vista no existe en export cabinet financial CSV: {e}")
            raise HTTPException(
                status_code=404,
                detail="Falta vista ops.v_cabinet_financial_14d. Aplica backend/sql/ops/v_cabinet_financial_14d.sql"
            )
        logger.exception(f"Error SQL en export cabinet financial CSV: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error SQL: {error_message[:200]}"
        )
    except Exception as e:
        logger.exception(f"Error inesperado en export cabinet financial CSV: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al exportar datos a CSV: {str(e)[:200]}"
        )


@router.get("/yango/cabinet/cobranza-yango/scout-attribution-metrics", response_model=ScoutAttributionMetricsResponse)
def get_scout_attribution_metrics(
    db: Session = Depends(get_db),
    only_with_debt: bool = Query(False, description="Si true, solo drivers con deuda pendiente"),
    min_debt: Optional[float] = Query(None, ge=0, description="Filtra por deuda mínima"),
    reached_milestone: Optional[str] = Query(None, description="Filtra por milestone: 'm1', 'm5', 'm25'"),
    scout_id: Optional[int] = Query(None, description="Filtra por Scout ID"),
    use_materialized: bool = Query(True, description="Usar vista materializada")
):
    """
    Obtiene métricas de atribución scout para Cobranza Yango.
    Endpoint separado con cache de 60s para evitar cálculos pesados en cada request.
    """
    try:
        # Generar clave de cache basada en filtros
        cache_key = (
            only_with_debt,
            min_debt,
            reached_milestone,
            scout_id,
            use_materialized
        )
        
        # Verificar cache
        current_time = time()
        if cache_key in _scout_metrics_cache:
            cached_time, cached_metrics = _scout_metrics_cache[cache_key]
            if current_time - cached_time < CACHE_TTL:
                return ScoutAttributionMetricsResponse(
                    status="ok",
                    metrics=cached_metrics,
                    filters={
                        "only_with_debt": only_with_debt,
                        "min_debt": min_debt,
                        "reached_milestone": reached_milestone,
                        "scout_id": scout_id
                    }
                )
        
        # Seleccionar vista (prioridad: MV enriched > MV legacy > vista normal)
        if use_materialized:
            check_mv_enriched = db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_matviews 
                    WHERE schemaname = 'ops' 
                    AND matviewname = 'mv_yango_cabinet_cobranza_enriched_14d'
                )
            """))
            mv_enriched_exists = check_mv_enriched.scalar()
            
            if mv_enriched_exists:
                view_name = "ops.mv_yango_cabinet_cobranza_enriched_14d"
                has_scout_fields = True
            else:
                check_mv_legacy = db.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_matviews 
                        WHERE schemaname = 'ops' 
                        AND matviewname = 'mv_cabinet_financial_14d'
                    )
                """))
                mv_legacy_exists = check_mv_legacy.scalar()
                view_name = "ops.mv_cabinet_financial_14d" if mv_legacy_exists else "ops.v_cabinet_financial_14d"
                has_scout_fields = False
        else:
            view_name = "ops.v_cabinet_financial_14d"
            has_scout_fields = False
        
        # Construir WHERE conditions
        params = {}
        where_conditions = []
        
        if only_with_debt:
            where_conditions.append("amount_due_yango > 0" if has_scout_fields else "cf.amount_due_yango > 0")
        
        if min_debt is not None:
            params["min_debt"] = min_debt
            where_conditions.append("amount_due_yango >= :min_debt" if has_scout_fields else "cf.amount_due_yango >= :min_debt")
        
        if reached_milestone:
            milestone_lower = reached_milestone.lower()
            if milestone_lower == "m1":
                where_conditions.append("reached_m1_14d = true" if has_scout_fields else "cf.reached_m1_14d = true")
            elif milestone_lower == "m5":
                where_conditions.append("reached_m5_14d = true" if has_scout_fields else "cf.reached_m5_14d = true")
            elif milestone_lower == "m25":
                where_conditions.append("reached_m25_14d = true" if has_scout_fields else "cf.reached_m25_14d = true")
        
        if scout_id is not None:
            params["scout_id"] = scout_id
            where_conditions.append("scout_id = :scout_id" if has_scout_fields else "scout.scout_id = :scout_id")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Query de métricas
        if has_scout_fields:
            metrics_sql = f"""
                SELECT 
                    COUNT(*) AS total_drivers,
                    COUNT(CASE WHEN scout_id IS NOT NULL THEN 1 END) AS drivers_with_scout,
                    COUNT(CASE WHEN scout_id IS NULL THEN 1 END) AS drivers_without_scout,
                    CASE 
                        WHEN COUNT(*) > 0 
                        THEN ROUND((COUNT(CASE WHEN scout_id IS NOT NULL THEN 1 END)::NUMERIC / COUNT(*)) * 100, 2)
                        ELSE 0
                    END AS pct_with_scout,
                    -- Breakdown por quality bucket
                    COUNT(CASE WHEN scout_quality_bucket = 'SATISFACTORY_LEDGER' THEN 1 END) AS quality_ledger,
                    COUNT(CASE WHEN scout_quality_bucket = 'EVENTS_ONLY' THEN 1 END) AS quality_events,
                    COUNT(CASE WHEN scout_quality_bucket = 'MIGRATIONS_ONLY' THEN 1 END) AS quality_migrations,
                    COUNT(CASE WHEN scout_quality_bucket = 'SCOUTING_DAILY_ONLY' THEN 1 END) AS quality_scouting,
                    COUNT(CASE WHEN scout_quality_bucket = 'CABINET_PAYMENTS_ONLY' THEN 1 END) AS quality_cabinet,
                    COUNT(CASE WHEN scout_quality_bucket = 'MISSING' THEN 1 END) AS quality_missing,
                    -- Breakdown por source table
                    COUNT(CASE WHEN scout_source_table = 'observational.lead_ledger' THEN 1 END) AS source_ledger,
                    COUNT(CASE WHEN scout_source_table = 'observational.lead_events' THEN 1 END) AS source_events,
                    COUNT(CASE WHEN scout_source_table LIKE '%migrations%' THEN 1 END) AS source_migrations,
                    COUNT(CASE WHEN scout_source_table LIKE '%scouting_daily%' THEN 1 END) AS source_scouting,
                    COUNT(CASE WHEN scout_source_table LIKE '%cabinet_payments%' THEN 1 END) AS source_cabinet,
                    -- Drivers sin scout por razón
                    COUNT(CASE WHEN scout_id IS NULL AND person_key IS NULL THEN 1 END) AS no_scout_missing_identity,
                    COUNT(CASE WHEN scout_id IS NULL AND person_key IS NOT NULL THEN 1 END) AS no_scout_no_source_match
                FROM {view_name}
                WHERE {where_clause}
            """
        else:
            # Fallback SIN JOIN costoso - solo métricas básicas de la vista financiera
            # Los campos de scout no están disponibles sin la MV enriched
            metrics_sql = f"""
                SELECT 
                    COUNT(*) AS total_drivers,
                    0 AS drivers_with_scout,
                    COUNT(*) AS drivers_without_scout,
                    0.00 AS pct_with_scout,
                    0 AS quality_ledger,
                    0 AS quality_events,
                    0 AS quality_scouting,
                    0 AS quality_migrations,
                    0 AS quality_cabinet,
                    COUNT(*) AS quality_missing,
                    0 AS source_ledger,
                    0 AS source_events,
                    0 AS source_migrations,
                    0 AS source_scouting,
                    0 AS source_cabinet,
                    COUNT(*) AS no_scout_missing_identity,
                    0 AS no_scout_no_source_match
                FROM {view_name} cf
                WHERE {where_clause}
            """
            # NOTA: Sin la MV enriched, no hay datos de scout disponibles.
            # Para obtener métricas de scout completas, crear ops.mv_yango_cabinet_cobranza_enriched_14d
        
        result = db.execute(text(metrics_sql), params)
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=500, detail="No se pudieron calcular las métricas")
        
        # Construir breakdowns
        breakdown_by_quality = {
            "SATISFACTORY_LEDGER": row.quality_ledger or 0,
            "EVENTS_ONLY": row.quality_events or 0,
            "MIGRATIONS_ONLY": row.quality_migrations or 0,
            "SCOUTING_DAILY_ONLY": row.quality_scouting or 0,
            "CABINET_PAYMENTS_ONLY": row.quality_cabinet or 0,
            "MISSING": row.quality_missing or 0
        }
        
        breakdown_by_source = {
            "lead_ledger": row.source_ledger or 0,
            "lead_events": row.source_events or 0,
            "migrations": row.source_migrations or 0,
            "scouting_daily": row.source_scouting or 0,
            "cabinet_payments": row.source_cabinet or 0
        }
        
        drivers_without_scout_by_reason = {
            "missing_identity": row.no_scout_missing_identity or 0,
            "no_source_match": row.no_scout_no_source_match or 0
        }
        
        # Query para top_missing_examples: drivers con milestone pero sin scout
        if has_scout_fields:
            top_missing_sql = f"""
                SELECT 
                    driver_id,
                    lead_date,
                    reached_m1_14d,
                    reached_m5_14d,
                    reached_m25_14d,
                    amount_due_yango
                FROM {view_name}
                WHERE {where_clause}
                    AND scout_id IS NULL
                    AND (reached_m1_14d = true OR reached_m5_14d = true OR reached_m25_14d = true)
                ORDER BY amount_due_yango DESC NULLS LAST, lead_date DESC NULLS LAST
                LIMIT 10
            """
        else:
            # Sin la MV enriched, mostramos los top drivers con milestone y mayor deuda
            # Sin información de scout (requiere la MV para esos datos)
            top_missing_sql = f"""
                SELECT 
                    cf.driver_id,
                    cf.lead_date,
                    cf.reached_m1_14d,
                    cf.reached_m5_14d,
                    cf.reached_m25_14d,
                    cf.amount_due_yango
                FROM {view_name} cf
                WHERE {where_clause}
                    AND (cf.reached_m1_14d = true OR cf.reached_m5_14d = true OR cf.reached_m25_14d = true)
                ORDER BY cf.amount_due_yango DESC NULLS LAST, cf.lead_date DESC NULLS LAST
                LIMIT 10
            """
        
        top_missing_result = db.execute(text(top_missing_sql), params)
        top_missing_rows = top_missing_result.fetchall()
        
        top_missing_examples = [
            {
                "driver_id": r.driver_id,
                "lead_date": r.lead_date.isoformat() if r.lead_date else None,
                "reached_m1": bool(r.reached_m1_14d),
                "reached_m5": bool(r.reached_m5_14d),
                "reached_m25": bool(r.reached_m25_14d),
                "amount_due_yango": float(r.amount_due_yango) if r.amount_due_yango else 0.0
            }
            for r in top_missing_rows
        ]
        
        metrics = ScoutAttributionMetrics(
            total_drivers=row.total_drivers or 0,
            drivers_with_scout=row.drivers_with_scout or 0,
            drivers_without_scout=row.drivers_without_scout or 0,
            pct_with_scout=float(row.pct_with_scout) if row.pct_with_scout else 0.0,
            breakdown_by_quality=breakdown_by_quality,
            breakdown_by_source=breakdown_by_source,
            drivers_without_scout_by_reason=drivers_without_scout_by_reason,
            top_missing_examples=top_missing_examples
        )
        
        # Guardar en cache
        _scout_metrics_cache[cache_key] = (current_time, metrics)
        
        # Limpiar cache expirado (mantener solo últimos 100 entries)
        if len(_scout_metrics_cache) > 100:
            expired_keys = [k for k, (t, _) in _scout_metrics_cache.items() if current_time - t >= CACHE_TTL]
            for k in expired_keys:
                _scout_metrics_cache.pop(k, None)
        
        return ScoutAttributionMetricsResponse(
            status="ok",
            metrics=metrics,
            filters={
                "only_with_debt": only_with_debt,
                "min_debt": min_debt,
                "reached_milestone": reached_milestone,
                "scout_id": scout_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en get_scout_attribution_metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al calcular métricas de scout: {str(e)[:200]}"
        )


@router.get("/yango/cabinet/cobranza-yango/weekly-kpis", response_model=WeeklyKpisResponse)
def get_weekly_kpis(
    db: Session = Depends(get_db),
    only_with_debt: bool = Query(False, description="Si true, solo drivers con deuda pendiente"),
    min_debt: Optional[float] = Query(None, ge=0, description="Filtra por deuda mínima"),
    reached_milestone: Optional[str] = Query(None, description="Filtra por milestone: 'm1', 'm5', 'm25'"),
    scout_id: Optional[int] = Query(None, description="Filtra por Scout ID"),
    scout_quality_bucket: Optional[str] = Query(None, description="Filtra por calidad de scout"),
    week_start_from: Optional[date] = Query(None, description="Filtra desde semana (inclusive)"),
    week_start_to: Optional[date] = Query(None, description="Filtra hasta semana (inclusive)"),
    limit_weeks: int = Query(52, ge=1, le=200, description="Límite de semanas a retornar (default 52, últimas N semanas)"),
    use_materialized: bool = Query(True, description="Usar vista materializada")
):
    """
    Obtiene KPIs agregados por semana para Cobranza Yango.
    Retorna métricas semanales ordenadas DESC (semanas más recientes primero).
    """
    try:
        # Verificar cache primero
        cache_key = (
            only_with_debt,
            min_debt,
            reached_milestone,
            scout_id,
            scout_quality_bucket,
            week_start_from,
            week_start_to,
            limit_weeks,
            use_materialized
        )
        current_time = time()
        if cache_key in _weekly_kpis_cache:
            cached_time, cached_data = _weekly_kpis_cache[cache_key]
            if current_time - cached_time < CACHE_TTL_WEEKLY:
                logger.debug("Returning cached weekly KPIs")
                return cached_data
        
        # Seleccionar vista (prioridad: MV enriched > MV legacy > vista normal)
        if use_materialized:
            check_mv_enriched = db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_matviews 
                    WHERE schemaname = 'ops' 
                    AND matviewname = 'mv_yango_cabinet_cobranza_enriched_14d'
                )
            """))
            mv_enriched_exists = check_mv_enriched.scalar()
            
            if mv_enriched_exists:
                view_name = "ops.mv_yango_cabinet_cobranza_enriched_14d"
                has_week_start = True
            else:
                check_mv_legacy = db.execute(text("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_matviews 
                        WHERE schemaname = 'ops' 
                        AND matviewname = 'mv_cabinet_financial_14d'
                    )
                """))
                mv_legacy_exists = check_mv_legacy.scalar()
                view_name = "ops.mv_cabinet_financial_14d" if mv_legacy_exists else "ops.v_cabinet_financial_14d"
                has_week_start = False
        else:
            view_name = "ops.v_cabinet_financial_14d"
            has_week_start = False
        
        # Construir WHERE conditions
        params = {}
        where_conditions = []
        
        if only_with_debt:
            where_conditions.append("amount_due_yango > 0" if has_week_start else "cf.amount_due_yango > 0")
        
        if min_debt is not None:
            params["min_debt"] = min_debt
            where_conditions.append("amount_due_yango >= :min_debt" if has_week_start else "cf.amount_due_yango >= :min_debt")
        
        if reached_milestone:
            milestone_lower = reached_milestone.lower()
            prefix = "" if has_week_start else "cf."
            if milestone_lower == 'm1':
                where_conditions.append(f"{prefix}reached_m1_14d = true AND {prefix}reached_m5_14d = false")
            elif milestone_lower == 'm5':
                where_conditions.append(f"{prefix}reached_m5_14d = true AND {prefix}reached_m25_14d = false")
            elif milestone_lower == 'm25':
                where_conditions.append(f"{prefix}reached_m25_14d = true")
        
        if scout_id is not None:
            params["scout_id"] = scout_id
            where_conditions.append("scout_id = :scout_id" if has_week_start else "scout.scout_id = :scout_id")
        
        if scout_quality_bucket is not None:
            params["scout_quality_bucket"] = scout_quality_bucket
            where_conditions.append("scout_quality_bucket = :scout_quality_bucket" if has_week_start else "scout.scout_quality_bucket = :scout_quality_bucket")
        
        if week_start_from is not None:
            params["week_start_from"] = week_start_from
            if has_week_start:
                where_conditions.append("week_start >= :week_start_from")
            else:
                where_conditions.append("DATE_TRUNC('week', cf.lead_date)::date >= :week_start_from")
        
        if week_start_to is not None:
            params["week_start_to"] = week_start_to
            if has_week_start:
                where_conditions.append("week_start <= :week_start_to")
            else:
                where_conditions.append("DATE_TRUNC('week', cf.lead_date)::date <= :week_start_to")
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Query de agregación semanal
        if has_week_start:
            metrics_sql = f"""
                SELECT 
                    week_start,
                    COUNT(*) AS total_rows,
                    SUM(amount_due_yango) AS debt_sum,
                    COUNT(CASE WHEN scout_id IS NOT NULL THEN 1 END) AS with_scout,
                    ROUND(COUNT(CASE WHEN scout_id IS NOT NULL THEN 1 END)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) AS pct_with_scout,
                    COUNT(CASE WHEN reached_m1_14d = true THEN 1 END) AS reached_m1,
                    COUNT(CASE WHEN reached_m5_14d = true THEN 1 END) AS reached_m5,
                    COUNT(CASE WHEN reached_m25_14d = true THEN 1 END) AS reached_m25,
                    SUM(total_paid_yango) AS paid_sum,
                    SUM(amount_due_yango) AS unpaid_sum
                FROM {view_name}
                WHERE {where_clause}
                    AND week_start IS NOT NULL
                GROUP BY week_start
                ORDER BY week_start DESC
                LIMIT :limit_weeks
            """
        else:
            # Fallback SIN JOIN costoso - métricas semanales básicas
            # Los campos de scout no están disponibles sin la MV enriched
            metrics_sql = f"""
                SELECT 
                    DATE_TRUNC('week', cf.lead_date)::date AS week_start,
                    COUNT(*) AS total_rows,
                    SUM(cf.amount_due_yango) AS debt_sum,
                    0 AS with_scout,
                    0.00 AS pct_with_scout,
                    COUNT(CASE WHEN cf.reached_m1_14d = true THEN 1 END) AS reached_m1,
                    COUNT(CASE WHEN cf.reached_m5_14d = true THEN 1 END) AS reached_m5,
                    COUNT(CASE WHEN cf.reached_m25_14d = true THEN 1 END) AS reached_m25,
                    SUM(cf.total_paid_yango) AS paid_sum,
                    SUM(cf.amount_due_yango) AS unpaid_sum
                FROM {view_name} cf
                WHERE {where_clause}
                    AND cf.lead_date IS NOT NULL
                GROUP BY DATE_TRUNC('week', cf.lead_date)::date
                ORDER BY week_start DESC
                LIMIT :limit_weeks
            """
            # NOTA: Sin la MV enriched, with_scout=0. Para métricas de scout, crear la MV.
        
        params["limit_weeks"] = limit_weeks
        
        result = db.execute(text(metrics_sql), params)
        rows = result.fetchall()
        
        weeks = [WeeklyKpiRow(
            week_start=row.week_start,
            total_rows=row.total_rows or 0,
            debt_sum=Decimal(str(row.debt_sum or 0)),
            with_scout=row.with_scout or 0,
            pct_with_scout=float(row.pct_with_scout) if row.pct_with_scout else 0.0,
            reached_m1=row.reached_m1 or 0,
            reached_m5=row.reached_m5 or 0,
            reached_m25=row.reached_m25 or 0,
            paid_sum=Decimal(str(row.paid_sum or 0)),
            unpaid_sum=Decimal(str(row.unpaid_sum or 0))
        ) for row in rows]
        
        result = WeeklyKpisResponse(
            status="ok",
            weeks=weeks,
            filters={
                "only_with_debt": only_with_debt,
                "min_debt": min_debt,
                "reached_milestone": reached_milestone,
                "scout_id": scout_id,
                "scout_quality_bucket": scout_quality_bucket,
                "week_start_from": week_start_from.isoformat() if week_start_from else None,
                "week_start_to": week_start_to.isoformat() if week_start_to else None,
                "limit_weeks": limit_weeks
            }
        )
        
        # Guardar en cache
        _weekly_kpis_cache[cache_key] = (current_time, result)
        
        # Limpiar cache expirado (mantener solo últimos 50 entries)
        if len(_weekly_kpis_cache) > 50:
            expired_keys = [k for k, (t, _) in _weekly_kpis_cache.items() if current_time - t >= CACHE_TTL_WEEKLY]
            for k in expired_keys:
                _weekly_kpis_cache.pop(k, None)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en get_weekly_kpis: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al calcular KPIs semanales: {str(e)[:200]}"
        )


@router.get("/cabinet-financial-14d/funnel-gap")
def get_funnel_gap_metrics(db: Session = Depends(get_db)):
    """Métricas del primer gap del embudo: leads sin identidad ni pago."""
    try:
        return service_get_funnel_gap_metrics(db)
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.error("Error calculando métricas del gap del embudo: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculando métricas del gap: {str(e)[:200]}") from e


@router.get("/cabinet-financial-14d/kpi-red-recovery-metrics", response_model=KpiRedRecoveryMetricsResponse)
def get_kpi_red_recovery_metrics(db: Session = Depends(get_db)):
    """Métricas de recovery del KPI rojo."""
    try:
        return service_get_kpi_red_recovery_metrics(db)
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.error("Error calculando métricas de recovery del KPI rojo: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculando métricas de recovery: {str(e)[:200]}") from e


@router.get("/cabinet-financial-14d/claims-audit-summary")
def get_claims_audit_summary(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100, description="Límite de casos a mostrar"),
):
    """Resumen de auditoría de claims: drivers elegibles sin claims generados."""
    try:
        return service_get_claims_audit_summary(db, limit=limit)
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.error("Error obteniendo resumen de auditoría de claims: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo auditoría de claims: {str(e)[:200]}") from e


@router.get("/cabinet-financial-14d/limbo", response_model=CabinetLimboResponse)
def get_cabinet_limbo(
    db: Session = Depends(get_db),
    limbo_stage: Optional[str] = Query(None, description="Filtra por limbo_stage: NO_IDENTITY, NO_DRIVER, NO_TRIPS_14D, TRIPS_NO_CLAIM, OK"),
    week_start: Optional[date] = Query(None, description="Filtra por semana (lunes de la semana ISO)"),
    lead_date_from: Optional[date] = Query(None, description="Filtra por lead_date desde"),
    lead_date_to: Optional[date] = Query(None, description="Filtra por lead_date hasta"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de resultados (máx 1000). Default: 100."),
    offset: int = Query(0, ge=0, description="Offset para paginación")
):
    """
    Obtiene leads de cabinet en limbo (LEAD-FIRST).
    
    Esta vista muestra TODOS los leads de cabinet (incluyendo limbo) con su etapa exacta
    en el embudo. Identifica leads que no avanzan.
    
    Filtros:
    - limbo_stage: Filtra por etapa de limbo
    - week_start: Filtra por semana (lunes de la semana ISO)
    - lead_date_from/to: Filtra por rango de fechas
    - limit/offset: Paginación
    
    Respuesta incluye:
    - meta: Metadatos de paginación
    - summary: Resumen de leads en limbo por etapa
    - data: Lista de leads con información de limbo
    
    Ejemplo curl:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d/limbo?limbo_stage=NO_IDENTITY&limit=50"
    ```
    """
    try:
        # Construir WHERE dinámico
        where_conditions = []
        params = {}
        
        if limbo_stage:
            valid_stages = ['NO_IDENTITY', 'NO_DRIVER', 'NO_TRIPS_14D', 'TRIPS_NO_CLAIM', 'OK']
            if limbo_stage not in valid_stages:
                raise HTTPException(
                    status_code=400,
                    detail=f"limbo_stage debe ser uno de: {', '.join(valid_stages)}"
                )
            where_conditions.append("limbo_stage = :limbo_stage")
            params["limbo_stage"] = limbo_stage
        
        if week_start:
            where_conditions.append("week_start = :week_start")
            params["week_start"] = week_start
        
        if lead_date_from:
            where_conditions.append("lead_date >= :lead_date_from")
            params["lead_date_from"] = lead_date_from
        
        if lead_date_to:
            where_conditions.append("lead_date <= :lead_date_to")
            params["lead_date_to"] = lead_date_to
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        params["limit"] = limit
        params["offset"] = offset
        
        # OPTIMIZATION: Single query with window function for total count and summary
        # This avoids 3 separate scans of the view
        combined_query = text(f"""
            WITH filtered_data AS (
                SELECT 
                    lead_id,
                    lead_source_pk,
                    lead_date,
                    week_start,
                    park_phone,
                    asset_plate_number,
                    lead_name,
                    person_key::text AS person_key,
                    driver_id,
                    trips_14d,
                    window_end_14d,
                    reached_m1_14d,
                    reached_m5_14d,
                    reached_m25_14d,
                    expected_amount_14d,
                    has_claim_m1,
                    has_claim_m5,
                    has_claim_m25,
                    limbo_stage,
                    limbo_reason_detail
                FROM ops.v_cabinet_leads_limbo
                WHERE {where_clause}
            ),
            summary_stats AS (
                SELECT
                    COUNT(*) AS total_leads,
                    COUNT(*) FILTER (WHERE limbo_stage = 'NO_IDENTITY') AS limbo_no_identity,
                    COUNT(*) FILTER (WHERE limbo_stage = 'NO_DRIVER') AS limbo_no_driver,
                    COUNT(*) FILTER (WHERE limbo_stage = 'NO_TRIPS_14D') AS limbo_no_trips_14d,
                    COUNT(*) FILTER (WHERE limbo_stage = 'TRIPS_NO_CLAIM') AS limbo_trips_no_claim,
                    COUNT(*) FILTER (WHERE limbo_stage = 'OK') AS limbo_ok
                FROM filtered_data
            ),
            paginated_data AS (
                SELECT *
                FROM filtered_data
                ORDER BY week_start DESC, lead_date DESC, lead_id
                LIMIT :limit OFFSET :offset
            )
            SELECT 
                'summary' AS row_type,
                NULL AS lead_id,
                NULL AS lead_source_pk,
                NULL::date AS lead_date,
                NULL::date AS week_start,
                NULL AS park_phone,
                NULL AS asset_plate_number,
                NULL AS lead_name,
                NULL AS person_key,
                NULL AS driver_id,
                NULL::int AS trips_14d,
                NULL::date AS window_end_14d,
                NULL::bool AS reached_m1_14d,
                NULL::bool AS reached_m5_14d,
                NULL::bool AS reached_m25_14d,
                NULL::numeric AS expected_amount_14d,
                NULL::bool AS has_claim_m1,
                NULL::bool AS has_claim_m5,
                NULL::bool AS has_claim_m25,
                NULL AS limbo_stage,
                NULL AS limbo_reason_detail,
                total_leads::int,
                limbo_no_identity::int,
                limbo_no_driver::int,
                limbo_no_trips_14d::int,
                limbo_trips_no_claim::int,
                limbo_ok::int
            FROM summary_stats
            UNION ALL
            SELECT 
                'data' AS row_type,
                lead_id,
                lead_source_pk,
                lead_date,
                week_start,
                park_phone,
                asset_plate_number,
                lead_name,
                person_key,
                driver_id,
                trips_14d,
                window_end_14d,
                reached_m1_14d,
                reached_m5_14d,
                reached_m25_14d,
                expected_amount_14d,
                has_claim_m1,
                has_claim_m5,
                has_claim_m25,
                limbo_stage,
                limbo_reason_detail,
                NULL::int AS total_leads,
                NULL::int AS limbo_no_identity,
                NULL::int AS limbo_no_driver,
                NULL::int AS limbo_no_trips_14d,
                NULL::int AS limbo_trips_no_claim,
                NULL::int AS limbo_ok
            FROM paginated_data
        """)
        
        result = db.execute(combined_query, params)
        rows = result.fetchall()
        
        # Parse results - first row is summary, rest is data
        summary_row = None
        data = []
        for row in rows:
            if row.row_type == 'summary':
                summary_row = row
            else:
                data.append({
                    "lead_id": row.lead_id,
                    "lead_source_pk": row.lead_source_pk,
                    "lead_date": row.lead_date,
                    "week_start": row.week_start,
                    "park_phone": row.park_phone,
                    "asset_plate_number": row.asset_plate_number,
                    "lead_name": row.lead_name,
                    "person_key": row.person_key,
                    "driver_id": row.driver_id,
                    "trips_14d": row.trips_14d or 0,
                    "window_end_14d": row.window_end_14d,
                    "reached_m1_14d": row.reached_m1_14d or False,
                    "reached_m5_14d": row.reached_m5_14d or False,
                    "reached_m25_14d": row.reached_m25_14d or False,
                    "expected_amount_14d": row.expected_amount_14d or 0,
                    "has_claim_m1": row.has_claim_m1 or False,
                    "has_claim_m5": row.has_claim_m5 or False,
                    "has_claim_m25": row.has_claim_m25 or False,
                    "limbo_stage": row.limbo_stage,
                    "limbo_reason_detail": row.limbo_reason_detail
                })
        
        # Extract summary and total
        total = summary_row.total_leads if summary_row else 0
        
        summary = CabinetLimboSummary(
            total_leads=summary_row.total_leads or 0,
            limbo_no_identity=summary_row.limbo_no_identity or 0,
            limbo_no_driver=summary_row.limbo_no_driver or 0,
            limbo_no_trips_14d=summary_row.limbo_no_trips_14d or 0,
            limbo_trips_no_claim=summary_row.limbo_trips_no_claim or 0,
            limbo_ok=summary_row.limbo_ok or 0
        )
        
        meta = CabinetLimboMeta(
            limit=limit,
            offset=offset,
            returned=len(data),
            total=total
        )
        
        return CabinetLimboResponse(
            meta=meta,
            summary=summary,
            data=[CabinetLimboRow(**row) for row in data]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.error(f"Error obteniendo leads en limbo: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo leads en limbo: {str(e)[:200]}"
        )


@router.get("/cabinet-financial-14d/limbo/export")
def export_cabinet_limbo_csv(
    db: Session = Depends(get_db),
    limbo_stage: Optional[str] = Query(None, description="Filtra por limbo_stage"),
    week_start: Optional[date] = Query(None, description="Filtra por semana"),
    lead_date_from: Optional[date] = Query(None, description="Filtra por lead_date desde"),
    lead_date_to: Optional[date] = Query(None, description="Filtra por lead_date hasta"),
    limit: int = Query(10000, ge=1, le=50000, description="Límite de resultados para export (máx 50000)")
):
    """
    Exporta leads en limbo a CSV.
    """
    try:
        from fastapi.responses import StreamingResponse
        import io
        import csv
        
        # Construir WHERE dinámico (mismo que get_cabinet_limbo)
        where_conditions = []
        params = {}
        
        if limbo_stage:
            valid_stages = ['NO_IDENTITY', 'NO_DRIVER', 'NO_TRIPS_14D', 'TRIPS_NO_CLAIM', 'OK']
            if limbo_stage not in valid_stages:
                raise HTTPException(status_code=400, detail=f"limbo_stage debe ser uno de: {', '.join(valid_stages)}")
            where_conditions.append("limbo_stage = :limbo_stage")
            params["limbo_stage"] = limbo_stage
        
        if week_start:
            where_conditions.append("week_start = :week_start")
            params["week_start"] = week_start
        
        if lead_date_from:
            where_conditions.append("lead_date >= :lead_date_from")
            params["lead_date_from"] = lead_date_from
        
        if lead_date_to:
            where_conditions.append("lead_date <= :lead_date_to")
            params["lead_date_to"] = lead_date_to
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        params["limit"] = limit
        
        # Query para datos
        data_query = text(f"""
            SELECT 
                lead_id,
                lead_source_pk,
                lead_date,
                week_start,
                park_phone,
                asset_plate_number,
                lead_name,
                person_key::text AS person_key,
                driver_id,
                trips_14d,
                window_end_14d,
                reached_m1_14d,
                reached_m5_14d,
                reached_m25_14d,
                expected_amount_14d,
                has_claim_m1,
                has_claim_m5,
                has_claim_m25,
                limbo_stage,
                limbo_reason_detail
            FROM ops.v_cabinet_leads_limbo
            WHERE {where_clause}
            ORDER BY week_start DESC, lead_date DESC, lead_id
            LIMIT :limit
        """)
        
        result = db.execute(data_query, params)
        rows = result.fetchall()
        
        # Crear CSV en memoria
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'lead_id', 'lead_source_pk', 'lead_date', 'week_start',
            'park_phone', 'asset_plate_number', 'lead_name',
            'person_key', 'driver_id', 'trips_14d', 'window_end_14d',
            'reached_m1_14d', 'reached_m5_14d', 'reached_m25_14d',
            'expected_amount_14d', 'has_claim_m1', 'has_claim_m5', 'has_claim_m25',
            'limbo_stage', 'limbo_reason_detail'
        ])
        
        # Data
        for row in rows:
            writer.writerow([
                row.lead_id,
                row.lead_source_pk,
                row.lead_date.isoformat() if row.lead_date else '',
                row.week_start.isoformat() if row.week_start else '',
                row.park_phone or '',
                row.asset_plate_number or '',
                row.lead_name or '',
                row.person_key or '',
                row.driver_id or '',
                row.trips_14d or 0,
                row.window_end_14d.isoformat() if row.window_end_14d else '',
                row.reached_m1_14d or False,
                row.reached_m5_14d or False,
                row.reached_m25_14d or False,
                float(row.expected_amount_14d) if row.expected_amount_14d else 0,
                row.has_claim_m1 or False,
                row.has_claim_m5 or False,
                row.has_claim_m25 or False,
                row.limbo_stage,
                row.limbo_reason_detail or ''
            ])
        
        output.seek(0)
        
        from datetime import datetime
        filename = f"cabinet_limbo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.error(f"Error exportando leads en limbo: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error exportando leads en limbo: {str(e)[:200]}"
        )


@router.get("/cabinet-financial-14d/claims-gap", response_model=CabinetClaimsGapResponse)
def get_cabinet_claims_gap(
    db: Session = Depends(get_db),
    gap_reason: Optional[str] = Query(None, description="Filtra por gap_reason"),
    week_start: Optional[date] = Query(None, description="Filtra por semana (lunes de la semana ISO)"),
    lead_date_from: Optional[date] = Query(None, description="Filtra por lead_date desde"),
    lead_date_to: Optional[date] = Query(None, description="Filtra por lead_date hasta"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone_value (1, 5, 25)"),
    limit: int = Query(100, ge=1, le=1000, description="Límite de resultados (máx 1000). Default: 100."),
    offset: int = Query(0, ge=0, description="Offset para paginación")
):
    """
    Obtiene gaps de claims de cabinet 14d (CLAIM-FIRST).
    
    Esta vista identifica drivers con milestones alcanzados dentro de ventana 14d
    pero SIN claim correspondiente.
    
    Filtros:
    - gap_reason: Filtra por razón del gap
    - week_start: Filtra por semana (lunes de la semana ISO)
    - lead_date_from/to: Filtra por rango de fechas
    - milestone_value: Filtra por milestone (1, 5, 25)
    - limit/offset: Paginación
    
    Respuesta incluye:
    - meta: Metadatos de paginación
    - summary: Resumen de gaps por razón y milestone
    - data: Lista de gaps con información detallada
    
    Ejemplo curl:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d/claims-gap?gap_reason=MILESTONE_ACHIEVED_NO_CLAIM&limit=50"
    ```
    """
    try:
        # Construir WHERE dinámico
        where_conditions = []
        params = {}
        
        if gap_reason:
            valid_reasons = ['CLAIM_NOT_GENERATED', 'OK', 'NO_IDENTITY', 'NO_DRIVER', 'INSUFFICIENT_TRIPS', 'OTHER']
            if gap_reason not in valid_reasons:
                raise HTTPException(
                    status_code=400,
                    detail=f"gap_reason debe ser uno de: {', '.join(valid_reasons)}"
                )
            where_conditions.append("gap_reason = :gap_reason")
            params["gap_reason"] = gap_reason
        
        if week_start:
            where_conditions.append("week_start = :week_start")
            params["week_start"] = week_start
        
        if lead_date_from:
            where_conditions.append("lead_date >= :lead_date_from")
            params["lead_date_from"] = lead_date_from
        
        if lead_date_to:
            where_conditions.append("lead_date <= :lead_date_to")
            params["lead_date_to"] = lead_date_to
        
        if milestone_value:
            if milestone_value not in [1, 5, 25]:
                raise HTTPException(status_code=400, detail="milestone_value debe ser 1, 5 o 25")
            where_conditions.append("milestone_value = :milestone_value")
            params["milestone_value"] = milestone_value
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        
        # Query para total (sin limit/offset)
        count_query = text(f"""
            SELECT COUNT(*) 
            FROM ops.v_cabinet_claims_gap_14d
            WHERE {where_clause}
        """)
        total_result = db.execute(count_query, params)
        total = total_result.scalar() or 0
        
        # Query para datos (con limit/offset y orden)
        data_query = text(f"""
            SELECT 
                lead_id,
                lead_source_pk,
                driver_id,
                person_key::text AS person_key,
                lead_date,
                week_start,
                milestone_value,
                trips_14d,
                milestone_achieved,
                expected_amount,
                claim_expected,
                claim_exists,
                claim_status,
                gap_reason
            FROM ops.v_cabinet_claims_gap_14d
            WHERE {where_clause}
            ORDER BY week_start DESC, lead_date DESC, milestone_value DESC
            LIMIT :limit OFFSET :offset
        """)
        params["limit"] = limit
        params["offset"] = offset
        
        result = db.execute(data_query, params)
        rows = result.fetchall()
        
        # Convertir a dict
        data = []
        for row in rows:
            data.append({
                "lead_id": row.lead_id,
                "lead_source_pk": row.lead_source_pk,
                "driver_id": row.driver_id,
                "person_key": row.person_key,
                "lead_date": row.lead_date.isoformat() if row.lead_date else None,
                "week_start": row.week_start.isoformat() if row.week_start else None,
                "milestone_value": row.milestone_value,
                "trips_14d": row.trips_14d or 0,
                "milestone_achieved": row.milestone_achieved or False,
                "expected_amount": float(row.expected_amount) if row.expected_amount else 0,
                "claim_expected": row.claim_expected or False,
                "claim_exists": row.claim_exists or False,
                "claim_status": row.claim_status,
                "gap_reason": row.gap_reason
            })
        
        # Query para summary (conteos por gap_reason y milestone_value)
        summary_query = text(f"""
            SELECT 
                COUNT(*) AS total_gaps,
                COUNT(*) FILTER (WHERE gap_reason = 'CLAIM_NOT_GENERATED') AS gaps_milestone_achieved_no_claim,
                COUNT(*) FILTER (WHERE gap_reason = 'OK') AS gaps_claim_exists,
                COUNT(*) FILTER (WHERE gap_reason = 'INSUFFICIENT_TRIPS') AS gaps_milestone_not_achieved,
                COUNT(*) FILTER (WHERE milestone_value = 1) AS gaps_m1,
                COUNT(*) FILTER (WHERE milestone_value = 5) AS gaps_m5,
                COUNT(*) FILTER (WHERE milestone_value = 25) AS gaps_m25,
                SUM(expected_amount) AS total_expected_amount
            FROM ops.v_cabinet_claims_gap_14d
            WHERE {where_clause}
        """)
        summary_result = db.execute(summary_query, params)
        summary_row = summary_result.fetchone()
        
        summary = CabinetClaimsGapSummary(
            total_gaps=summary_row.total_gaps or 0,
            gaps_milestone_achieved_no_claim=summary_row.gaps_milestone_achieved_no_claim or 0,
            gaps_claim_exists=summary_row.gaps_claim_exists or 0,
            gaps_milestone_not_achieved=summary_row.gaps_milestone_not_achieved or 0,
            gaps_m1=summary_row.gaps_m1 or 0,
            gaps_m5=summary_row.gaps_m5 or 0,
            gaps_m25=summary_row.gaps_m25 or 0,
            total_expected_amount=summary_row.total_expected_amount or 0
        )
        
        meta = CabinetClaimsGapMeta(
            limit=limit,
            offset=offset,
            returned=len(data),
            total=total
        )
        
        return CabinetClaimsGapResponse(
            meta=meta,
            summary=summary,
            data=[CabinetClaimsGapRow(**row) for row in data]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.error(f"Error obteniendo gaps de claims: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo gaps de claims: {str(e)[:200]}"
        )


@router.get("/cabinet-financial-14d/claims-gap/summary", response_model=Dict)
def get_cabinet_claims_gap_summary(
    db: Session = Depends(get_db),
    week_start: Optional[date] = Query(None, description="Filtra por semana (opcional)")
):
    """
    Obtiene resumen de gaps de claims de cabinet 14d.
    
    Devuelve:
    - counts por gap_reason
    - counts por milestone
    - monto_total_expected_missing (sum expected_amount donde CLAIM_NOT_GENERATED)
    - monto_total_expected_ok
    - por semana si week_start no null (opcional)
    """
    try:
        where_clause = "1=1"
        params = {}
        
        if week_start:
            where_clause = "week_start = :week_start"
            params["week_start"] = week_start
        
        query = text(f"""
            SELECT 
                COUNT(*) AS total_gaps,
                COUNT(*) FILTER (WHERE gap_reason = 'CLAIM_NOT_GENERATED') AS gaps_claim_not_generated,
                COUNT(*) FILTER (WHERE gap_reason = 'OK') AS gaps_ok,
                COUNT(*) FILTER (WHERE gap_reason = 'NO_IDENTITY') AS gaps_no_identity,
                COUNT(*) FILTER (WHERE gap_reason = 'NO_DRIVER') AS gaps_no_driver,
                COUNT(*) FILTER (WHERE gap_reason = 'INSUFFICIENT_TRIPS') AS gaps_insufficient_trips,
                COUNT(*) FILTER (WHERE milestone_value = 1) AS gaps_m1,
                COUNT(*) FILTER (WHERE milestone_value = 5) AS gaps_m5,
                COUNT(*) FILTER (WHERE milestone_value = 25) AS gaps_m25,
                SUM(expected_amount) FILTER (WHERE gap_reason = 'CLAIM_NOT_GENERATED') AS monto_total_expected_missing,
                SUM(expected_amount) FILTER (WHERE gap_reason = 'OK') AS monto_total_expected_ok
            FROM ops.v_cabinet_claims_gap_14d
            WHERE {where_clause}
        """)
        
        result = db.execute(query, params)
        row = result.fetchone()
        
        return {
            "total_gaps": row.total_gaps or 0,
            "gaps_claim_not_generated": row.gaps_claim_not_generated or 0,
            "gaps_ok": row.gaps_ok or 0,
            "gaps_no_identity": row.gaps_no_identity or 0,
            "gaps_no_driver": row.gaps_no_driver or 0,
            "gaps_insufficient_trips": row.gaps_insufficient_trips or 0,
            "gaps_m1": row.gaps_m1 or 0,
            "gaps_m5": row.gaps_m5 or 0,
            "gaps_m25": row.gaps_m25 or 0,
            "monto_total_expected_missing": float(row.monto_total_expected_missing) if row.monto_total_expected_missing else 0,
            "monto_total_expected_ok": float(row.monto_total_expected_ok) if row.monto_total_expected_ok else 0,
            "week_start": week_start.isoformat() if week_start else None
        }
        
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.error(f"Error obteniendo summary de gaps: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo summary de gaps: {str(e)[:200]}"
        )


@router.get("/cabinet-financial-14d/claims-gap/export")
def export_cabinet_claims_gap_csv(
    db: Session = Depends(get_db),
    gap_reason: Optional[str] = Query(None, description="Filtra por gap_reason"),
    week_start: Optional[date] = Query(None, description="Filtra por semana"),
    lead_date_from: Optional[date] = Query(None, description="Filtra por lead_date desde"),
    lead_date_to: Optional[date] = Query(None, description="Filtra por lead_date hasta"),
    milestone_value: Optional[int] = Query(None, description="Filtra por milestone_value"),
    limit: int = Query(10000, ge=1, le=50000, description="Límite de resultados para export (máx 50000)")
):
    """
    Exporta gaps de claims a CSV.
    """
    try:
        from fastapi.responses import StreamingResponse
        import io
        import csv
        
        # Construir WHERE dinámico (mismo que get_cabinet_claims_gap)
        where_conditions = []
        params = {}
        
        if gap_reason:
            where_conditions.append("gap_reason = :gap_reason")
            params["gap_reason"] = gap_reason
        
        if week_start:
            where_conditions.append("week_start = :week_start")
            params["week_start"] = week_start
        
        if lead_date_from:
            where_conditions.append("lead_date >= :lead_date_from")
            params["lead_date_from"] = lead_date_from
        
        if lead_date_to:
            where_conditions.append("lead_date <= :lead_date_to")
            params["lead_date_to"] = lead_date_to
        
        if milestone_value:
            where_conditions.append("milestone_value = :milestone_value")
            params["milestone_value"] = milestone_value
        
        where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
        params["limit"] = limit
        
        # Query para datos
        data_query = text(f"""
            SELECT 
                lead_id,
                lead_source_pk,
                driver_id,
                person_key::text AS person_key,
                lead_date,
                week_start,
                milestone_value,
                trips_14d,
                milestone_achieved,
                expected_amount,
                claim_expected,
                claim_exists,
                claim_status,
                gap_reason
            FROM ops.v_cabinet_claims_gap_14d
            WHERE {where_clause}
            ORDER BY week_start DESC, lead_date DESC, milestone_value DESC
            LIMIT :limit
        """)
        
        result = db.execute(data_query, params)
        rows = result.fetchall()
        
        # Crear CSV en memoria
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Headers
        writer.writerow([
            'lead_id', 'lead_source_pk', 'driver_id', 'person_key', 'lead_date', 'week_start',
            'milestone_value', 'trips_14d', 'milestone_achieved', 'expected_amount',
            'claim_expected', 'claim_exists', 'claim_status', 'gap_reason'
        ])
        
        # Data
        for row in rows:
            writer.writerow([
                row.lead_id,
                row.lead_source_pk,
                row.driver_id or '',
                row.person_key or '',
                row.lead_date.isoformat() if row.lead_date else '',
                row.week_start.isoformat() if row.week_start else '',
                row.milestone_value,
                row.trips_14d or 0,
                row.milestone_achieved or False,
                float(row.expected_amount) if row.expected_amount else 0,
                row.claim_expected or False,
                row.claim_exists or False,
                row.claim_status,
                row.gap_reason
            ])
        
        output.seek(0)
        
        from datetime import datetime
        filename = f"cabinet_claims_gap_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        logger.error(f"Error exportando gaps de claims: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error exportando gaps de claims: {str(e)[:200]}"
        )

