from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List
from app.db import get_db
from app.models.ops import IngestionRun, Alert
from app.schemas.ingestion import IngestionRun as IngestionRunSchema
from app.schemas.data_health import (
    DataHealthResponse,
    DataFreshnessStatus,
    DataHealthStatus,
    DataIngestionDaily
)
from app.services.alerts import AlertService

router = APIRouter()


@router.get("/ingestion-runs", response_model=List[IngestionRunSchema])
def list_ingestion_runs(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    runs = db.query(IngestionRun).order_by(IngestionRun.started_at.desc()).offset(skip).limit(limit).all()
    # #region agent log
    if runs and skip == 0:
        import json
        from app.models.canon import IdentityLink
        from sqlalchemy import func
        try:
            first_run = runs[0]
            links_count = db.query(func.count(IdentityLink.id)).filter(IdentityLink.run_id == first_run.id).scalar()
            with open('c:\\cursor\\CT4\\.cursor\\debug.log', 'a', encoding='utf-8') as f:
                f.write(json.dumps({
                    "sessionId": "debug-session",
                    "runId": "initial",
                    "hypothesisId": "B",
                    "location": "ops.py:list_ingestion_runs:first_run",
                    "message": "Última corrida (primera en lista)",
                    "data": {
                        "run_id": first_run.id,
                        "status": first_run.status.value if hasattr(first_run.status, 'value') else str(first_run.status),
                        "started_at": first_run.started_at.isoformat() if first_run.started_at else None,
                        "links_count": links_count
                    },
                    "timestamp": int(__import__('time').time() * 1000)
                }) + '\n')
        except: pass
    # #endregion
    return runs


@router.get("/alerts")
def list_alerts(
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000)
):
    service = AlertService(db)
    alerts = service.get_active_alerts(limit)
    return [
        {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "severity": alert.severity.value if hasattr(alert.severity, 'value') else str(alert.severity),
            "week_label": alert.week_label,
            "message": alert.message,
            "details": alert.details,
            "created_at": alert.created_at.isoformat() if alert.created_at else None,
            "run_id": alert.run_id
        }
        for alert in alerts
    ]


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    service = AlertService(db)
    alert = service.acknowledge_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alerta no encontrada")
    return {"message": "Alerta reconocida exitosamente", "alert_id": alert.id}


@router.get("/data-health", response_model=DataHealthResponse)
def get_data_health(
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=90, description="Días de historia para ingestion_daily")
):
    """
    Obtiene el estado de salud de las ingestas de datos.
    
    Retorna:
    - freshness_status: Estado de frescura por fuente
    - health_status: Estado de salud por fuente (con semáforo)
    - ingestion_daily: Métricas diarias de ingesta (últimos N días)
    """
    try:
        # Consultar freshness_status
        freshness_result = db.execute(text("""
            SELECT 
                source_name,
                max_business_date,
                business_days_lag,
                max_ingestion_ts,
                ingestion_lag_interval::text AS ingestion_lag_interval,
                rows_business_yesterday,
                rows_business_today,
                rows_ingested_yesterday,
                rows_ingested_today
            FROM ops.v_data_freshness_status
            ORDER BY source_name
        """))
        
        freshness_status = [
            DataFreshnessStatus(
                source_name=row.source_name,
                max_business_date=row.max_business_date,
                business_days_lag=row.business_days_lag,
                max_ingestion_ts=row.max_ingestion_ts,
                ingestion_lag_interval=row.ingestion_lag_interval,
                rows_business_yesterday=row.rows_business_yesterday or 0,
                rows_business_today=row.rows_business_today or 0,
                rows_ingested_yesterday=row.rows_ingested_yesterday or 0,
                rows_ingested_today=row.rows_ingested_today or 0
            )
            for row in freshness_result
        ]
        
        # Consultar health_status (incluye source_type)
        health_result = db.execute(text("""
            SELECT 
                source_name,
                source_type,
                max_business_date,
                business_days_lag,
                max_ingestion_ts,
                ingestion_lag_interval::text AS ingestion_lag_interval,
                rows_business_yesterday,
                rows_business_today,
                rows_ingested_yesterday,
                rows_ingested_today,
                health_status
            FROM ops.v_data_health_status
            ORDER BY source_type, source_name
        """))
        
        health_status = [
            DataHealthStatus(
                source_name=row.source_name,
                max_business_date=row.max_business_date,
                business_days_lag=row.business_days_lag,
                max_ingestion_ts=row.max_ingestion_ts,
                ingestion_lag_interval=row.ingestion_lag_interval,
                rows_business_yesterday=row.rows_business_yesterday or 0,
                rows_business_today=row.rows_business_today or 0,
                rows_ingested_yesterday=row.rows_ingested_yesterday or 0,
                rows_ingested_today=row.rows_ingested_today or 0,
                source_type=row.source_type,
                health_status=row.health_status
            )
            for row in health_result
        ]
        
        # Consultar ingestion_daily (últimos N días)
        # Usar make_interval para construir el intervalo correctamente
        ingestion_result = db.execute(text("""
            SELECT 
                source_name,
                metric_type,
                metric_date,
                rows_count
            FROM ops.v_data_ingestion_daily
            WHERE metric_date >= CURRENT_DATE - make_interval(days => :days)
            ORDER BY source_name, metric_type, metric_date DESC
        """), {"days": days})
        
        ingestion_daily = [
            DataIngestionDaily(
                source_name=row.source_name,
                metric_type=row.metric_type,
                metric_date=row.metric_date,
                rows_count=row.rows_count or 0
            )
            for row in ingestion_result
        ]
        
        return DataHealthResponse(
            freshness_status=freshness_status,
            health_status=health_status,
            ingestion_daily=ingestion_daily
        )
        
    except Exception as e:
        # Rollback si hay error, pero no abortar transacción
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error consultando data health: {str(e)}"
        )

