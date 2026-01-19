"""
Servicio de procesamiento automático de leads.

Este servicio ejecuta un polling periódico para detectar y procesar
nuevos leads automáticamente sin intervención manual.
"""
import logging
import os
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import text

from app.db import SessionLocal

logger = logging.getLogger(__name__)

# Configuración
AUTO_PROCESS_ENABLED = os.getenv("AUTO_PROCESS_LEADS", "true").lower() == "true"
AUTO_PROCESS_INTERVAL_MINUTES = int(os.getenv("AUTO_PROCESS_INTERVAL_MINUTES", "5"))
AUTO_PROCESS_MIN_PENDING = int(os.getenv("AUTO_PROCESS_MIN_PENDING", "1"))

# Scheduler global
_scheduler: Optional[BackgroundScheduler] = None
_is_processing = False
_last_run_result = None


def get_pending_leads_count() -> dict:
    """Obtiene el conteo de leads pendientes de procesar."""
    db = SessionLocal()
    try:
        query = text("""
            WITH lead_source_pks AS (
                SELECT DISTINCT COALESCE(external_id::text, id::text) as source_pk
                FROM public.module_ct_cabinet_leads
            )
            SELECT 
                (SELECT COUNT(*) FROM lead_source_pks) as total_in_table,
                (SELECT COUNT(*) FROM lead_source_pks l 
                 WHERE EXISTS (SELECT 1 FROM canon.identity_links il 
                              WHERE il.source_table = 'module_ct_cabinet_leads' 
                              AND il.source_pk = l.source_pk)) as in_links,
                (SELECT COUNT(*) FROM lead_source_pks l 
                 WHERE EXISTS (SELECT 1 FROM canon.identity_unmatched iu 
                              WHERE iu.source_table = 'module_ct_cabinet_leads' 
                              AND iu.source_pk = l.source_pk)) as in_unmatched
        """)
        result = db.execute(query)
        row = result.fetchone()
        
        total = row[0] or 0
        in_links = row[1] or 0
        in_unmatched = row[2] or 0
        pending = total - in_links - in_unmatched
        
        return {
            "total_in_table": total,
            "in_links": in_links,
            "in_unmatched": in_unmatched,
            "pending_count": max(0, pending)
        }
    except Exception as e:
        logger.error(f"Error obteniendo pending leads: {e}")
        return {"pending_count": 0, "error": str(e)}
    finally:
        db.close()


def process_pending_leads() -> dict:
    """Procesa los leads pendientes."""
    global _is_processing, _last_run_result
    
    if _is_processing:
        logger.info("[AUTO-PROCESSOR] Ya hay un procesamiento en curso, saltando...")
        return {"status": "skipped", "reason": "already_processing"}
    
    _is_processing = True
    start_time = datetime.now()
    
    try:
        # Verificar si hay leads pendientes
        pending_info = get_pending_leads_count()
        pending_count = pending_info.get("pending_count", 0)
        
        if pending_count < AUTO_PROCESS_MIN_PENDING:
            logger.info(f"[AUTO-PROCESSOR] No hay leads pendientes ({pending_count} < {AUTO_PROCESS_MIN_PENDING})")
            _last_run_result = {
                "status": "no_pending",
                "pending_count": pending_count,
                "timestamp": start_time.isoformat()
            }
            return _last_run_result
        
        logger.info(f"[AUTO-PROCESSOR] Detectados {pending_count} leads pendientes. Iniciando procesamiento...")
        
        # Importar aquí para evitar imports circulares
        from app.services.cabinet_leads_processor import CabinetLeadsProcessor
        
        db = SessionLocal()
        try:
            processor = CabinetLeadsProcessor(db)
            result = processor.process_all(
                refresh_index=True,
                run_attribution=True,
                refresh_mvs=True
            )
            
            duration = (datetime.now() - start_time).total_seconds()
            
            _last_run_result = {
                "status": "completed",
                "pending_before": pending_count,
                "result": result,
                "duration_seconds": duration,
                "timestamp": start_time.isoformat()
            }
            
            logger.info(f"[AUTO-PROCESSOR] Procesamiento completado en {duration:.1f}s: {result}")
            return _last_run_result
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"[AUTO-PROCESSOR] Error en procesamiento: {e}", exc_info=True)
        _last_run_result = {
            "status": "error",
            "error": str(e),
            "timestamp": start_time.isoformat()
        }
        return _last_run_result
    finally:
        _is_processing = False


def auto_process_job():
    """Job que se ejecuta periódicamente para procesar leads."""
    logger.debug("[AUTO-PROCESSOR] Ejecutando job de auto-procesamiento...")
    try:
        result = process_pending_leads()
        if result.get("status") == "completed":
            logger.info(f"[AUTO-PROCESSOR] Job completado: {result.get('result', {}).get('ingestion', {}).get('stats', {})}")
    except Exception as e:
        logger.error(f"[AUTO-PROCESSOR] Error en job: {e}", exc_info=True)


def start_scheduler():
    """Inicia el scheduler para procesamiento automático."""
    global _scheduler
    
    if not AUTO_PROCESS_ENABLED:
        logger.info("[AUTO-PROCESSOR] Procesamiento automático DESHABILITADO (AUTO_PROCESS_LEADS=false)")
        return
    
    if _scheduler is not None:
        logger.warning("[AUTO-PROCESSOR] Scheduler ya está corriendo")
        return
    
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        auto_process_job,
        trigger=IntervalTrigger(minutes=AUTO_PROCESS_INTERVAL_MINUTES),
        id="auto_process_leads",
        name="Auto Process New Leads",
        replace_existing=True,
        max_instances=1
    )
    _scheduler.start()
    
    logger.info(f"[AUTO-PROCESSOR] Scheduler iniciado. Intervalo: {AUTO_PROCESS_INTERVAL_MINUTES} minutos")


def stop_scheduler():
    """Detiene el scheduler."""
    global _scheduler
    
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("[AUTO-PROCESSOR] Scheduler detenido")


def get_scheduler_status() -> dict:
    """Obtiene el estado del scheduler."""
    global _scheduler, _is_processing, _last_run_result
    
    if _scheduler is None:
        return {
            "enabled": AUTO_PROCESS_ENABLED,
            "running": False,
            "interval_minutes": AUTO_PROCESS_INTERVAL_MINUTES,
            "is_processing": _is_processing,
            "last_run": _last_run_result
        }
    
    jobs = _scheduler.get_jobs()
    next_run = None
    if jobs:
        next_run = jobs[0].next_run_time.isoformat() if jobs[0].next_run_time else None
    
    return {
        "enabled": AUTO_PROCESS_ENABLED,
        "running": _scheduler.running,
        "interval_minutes": AUTO_PROCESS_INTERVAL_MINUTES,
        "next_run": next_run,
        "is_processing": _is_processing,
        "last_run": _last_run_result
    }


def trigger_manual_run() -> dict:
    """Dispara una ejecución manual del procesamiento."""
    logger.info("[AUTO-PROCESSOR] Ejecución manual disparada")
    return process_pending_leads()
