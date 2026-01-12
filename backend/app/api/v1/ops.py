"""
Endpoints para operaciones del sistema
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import datetime, date, timezone
import logging

from app.db import get_db
from app.models.ops import Alert, AlertSeverity
from app.schemas.ops_alerts import OpsAlertsResponse, OpsAlertRow, AlertSeverity as AlertSeveritySchema
from app.schemas.ops_data_health import IdentitySystemHealthRow
from app.schemas.ops_raw_health import (
    RawDataHealthStatusResponse,
    RawDataHealthStatusRow,
    RawDataFreshnessStatusResponse,
    RawDataFreshnessStatusRow,
    RawDataIngestionDailyResponse,
    RawDataIngestionDailyRow,
)
from app.schemas.ops_mv_health import MvHealthResponse, MvHealthRow
from app.schemas.ops_health_checks import HealthChecksResponse, HealthCheckRow
from app.schemas.ops_health_global import HealthGlobalResponse
from app.schemas.ops_source_registry import SourceRegistryResponse, SourceRegistryRow
from app.schemas.ops_source_registry import SourceRegistryResponse, SourceRegistryRow
from app.api.v1 import ops_payments
from app.schemas.identity_gap import (
    IdentityGapResponse,
    IdentityGapRow,
    IdentityGapTotals,
    IdentityGapBreakdown,
    IdentityGapAlertsResponse,
    IdentityGapAlertRow
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Incluir subrouter de payments
router.include_router(ops_payments.router, prefix="/payments", tags=["ops-payments"])


@router.get("/health")
def ops_health():
    """
    Health check para el módulo de operaciones
    """
    return {"status": "ok", "module": "ops"}


@router.get("/alerts", response_model=OpsAlertsResponse)
def list_alerts(
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=200, description="Número de resultados por página"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    severity: Optional[AlertSeveritySchema] = Query(None, description="Filtrar por severidad (info, warning, error)"),
    acknowledged: Optional[bool] = Query(None, description="Filtrar por estado de reconocimiento (true/false)"),
    week_label: Optional[str] = Query(None, description="Filtrar por semana ISO (ej: 2025-W51)")
):
    """
    Lista alertas operacionales con paginación y filtros.
    
    Retorna un listado paginado de alertas ordenadas por fecha de creación
    descendente (más recientes primero).
    
    Ejemplo curl (sin filtros):
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/alerts?limit=20&offset=0"
    ```
    
    Ejemplo curl (con filtros):
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/alerts?limit=10&offset=0&severity=warning&acknowledged=false&week_label=2025-W51"
    ```
    
    Args:
        limit: Número máximo de resultados (1-200, default: 20)
        offset: Número de resultados a saltar (default: 0)
        severity: Filtrar por severidad (info, warning, error)
        acknowledged: Filtrar por reconocimiento (true: reconocidas, false: no reconocidas)
        week_label: Filtrar por semana ISO (formato: YYYY-WNN)
    
    Returns:
        OpsAlertsResponse con items, total, limit y offset
    """
    try:
        # Construir query base
        query = db.query(Alert)
        
        # Filtrar por severity si se proporciona
        if severity:
            # Convertir AlertSeveritySchema a AlertSeverity del modelo
            severity_value = None
            if severity == AlertSeveritySchema.INFO:
                severity_value = AlertSeverity.INFO
            elif severity == AlertSeveritySchema.WARNING:
                severity_value = AlertSeverity.WARNING
            elif severity == AlertSeveritySchema.ERROR:
                severity_value = AlertSeverity.ERROR
            
            if severity_value:
                query = query.filter(Alert.severity == severity_value)
        
        # Filtrar por week_label si se proporciona
        if week_label:
            query = query.filter(Alert.week_label == week_label)
        
        # Filtrar por acknowledged si se proporciona
        if acknowledged is not None:
            if acknowledged:
                # acknowledged == true: acknowledged_at IS NOT NULL
                query = query.filter(Alert.acknowledged_at.isnot(None))
            else:
                # acknowledged == false: acknowledged_at IS NULL
                query = query.filter(Alert.acknowledged_at.is_(None))
        
        # Contar total (sin paginación)
        total = query.count()
        
        # Ordenar por created_at DESC y aplicar paginación
        alerts = query.order_by(Alert.created_at.desc()).offset(offset).limit(limit).all()
        
        # Convertir a schemas
        items = [OpsAlertRow.model_validate(alert) for alert in alerts]
        
        return OpsAlertsResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
    
    except Exception as e:
        # Log del error para debugging
        logger.error(f"Error en list_alerts: {str(e)}", exc_info=True)
        
        # Retornar error 500
        raise HTTPException(
            status_code=500,
            detail="database_error"
        )


@router.post("/alerts/{alert_id}/acknowledge", response_model=OpsAlertRow)
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    Reconoce una alerta operacional.
    
    Marca una alerta como reconocida estableciendo `acknowledged_at` a la fecha/hora actual.
    Si la alerta ya está reconocida, la operación es idempotente (retorna el estado actual).
    
    Ejemplo curl:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/ops/alerts/123/acknowledge"
    ```
    
    Args:
        alert_id: ID de la alerta a reconocer
    
    Returns:
        OpsAlertRow con el estado actualizado de la alerta
    
    Raises:
        404: Si la alerta no existe
        500: Si ocurre un error de base de datos
    """
    try:
        # Buscar alerta por PK
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        
        if not alert:
            raise HTTPException(
                status_code=404,
                detail=f"Alerta con id {alert_id} no encontrada"
            )
        
        # Si ya está reconocida, retornar igual (idempotente)
        if alert.acknowledged_at is not None:
            return OpsAlertRow.model_validate(alert)
        
        # Set acknowledged_at = now() y commit
        alert.acknowledged_at = datetime.utcnow()
        db.commit()
        db.refresh(alert)
        
        return OpsAlertRow.model_validate(alert)
    
    except HTTPException:
        # Re-raise HTTP exceptions (404)
        raise
    except Exception as e:
        # Log del error para debugging
        logger.error(f"Error en acknowledge_alert (alert_id={alert_id}): {str(e)}", exc_info=True)
        
        # Rollback en caso de error
        try:
            db.rollback()
        except:
            pass
        
        # Retornar error 500
        raise HTTPException(
            status_code=500,
            detail="database_error"
        )


@router.get("/data-health", response_model=IdentitySystemHealthRow)
def get_data_health(db: Session = Depends(get_db)):
    """
    Obtiene métricas de salud del sistema de identidad canónica.
    
    Retorna métricas agregadas en una sola fila:
    - Estado de última corrida de identidad
    - Delay desde última corrida exitosa
    - Unmatched pendientes
    - Alertas activas
    - Totales del registro canónico
    
    Ejemplo curl:
    ```bash
    curl http://localhost:8000/api/v1/ops/data-health
    ```
    
    Returns:
        IdentitySystemHealthRow con todas las métricas del sistema
    
    Raises:
        500: Si ocurre un error de base de datos o la vista no retorna filas
    """
    try:
        # Consultar la vista directamente
        query = text("SELECT * FROM ops.v_identity_system_health")
        result = db.execute(query)
        row = result.fetchone()
        
        if row is None:
            # La vista siempre debería retornar 1 fila, pero por seguridad
            logger.error("Vista ops.v_identity_system_health retornó 0 filas")
            raise HTTPException(
                status_code=500,
                detail="database_error"
            )
        
        # Convertir Row a dict para el schema
        row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
        
        # Convertir a schema
        return IdentitySystemHealthRow.model_validate(row_dict)
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log del error para debugging
        logger.error(f"Error en get_data_health: {str(e)}", exc_info=True)
        
        # Retornar error 500
        raise HTTPException(
            status_code=500,
            detail="database_error"
        )


@router.get("/raw-health/status", response_model=RawDataHealthStatusResponse)
def get_raw_health_status(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Número de resultados por página"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    source: Optional[str] = Query(None, description="Filtrar por nombre de fuente (case-insensitive)")
):
    """
    Obtiene el estado de salud de datos RAW por fuente.
    
    Retorna un listado paginado de fuentes con su estado de salud calculado,
    basado en la vista ops.v_data_health_status.
    
    Ejemplo curl (sin filtros):
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/raw-health/status?limit=50&offset=0"
    ```
    
    Ejemplo curl (con filtro por fuente):
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/raw-health/status?limit=50&offset=0&source=module_ct_cabinet_leads"
    ```
    
    Args:
        limit: Número máximo de resultados (1-200, default: 50)
        offset: Número de resultados a saltar (default: 0)
        source: Filtrar por nombre de fuente (búsqueda case-insensitive)
    
    Returns:
        RawDataHealthStatusResponse con items, total, limit y offset
    
    Raises:
        500: Si ocurre un error de base de datos
    """
    try:
        # Construir query base con conversión de interval a text
        query_str = """
            SELECT 
                source_name,
                source_type,
                max_business_date,
                business_days_lag,
                max_ingestion_ts,
                ingestion_lag_interval::text as ingestion_lag_interval,
                rows_business_yesterday,
                rows_business_today,
                rows_ingested_yesterday,
                rows_ingested_today,
                health_status
            FROM ops.v_data_health_status
        """
        params = {}
        
        # Agregar filtro por source si se proporciona
        if source:
            query_str += " WHERE source_name ILIKE :source"
            params['source'] = f"%{source}%"
        
        # Contar total (sin paginación)
        count_query_str = "SELECT COUNT(*) FROM ops.v_data_health_status"
        if source:
            count_query_str += " WHERE source_name ILIKE :source"
        count_result = db.execute(text(count_query_str), params)
        total = count_result.scalar() or 0
        
        # Agregar ordenamiento y paginación
        query_str += " ORDER BY source_name ASC LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = offset
        
        # Ejecutar query
        result = db.execute(text(query_str), params)
        rows = result.fetchall()
        
        # Convertir a schemas
        items = []
        for row in rows:
            row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
            items.append(RawDataHealthStatusRow.model_validate(row_dict))
        
        return RawDataHealthStatusResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("raw_health_status failed")
        raise HTTPException(
            status_code=500,
            detail="database_error"
        )


@router.get("/raw-health/freshness", response_model=RawDataFreshnessStatusResponse)
def get_raw_freshness_status(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Número de resultados por página"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    source: Optional[str] = Query(None, description="Filtrar por nombre de fuente (case-insensitive)")
):
    """
    Obtiene el estado de frescura de datos RAW por fuente.
    
    Retorna un listado paginado de fuentes con métricas de frescura,
    basado en la vista ops.v_data_freshness_status.
    
    Ejemplo curl (sin filtros):
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/raw-health/freshness?limit=50&offset=0"
    ```
    
    Ejemplo curl (con filtro por fuente):
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/raw-health/freshness?limit=50&offset=0&source=summary_daily"
    ```
    
    Args:
        limit: Número máximo de resultados (1-200, default: 50)
        offset: Número de resultados a saltar (default: 0)
        source: Filtrar por nombre de fuente (búsqueda case-insensitive)
    
    Returns:
        RawDataFreshnessStatusResponse con items, total, limit y offset
    
    Raises:
        500: Si ocurre un error de base de datos
    """
    try:
        # Construir query base con conversión de interval a text
        query_str = """
            SELECT 
                source_name,
                max_business_date,
                business_days_lag,
                max_ingestion_ts,
                ingestion_lag_interval::text as ingestion_lag_interval,
                rows_business_yesterday,
                rows_business_today,
                rows_ingested_yesterday,
                rows_ingested_today
            FROM ops.v_data_freshness_status
        """
        params = {}
        
        # Agregar filtro por source si se proporciona
        if source:
            query_str += " WHERE source_name ILIKE :source"
            params['source'] = f"%{source}%"
        
        # Contar total (sin paginación)
        count_query_str = "SELECT COUNT(*) FROM ops.v_data_freshness_status"
        if source:
            count_query_str += " WHERE source_name ILIKE :source"
        count_result = db.execute(text(count_query_str), params)
        total = count_result.scalar() or 0
        
        # Agregar ordenamiento y paginación
        query_str += " ORDER BY source_name ASC LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = offset
        
        # Ejecutar query
        result = db.execute(text(query_str), params)
        rows = result.fetchall()
        
        # Convertir a schemas
        items = []
        for row in rows:
            row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
            items.append(RawDataFreshnessStatusRow.model_validate(row_dict))
        
        return RawDataFreshnessStatusResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("raw_freshness_status failed")
        raise HTTPException(
            status_code=500,
            detail="database_error"
        )


@router.get("/raw-health/ingestion-daily", response_model=RawDataIngestionDailyResponse)
def get_raw_ingestion_daily(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Número de resultados por página"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    source: Optional[str] = Query(None, description="Filtrar por nombre de fuente (case-insensitive)"),
    date_from: Optional[date] = Query(None, description="Fecha inicio del rango (inclusive)"),
    date_to: Optional[date] = Query(None, description="Fecha fin del rango (inclusive)")
):
    """
    Obtiene métricas diarias de ingesta de datos RAW por fuente.
    
    Retorna un listado paginado de métricas diarias (business/ingestion) por fuente,
    basado en la vista ops.v_data_ingestion_daily.
    
    Ejemplo curl (sin filtros):
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/raw-health/ingestion-daily?limit=50&offset=0"
    ```
    
    Ejemplo curl (con filtros):
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/raw-health/ingestion-daily?limit=50&offset=0&source=module_ct_cabinet_leads&date_from=2024-01-01&date_to=2024-01-31"
    ```
    
    Args:
        limit: Número máximo de resultados (1-200, default: 50)
        offset: Número de resultados a saltar (default: 0)
        source: Filtrar por nombre de fuente (búsqueda case-insensitive)
        date_from: Fecha inicio del rango (inclusive)
        date_to: Fecha fin del rango (inclusive)
    
    Returns:
        RawDataIngestionDailyResponse con items, total, limit y offset
    
    Raises:
        500: Si ocurre un error de base de datos
    """
    try:
        # Construir query base
        query_str = "SELECT * FROM ops.v_data_ingestion_daily"
        params = {}
        conditions = []
        
        # Agregar filtro por source si se proporciona
        if source:
            conditions.append("source_name ILIKE :source")
            params['source'] = f"%{source}%"
        
        # Agregar filtro por rango de fechas si se proporciona
        if date_from:
            conditions.append("metric_date >= :date_from")
            params['date_from'] = date_from
        
        if date_to:
            conditions.append("metric_date <= :date_to")
            params['date_to'] = date_to
        
        # Agregar condiciones WHERE si hay filtros
        if conditions:
            query_str += " WHERE " + " AND ".join(conditions)
        
        # Contar total (sin paginación)
        count_query_str = "SELECT COUNT(*) FROM ops.v_data_ingestion_daily"
        if conditions:
            count_query_str += " WHERE " + " AND ".join(conditions)
        count_result = db.execute(text(count_query_str), params)
        total = count_result.scalar() or 0
        
        # Agregar ordenamiento y paginación
        query_str += " ORDER BY metric_date DESC, source_name ASC LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = offset
        
        # Ejecutar query
        result = db.execute(text(query_str), params)
        rows = result.fetchall()
        
        # Convertir a schemas
        items = []
        for row in rows:
            row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
            items.append(RawDataIngestionDailyRow.model_validate(row_dict))
        
        return RawDataIngestionDailyResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("raw_ingestion_daily failed")
        raise HTTPException(
            status_code=500,
            detail="database_error"
        )


@router.get("/mv-health", response_model=MvHealthResponse)
def get_mv_health(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Número de resultados por página"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    schema_name: Optional[str] = Query(None, description="Filtrar por schema (ej: 'ops' o 'canon')"),
    stale_only: Optional[bool] = Query(None, description="Si true, solo MVs con refresh > 1440 minutos o sin refresh")
):
    """
    Obtiene el estado de salud de las Materialized Views.
    
    Retorna un listado paginado de MVs con información de tamaño, último refresh,
    y estado del último refresh (SUCCESS/FAILED).
    
    Funciona incluso si no hay logs de refresh (last_refresh_* = null).
    
    Ejemplo curl (sin filtros):
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/mv-health?limit=5&offset=0"
    ```
    
    Ejemplo curl (con filtro por schema):
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/mv-health?schema_name=ops&stale_only=true"
    ```
    
    Args:
        limit: Número máximo de resultados (1-200, default: 50)
        offset: Número de resultados a saltar (default: 0)
        schema_name: Filtrar por schema (ej: 'ops', 'canon')
        stale_only: Si true, solo MVs con refresh > 1440 minutos o sin refresh
    
    Returns:
        MvHealthResponse con items, total, limit y offset
    
    Raises:
        500: Si ocurre un error de base de datos
    """
    try:
        # Query base
        query_str = """
            SELECT
                m.schemaname AS schema_name,
                m.matviewname AS mv_name,
                m.ispopulated AS is_populated,
                (pg_relation_size(format('%I.%I', m.schemaname, m.matviewname)::regclass) / 1024.0 / 1024.0) AS size_mb,
                l.refreshed_at AS last_refresh_at,
                l.status AS last_refresh_status,
                l.error_message AS last_refresh_error,
                CASE
                    WHEN l.refreshed_at IS NULL THEN NULL
                    ELSE floor(extract(epoch from (now() - l.refreshed_at))/60)::int
                END AS minutes_since_refresh
            FROM pg_matviews m
            LEFT JOIN LATERAL (
                SELECT refreshed_at, status, error_message
                FROM ops.mv_refresh_log
                WHERE schema_name = m.schemaname AND mv_name = m.matviewname
                ORDER BY refreshed_at DESC
                LIMIT 1
            ) l ON true
            WHERE m.schemaname IN ('ops','canon')
        """
        params = {}
        
        # Agregar filtro por schema_name si se proporciona
        if schema_name:
            query_str += " AND m.schemaname = :schema_name"
            params['schema_name'] = schema_name
        
        # Agregar filtro por stale_only si es true
        if stale_only:
            query_str += """
                AND (l.refreshed_at IS NULL 
                     OR floor(extract(epoch from (now() - l.refreshed_at))/60) > 1440)
            """
        
        # Query para contar total (sin paginación)
        count_query_str = """
            SELECT COUNT(*)
            FROM pg_matviews m
            LEFT JOIN LATERAL (
                SELECT refreshed_at, status, error_message
                FROM ops.mv_refresh_log
                WHERE schema_name = m.schemaname AND mv_name = m.matviewname
                ORDER BY refreshed_at DESC
                LIMIT 1
            ) l ON true
            WHERE m.schemaname IN ('ops','canon')
        """
        count_params = {}
        
        if schema_name:
            count_query_str += " AND m.schemaname = :schema_name"
            count_params['schema_name'] = schema_name
        
        if stale_only:
            count_query_str += """
                AND (l.refreshed_at IS NULL 
                     OR floor(extract(epoch from (now() - l.refreshed_at))/60) > 1440)
            """
        
        # Contar total
        count_result = db.execute(text(count_query_str), count_params)
        total = count_result.scalar() or 0
        
        # Agregar ordenamiento y paginación
        query_str += " ORDER BY m.schemaname, m.matviewname LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = offset
        
        # Ejecutar query
        result = db.execute(text(query_str), params)
        rows = result.fetchall()
        
        # Convertir a schemas
        calculated_at = datetime.now(timezone.utc)
        items = []
        for row in rows:
            row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
            # Agregar calculated_at
            row_dict['calculated_at'] = calculated_at
            items.append(MvHealthRow.model_validate(row_dict))
        
        return MvHealthResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("mv_health failed")
        raise HTTPException(
            status_code=500,
            detail="database_error"
        )


@router.get("/health-checks", response_model=HealthChecksResponse)
def get_health_checks(
    db: Session = Depends(get_db)
):
    """
    Obtiene los checks de salud del sistema.
    
    Retorna un listado de checks que evalúan condiciones de salud
    de RAW data, Materialized Views e identidad.
    
    Cada check tiene:
    - check_key: Identificador único del check
    - severity: error, warning, info
    - status: OK, WARN, ERROR
    - message: Mensaje descriptivo
    - drilldown_url: URL para ver detalles del check (ej: /ops/health?tab=raw)
    - last_evaluated_at: Timestamp de evaluación
    
    Ejemplo curl:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/health-checks"
    ```
    
    Returns:
        HealthChecksResponse con items (lista de checks)
    
    Raises:
        500: Si ocurre un error de base de datos
    """
    try:
        # Query para obtener todos los checks
        query_str = """
            SELECT 
                check_key,
                severity,
                status,
                message,
                drilldown_url,
                last_evaluated_at
            FROM ops.v_health_checks
            ORDER BY 
                CASE severity 
                    WHEN 'error' THEN 1 
                    WHEN 'warning' THEN 2 
                    WHEN 'info' THEN 3 
                END,
                check_key
        """
        
        # Ejecutar query
        result = db.execute(text(query_str))
        rows = result.fetchall()
        
        # Convertir a schemas
        items = []
        for row in rows:
            row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
            items.append(HealthCheckRow.model_validate(row_dict))
        
        return HealthChecksResponse(items=items)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("health_checks failed")
        raise HTTPException(
            status_code=500,
            detail="database_error"
        )


@router.get("/health-global", response_model=HealthGlobalResponse)
def get_health_global(
    db: Session = Depends(get_db)
):
    """
    Obtiene el estado global de salud del sistema.
    
    Retorna un resumen agregado de todos los checks:
    - global_status: OK, WARN, o ERROR
    - error_count: Número de checks con severity=error y status=ERROR
    - warn_count: Número de checks con severity=warning y status=WARN
    - ok_count: Número de checks con status=OK
    - calculated_at: Timestamp de cálculo
    
    Lógica:
    - global_status = ERROR si existe cualquier check con severity='error' y status='ERROR'
    - else WARN si existe cualquier check con status in ('WARN','ERROR')
    - else OK
    
    Ejemplo curl:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/health-global"
    ```
    
    Returns:
        HealthGlobalResponse con estado global y contadores
    
    Raises:
        500: Si ocurre un error de base de datos
    """
    try:
        # Query para obtener el estado global
        query_str = """
            SELECT 
                global_status,
                error_count,
                warn_count,
                ok_count,
                calculated_at
            FROM ops.v_health_global
        """
        
        # Ejecutar query
        result = db.execute(text(query_str))
        row = result.fetchone()
        
        if not row:
            # Si no hay datos, retornar estado OK por defecto
            return HealthGlobalResponse(
                global_status='OK',
                error_count=0,
                warn_count=0,
                ok_count=0,
                calculated_at=datetime.now(timezone.utc)
            )
        
        # Convertir a schema
        row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
        return HealthGlobalResponse.model_validate(row_dict)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("health_global failed")
        raise HTTPException(
            status_code=500,
            detail="database_error"
        )


@router.get("/source-registry", response_model=SourceRegistryResponse)
def get_source_registry(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=1, le=200, description="Número de resultados por página"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    schema_name: Optional[str] = Query(None, description="Filtrar por schema"),
    object_type: Optional[str] = Query(None, description="Filtrar por tipo (table/view/matview)"),
    layer: Optional[str] = Query(None, description="Filtrar por layer (RAW/DERIVED/MV/CANON)"),
    role: Optional[str] = Query(None, description="Filtrar por role (PRIMARY/SECONDARY)"),
    criticality: Optional[str] = Query(None, description="Filtrar por criticality (critical/important/normal)"),
    should_monitor: Optional[bool] = Query(None, description="Filtrar por should_monitor"),
    health_enabled: Optional[bool] = Query(None, description="Filtrar por health_enabled")
):
    """
    Obtiene el Source Registry con paginación y filtros.
    
    Retorna un listado paginado de objetos (tablas/vistas/matviews) registrados
    en el registry canónico con sus metadatos.
    
    Ejemplo curl (sin filtros):
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/source-registry?limit=10&offset=0"
    ```
    
    Ejemplo curl (con filtros):
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/source-registry?limit=50&offset=0&layer=RAW&criticality=critical"
    ```
    
    Args:
        limit: Número máximo de resultados (1-200, default: 50)
        offset: Número de resultados a saltar (default: 0)
        schema_name: Filtrar por schema (ej: 'ops', 'canon')
        object_type: Filtrar por tipo (table/view/matview)
        layer: Filtrar por layer (RAW/DERIVED/MV/CANON)
        role: Filtrar por role (PRIMARY/SECONDARY)
        criticality: Filtrar por criticality (critical/important/normal)
        should_monitor: Filtrar por should_monitor (true/false)
        health_enabled: Filtrar por health_enabled (true/false)
    
    Returns:
        SourceRegistryResponse con items, total, limit y offset
    
    Raises:
        500: Si ocurre un error de base de datos
    """
    try:
        # Construir query base
        query_str = "SELECT * FROM ops.source_registry"
        params = {}
        conditions = []
        
        # Agregar filtros
        if schema_name:
            conditions.append("schema_name = :schema_name")
            params['schema_name'] = schema_name
        
        if object_type:
            conditions.append("object_type = :object_type")
            params['object_type'] = object_type
        
        if layer:
            conditions.append("layer = :layer")
            params['layer'] = layer
        
        if role:
            conditions.append("role = :role")
            params['role'] = role
        
        if criticality:
            conditions.append("criticality = :criticality")
            params['criticality'] = criticality
        
        if should_monitor is not None:
            conditions.append("should_monitor = :should_monitor")
            params['should_monitor'] = should_monitor
        
        if health_enabled is not None:
            conditions.append("health_enabled = :health_enabled")
            params['health_enabled'] = health_enabled
        
        # Agregar condiciones WHERE si hay filtros
        if conditions:
            query_str += " WHERE " + " AND ".join(conditions)
        
        # Contar total (sin paginación)
        count_query_str = "SELECT COUNT(*) FROM ops.source_registry"
        if conditions:
            count_query_str += " WHERE " + " AND ".join(conditions)
        count_result = db.execute(text(count_query_str), params)
        total = count_result.scalar() or 0
        
        # Agregar ordenamiento y paginación
        query_str += " ORDER BY schema_name, object_name LIMIT :limit OFFSET :offset"
        params['limit'] = limit
        params['offset'] = offset
        
        # Ejecutar query
        result = db.execute(text(query_str), params)
        rows = result.fetchall()
        
        # Convertir a schemas
        items = []
        for row in rows:
            row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(row)
            # Convertir depends_on JSONB a lista de dicts
            if row_dict.get('depends_on'):
                if isinstance(row_dict['depends_on'], str):
                    import json
                    row_dict['depends_on'] = json.loads(row_dict['depends_on'])
            items.append(SourceRegistryRow.model_validate(row_dict))
        
        return SourceRegistryResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("source_registry failed")
        raise HTTPException(
            status_code=500,
            detail="database_error"
        )


@router.post("/yango-payments/ingest")
def ingest_yango_payments(db: Session = Depends(get_db)):
    """
    Ejecuta la ingesta de pagos Yango desde module_ct_cabinet_payments al ledger.
    
    Esta función ejecuta ops.ingest_yango_payments_snapshot() que:
    - Lee desde ops.v_yango_payments_raw_current_aliases (que a su vez lee desde public.module_ct_cabinet_payments)
    - Inserta nuevos registros en ops.yango_payment_ledger de forma idempotente
    - Actualiza registros existentes cuando aparece información de identidad (driver_id/person_key)
    
    Ejemplo curl:
    ```bash
    curl -X POST "http://localhost:8000/api/v1/ops/yango-payments/ingest"
    ```
    
    Returns:
        Dict con status y rows_inserted (número de filas nuevas insertadas)
    
    Raises:
        500: Si ocurre un error de base de datos
    """
    try:
        result = db.execute(text("SELECT ops.ingest_yango_payments_snapshot()"))
        rows_inserted = result.scalar() or 0
        db.commit()
        
        logger.info(f"Yango payments ingest completed: {rows_inserted} rows inserted")
        
        return {
            "status": "success",
            "rows_inserted": rows_inserted,
            "message": f"Se insertaron {rows_inserted} nuevos registros en el ledger"
        }
    except Exception as e:
        db.rollback()
        logger.exception("ingest_yango_payments failed")
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando ingesta de pagos Yango: {str(e)}"
        )


@router.get("/identity-gaps", response_model=IdentityGapResponse)
def get_identity_gaps(
    db: Session = Depends(get_db),
    date_from: Optional[date] = Query(None, description="Fecha mínima de lead_date"),
    date_to: Optional[date] = Query(None, description="Fecha máxima de lead_date"),
    risk_level: Optional[str] = Query(None, description="Filtrar por risk_level: high, medium, low"),
    gap_reason: Optional[str] = Query(None, description="Filtrar por gap_reason: no_identity, no_origin, activity_without_identity, no_activity, resolved"),
    page: int = Query(1, ge=1, description="Número de página (1-indexed)"),
    page_size: int = Query(100, ge=1, le=1000, description="Tamaño de página (máx 1000)")
):
    """
    Obtiene análisis de brechas de identidad para leads Cabinet.
    
    Retorna:
    - totals: Totales agregados (total_leads, unresolved, resolved, pct_unresolved)
    - breakdown: Desglose por gap_reason y risk_level
    - items: Lista paginada de leads con sus brechas
    
    Ejemplo curl:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/identity-gaps?page=1&page_size=100&risk_level=high"
    ```
    """
    try:
        offset = (page - 1) * page_size
        
        # Construir query base
        query_str = "SELECT * FROM ops.v_identity_gap_analysis"
        params = {}
        conditions = []
        
        if date_from:
            conditions.append("lead_date >= :date_from")
            params["date_from"] = date_from
        
        if date_to:
            conditions.append("lead_date <= :date_to")
            params["date_to"] = date_to
        
        if risk_level:
            conditions.append("risk_level = :risk_level")
            params["risk_level"] = risk_level
        
        if gap_reason:
            conditions.append("gap_reason = :gap_reason")
            params["gap_reason"] = gap_reason
        
        if conditions:
            query_str += " WHERE " + " AND ".join(conditions)
        
        # Contar total
        count_query = f"SELECT COUNT(*) FROM ops.v_identity_gap_analysis"
        if conditions:
            count_query += " WHERE " + " AND ".join(conditions)
        count_result = db.execute(text(count_query), params)
        total = count_result.scalar() or 0
        
        # Obtener breakdown
        breakdown_query = f"""
            SELECT gap_reason, risk_level, COUNT(*) as count
            FROM ops.v_identity_gap_analysis
        """
        if conditions:
            breakdown_query += " WHERE " + " AND ".join(conditions)
        breakdown_query += " GROUP BY gap_reason, risk_level"
        breakdown_result = db.execute(text(breakdown_query), params)
        breakdown_rows = breakdown_result.fetchall()
        breakdown = [
            IdentityGapBreakdown(
                gap_reason=row.gap_reason,
                risk_level=row.risk_level,
                count=row.count
            )
            for row in breakdown_rows
        ]
        
        # Obtener totals
        totals_query = f"""
            SELECT 
                COUNT(*) as total_leads,
                COUNT(*) FILTER (WHERE gap_reason != 'resolved') as unresolved,
                COUNT(*) FILTER (WHERE gap_reason = 'resolved') as resolved
            FROM ops.v_identity_gap_analysis
        """
        if conditions:
            totals_query += " WHERE " + " AND ".join(conditions)
        totals_result = db.execute(text(totals_query), params)
        totals_row = totals_result.fetchone()
        
        totals = IdentityGapTotals(
            total_leads=totals_row.total_leads or 0,
            unresolved=totals_row.unresolved or 0,
            resolved=totals_row.resolved or 0,
            pct_unresolved=round(100.0 * (totals_row.unresolved or 0) / max(totals_row.total_leads or 1, 1), 2)
        )
        
        # Obtener items paginados
        query_str += " ORDER BY gap_age_days DESC, lead_date DESC LIMIT :limit OFFSET :offset"
        params["limit"] = page_size
        params["offset"] = offset
        result = db.execute(text(query_str), params)
        rows = result.fetchall()
        
        items = [
            IdentityGapRow.model_validate(dict(row._mapping) if hasattr(row, '_mapping') else dict(row))
            for row in rows
        ]
        
        return IdentityGapResponse(
            totals=totals,
            breakdown=breakdown,
            items=items,
            meta={
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size
            }
        )
    
    except Exception as e:
        logger.exception("get_identity_gaps failed")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo brechas de identidad: {str(e)}"
        )


@router.get("/identity-gaps/alerts", response_model=IdentityGapAlertsResponse)
def get_identity_gap_alerts(
    db: Session = Depends(get_db)
):
    """
    Obtiene alertas activas de brechas de identidad.
    
    Retorna lista de alertas para leads con problemas críticos:
    - over_24h_no_identity: Lead sin identidad por >24h
    - over_7d_unresolved: Lead sin resolver por >7 días
    - activity_no_identity: Lead con actividad pero sin person_key
    
    Ejemplo curl:
    ```bash
    curl -X GET "http://localhost:8000/api/v1/ops/identity-gaps/alerts"
    ```
    """
    try:
        query = text("SELECT * FROM ops.v_identity_gap_alerts ORDER BY severity DESC, days_open DESC")
        result = db.execute(query)
        rows = result.fetchall()
        
        items = [
            IdentityGapAlertRow.model_validate(dict(row._mapping) if hasattr(row, '_mapping') else dict(row))
            for row in rows
        ]
        
        return IdentityGapAlertsResponse(
            items=items,
            total=len(items),
            meta={}
        )
    
    except Exception as e:
        logger.exception("get_identity_gap_alerts failed")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo alertas de brechas: {str(e)}"
        )
