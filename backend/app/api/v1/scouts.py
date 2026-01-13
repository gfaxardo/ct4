"""
Endpoints para Scout Attribution Observability
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from datetime import date, datetime
from uuid import UUID
import logging

from app.db import get_db
from app.models.ops import IngestionRun, RunStatus

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/attribution/metrics")
def get_attribution_metrics(db: Session = Depends(get_db)):
    """
    Obtiene métricas instantáneas de scout attribution
    """
    try:
        query = text("""
            SELECT 
                total_persons,
                persons_with_scout_satisfactory,
                pct_scout_satisfactory,
                persons_missing_scout,
                conflicts_count,
                backlog_a_events_without_scout,
                backlog_d_scout_in_events_not_in_ledger,
                backlog_c_legacy_no_events_no_ledger,
                last_job_status,
                last_job_ended_at,
                last_job_started_at,
                last_job_duration_seconds,
                last_job_summary,
                last_job_error,
                snapshot_timestamp
            FROM ops.v_scout_attribution_metrics_snapshot
        """)
        
        result = db.execute(query)
        row = result.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="Métricas no disponibles")
        
        return {
            "total_persons": row.total_persons,
            "persons_with_scout_satisfactory": row.persons_with_scout_satisfactory,
            "pct_scout_satisfactory": float(row.pct_scout_satisfactory) if row.pct_scout_satisfactory else 0,
            "persons_missing_scout": row.persons_missing_scout,
            "conflicts_count": row.conflicts_count,
            "backlog": {
                "a_events_without_scout": row.backlog_a_events_without_scout,
                "d_scout_in_events_not_in_ledger": row.backlog_d_scout_in_events_not_in_ledger,
                "c_legacy": row.backlog_c_legacy_no_events_no_ledger,
            },
            "last_job": {
                "status": row.last_job_status,
                "ended_at": row.last_job_ended_at.isoformat() if row.last_job_ended_at else None,
                "started_at": row.last_job_started_at.isoformat() if row.last_job_started_at else None,
                "duration_seconds": row.last_job_duration_seconds,
                "summary": row.last_job_summary,
                "error": row.last_job_error,
            },
            "snapshot_timestamp": row.snapshot_timestamp.isoformat() if row.snapshot_timestamp else None
        }
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo métricas: {str(e)}")


@router.get("/attribution/metrics/daily")
def get_attribution_metrics_daily(
    days: int = Query(30, ge=1, le=365, description="Días de histórico"),
    db: Session = Depends(get_db)
):
    """
    Obtiene métricas diarias históricas para gráficos
    """
    try:
        query = text("""
            SELECT 
                metric_date,
                total_persons,
                satisfactory_count,
                pct_satisfactory,
                missing_count,
                by_source_scouting_daily,
                by_source_cabinet_leads,
                by_source_lead_ledger,
                computed_at
            FROM ops.v_scout_attribution_metrics_daily
            WHERE metric_date >= CURRENT_DATE - INTERVAL ':days days'
            ORDER BY metric_date DESC
        """).bindparams(days=days)
        
        result = db.execute(query)
        rows = result.fetchall()
        
        return {
            "daily_metrics": [
                {
                    "date": str(row.metric_date),
                    "total_persons": row.total_persons,
                    "satisfactory_count": row.satisfactory_count,
                    "pct_satisfactory": float(row.pct_satisfactory) if row.pct_satisfactory else 0,
                    "missing_count": row.missing_count,
                    "by_source": {
                        "scouting_daily": row.by_source_scouting_daily,
                        "cabinet_leads": row.by_source_cabinet_leads,
                        "lead_ledger": row.by_source_lead_ledger,
                    }
                }
                for row in rows
            ]
        }
    except Exception as e:
        logger.error(f"Error obteniendo métricas diarias: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo métricas diarias: {str(e)}")


@router.get("/attribution/conflicts")
def get_conflicts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Lista person_keys con conflictos (múltiples scouts)
    """
    try:
        offset = (page - 1) * page_size
        
        query = text("""
            SELECT 
                person_key,
                distinct_scout_count,
                scout_ids,
                sources,
                origin_tags,
                first_event_date,
                last_event_date,
                total_sources
            FROM ops.v_scout_attribution_conflicts
            ORDER BY distinct_scout_count DESC, total_sources DESC
            LIMIT :page_size OFFSET :offset
        """)
        
        count_query = text("SELECT COUNT(*) FROM ops.v_scout_attribution_conflicts")
        
        result = db.execute(query, {"page_size": page_size, "offset": offset})
        count_result = db.execute(count_query)
        total = count_result.scalar()
        
        return {
            "conflicts": [
                {
                    "person_key": str(row.person_key),
                    "distinct_scout_count": row.distinct_scout_count,
                    "scout_ids": row.scout_ids,
                    "sources": row.sources,
                    "origin_tags": row.origin_tags,
                    "first_event_date": str(row.first_event_date) if row.first_event_date else None,
                    "last_event_date": str(row.last_event_date) if row.last_event_date else None,
                    "total_sources": row.total_sources,
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
        logger.error(f"Error obteniendo conflictos: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo conflictos: {str(e)}")


@router.get("/attribution/backlog")
def get_backlog(
    category: Optional[str] = Query(None, description="Filtrar por categoría (A, C, D)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Lista backlog por categorías (A: eventos sin scout, C: legacy, D: scout en eventos no propagado)
    """
    try:
        offset = (page - 1) * page_size
        
        where_clause = ""
        params = {"page_size": page_size, "offset": offset}
        
        if category:
            where_clause = "WHERE category = :category"
            params["category"] = category
        
        query_text = f"""
            SELECT 
                person_key,
                category,
                category_label,
                scout_id,
                source_tables,
                origin_tags,
                first_event_date,
                last_event_date,
                event_count
            FROM ops.v_persons_without_scout_categorized
            {where_clause}
            ORDER BY event_count DESC, first_event_date DESC
            LIMIT :page_size OFFSET :offset
        """
        query = text(query_text)
        
        count_query = text(f"""
            SELECT COUNT(*) 
            FROM ops.v_persons_without_scout_categorized
            {where_clause}
        """)
        
        result = db.execute(query, params)
        count_result = db.execute(count_query, {"category": category} if category else {})
        total = count_result.scalar()
        
        return {
            "backlog": [
                {
                    "person_key": str(row.person_key),
                    "category": row.category,
                    "category_label": row.category_label,
                    "scout_id": row.scout_id,
                    "source_tables": row.source_tables,
                    "origin_tags": row.origin_tags,
                    "first_event_date": str(row.first_event_date) if row.first_event_date else None,
                    "last_event_date": str(row.last_event_date) if row.last_event_date else None,
                    "event_count": row.event_count,
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
        logger.error(f"Error obteniendo backlog: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo backlog: {str(e)}")


@router.get("/attribution/job-status")
def get_job_status(db: Session = Depends(get_db)):
    """
    Obtiene estado del último job de refresh
    """
    try:
        # Buscar último run de scout_attribution_refresh (usar cast a TEXT para comparar)
        query = text("""
            SELECT 
                id,
                started_at,
                completed_at,
                status,
                stats,
                error_message
            FROM ops.ingestion_runs
            WHERE job_type::TEXT = 'scout_attribution_refresh'
            ORDER BY started_at DESC
            LIMIT 1
        """)
        
        result = db.execute(query)
        row = result.fetchone()
        
        if not row:
            return {
                "last_run": None,
                "status": "never_run"
            }
        
        job_run = row
        
        duration_seconds = None
        if job_run.completed_at and job_run.started_at:
            duration_seconds = int((job_run.completed_at - job_run.started_at).total_seconds())
        
        # Convertir status a string si es enum
        status_str = str(job_run.status) if hasattr(job_run.status, 'value') else job_run.status
        
        return {
            "last_run": {
                "run_id": job_run.id,
                "status": status_str,
                "started_at": job_run.started_at.isoformat() if job_run.started_at else None,
                "ended_at": job_run.completed_at.isoformat() if job_run.completed_at else None,
                "duration_seconds": duration_seconds,
                "summary": job_run.stats,
                "error": job_run.error_message,
            },
            "status": status_str
        }
    except Exception as e:
        logger.error(f"Error obteniendo estado del job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo estado del job: {str(e)}")


@router.post("/attribution/run-now")
def run_now(db: Session = Depends(get_db)):
    """
    Ejecuta refresh de scout attribution ahora (manual trigger)
    """
    try:
        # Verificar si hay un job corriendo
        running_job = db.query(IngestionRun).filter(
            IngestionRun.job_type == 'scout_attribution_refresh',
            IngestionRun.status == RunStatus.RUNNING
        ).first()
        
        if running_job:
            raise HTTPException(
                status_code=409,
                detail=f"Ya hay un job corriendo (run_id={running_job.id})"
            )
        
        # Ejecutar job (en background si es posible, o síncrono)
        # Por ahora, ejecutar síncrono
        from backend.scripts.run_scout_attribution_refresh import main
        
        result = main()
        
        return {
            "status": "completed",
            "run_id": result.get("run_id"),
            "message": "Refresh ejecutado exitosamente"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ejecutando refresh: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error ejecutando refresh: {str(e)}")


@router.get("/liquidation/base")
def get_liquidation_base(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    filters: Optional[str] = Query(None, description="Filtros JSON"),
    db: Session = Depends(get_db)
):
    """
    Vista base para liquidación de scouts (NO ejecuta pagos)
    """
    try:
        offset = (page - 1) * page_size
        
        query = text("""
            SELECT 
                person_key,
                driver_id,
                scout_id,
                origin_tag,
                milestone_reached,
                milestone_date,
                eligible_7d,
                amount_payable,
                payment_status,
                block_reason
            FROM ops.v_scout_payment_base
            ORDER BY payment_status, scout_id
            LIMIT :page_size OFFSET :offset
        """)
        
        count_query = text("SELECT COUNT(*) FROM ops.v_scout_payment_base")
        
        result = db.execute(query, {"page_size": page_size, "offset": offset})
        count_result = db.execute(count_query)
        total = count_result.scalar() or 0
        
        return {
            "items": [
                {
                    "person_key": str(row.person_key) if row.person_key else None,
                    "driver_id": row.driver_id,
                    "scout_id": row.scout_id,
                    "origin_tag": row.origin_tag,
                    "milestone_reached": row.milestone_reached,
                    "milestone_date": str(row.milestone_date) if row.milestone_date else None,
                    "eligible_7d": row.eligible_7d,
                    "amount_payable": float(row.amount_payable) if row.amount_payable else 0,
                    "payment_status": row.payment_status,
                    "block_reason": row.block_reason,
                }
                for row in result.fetchall()
            ],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "total_pages": (total + page_size - 1) // page_size if page_size > 0 else 0
            }
        }
    except Exception as e:
        logger.error(f"Error obteniendo liquidación base: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error obteniendo liquidación base: {str(e)}")

