#!/usr/bin/env python3
"""
Script para ejecutar ingesta de identidad de forma programada.
Diseñado para ejecutarse periódicamente (cron, task scheduler, etc.)

Uso:
    python backend/scripts/run_identity_ingestion_scheduled.py

Configurar en:
    - Windows Task Scheduler: cada 6 horas
    - Linux/Mac Cron: 0 */6 * * *
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal
from app.services.ingestion import IngestionService
from app.services.lead_attribution import LeadAttributionService
from datetime import date, timedelta
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# #region agent log
def debug_log(location, message, data=None, hypothesis_id=None):
    try:
        log_entry = {
            "id": f"log_{int(datetime.now().timestamp() * 1000)}",
            "timestamp": int(datetime.now().timestamp() * 1000),
            "location": location,
            "message": message,
            "data": data or {},
            "sessionId": "debug-session",
            "runId": "scheduled-ingestion",
            "hypothesisId": hypothesis_id
        }
        with open("c:\\cursor\\CT4\\.cursor\\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception:
        pass
# #endregion


def run_ingestion():
    """Ejecuta ingesta de identidad y pobla lead_events en modo incremental."""
    # #region agent log
    debug_log("run_identity_ingestion_scheduled.py:run_ingestion", "ENTRY", {"timestamp": datetime.now().isoformat()}, "H3")
    # #endregion
    
    db = SessionLocal()
    try:
        # Paso 1: Ejecutar ingesta de identidad (crea identity_links)
        logger.info("=" * 60)
        logger.info("Paso 1: Ejecutando ingesta de identidad...")
        logger.info("=" * 60)
        
        # #region agent log
        debug_log("run_identity_ingestion_scheduled.py:run_ingestion", "BEFORE_INGESTION", {}, "H3")
        # #endregion
        
        ingestion_service = IngestionService(db)
        
        # Solo procesar scouting_daily si cabinet_leads no existe
        # Verificar si cabinet_leads existe
        try:
            from sqlalchemy import text
            check_table = db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'module_ct_cabinet_leads'
                )
            """))
            cabinet_leads_exists = check_table.scalar()
            
            # #region agent log
            debug_log("run_identity_ingestion_scheduled.py:run_ingestion", "CHECK_CABINET_LEADS", {"exists": cabinet_leads_exists}, "H3")
            # #endregion
            
            if cabinet_leads_exists:
                run = ingestion_service.run_ingestion(incremental=True)
            else:
                logger.info("module_ct_cabinet_leads no existe, procesando solo scouting_daily")
                run = ingestion_service.run_ingestion(incremental=True, source_tables=["module_ct_scouting_daily"])
        except Exception as e:
            logger.warning(f"Error verificando tabla cabinet_leads, intentando solo scouting_daily: {e}")
            run = ingestion_service.run_ingestion(incremental=True, source_tables=["module_ct_scouting_daily"])
        
        # #region agent log
        debug_log("run_identity_ingestion_scheduled.py:run_ingestion", "AFTER_INGESTION", {"run_id": run.id, "status": str(run.status), "scope_date_to": str(run.scope_date_to) if run.scope_date_to else None}, "H3")
        # #endregion
        
        logger.info(f"Ingesta completada: run_id={run.id}, status={run.status}")
        
        # Continuar incluso si la ingesta falló parcialmente (puede haber procesado scouting_daily)
        if run.status.value != 'COMPLETED':
            logger.warning(f"Ingesta falló o completó parcialmente: {run.error_message}")
            # #region agent log
            debug_log("run_identity_ingestion_scheduled.py:run_ingestion", "INGESTION_PARTIAL_FAIL", {"error": run.error_message, "stats": str(run.stats)}, "H3")
            # #endregion
            # No retornar error aquí, continuar con populate_events
        
        logger.info(f"Stats ingesta: {run.stats}")
        
        # Paso 2: Poblar lead_events (requiere identity_links creados)
        logger.info("")
        logger.info("=" * 60)
        logger.info("Paso 2: Poblando lead_events...")
        logger.info("=" * 60)
        
        attribution_service = LeadAttributionService(db)
        
        # Obtener fechas desde la última corrida o usar últimos 30 días
        date_to = date.today()
        if run.scope_date_to:
            date_from = run.scope_date_to
        else:
            date_from = date_to - timedelta(days=30)
        
        # #region agent log
        debug_log("run_identity_ingestion_scheduled.py:run_ingestion", "BEFORE_POPULATE_EVENTS", {"date_from": str(date_from), "date_to": str(date_to)}, "H2")
        # #endregion
        
        logger.info(f"Poblando eventos desde {date_from} hasta {date_to}")
        
        # Poblar eventos desde scouting_daily (cabinet)
        stats_scouting = attribution_service.populate_events_from_scouting(
            date_from=date_from,
            date_to=date_to,
            run_id=None
        )
        
        # #region agent log
        debug_log("run_identity_ingestion_scheduled.py:run_ingestion", "AFTER_POPULATE_SCOUTING", {"stats": stats_scouting}, "H2")
        # #endregion
        
        logger.info(f"Scouting eventos: {stats_scouting}")
        
        # Poblar eventos desde cabinet_leads (si la tabla existe)
        try:
            stats_cabinet = attribution_service.populate_events_from_cabinet(
                date_from=date_from,
                date_to=date_to
            )
            # #region agent log
            debug_log("run_identity_ingestion_scheduled.py:run_ingestion", "AFTER_POPULATE_CABINET", {"stats": stats_cabinet}, "H2")
            # #endregion
            logger.info(f"Cabinet eventos: {stats_cabinet}")
        except Exception as e:
            logger.warning(f"No se pudo poblar eventos de cabinet: {e}")
            # #region agent log
            debug_log("run_identity_ingestion_scheduled.py:run_ingestion", "POPULATE_CABINET_ERROR", {"error": str(e)}, "H2")
            # #endregion
        
        # #region agent log
        debug_log("run_identity_ingestion_scheduled.py:run_ingestion", "BEFORE_CHECK_MV_REFRESH", {}, "H1")
        # #endregion
        
        # Paso 3: Refrescar vista materializada (si existe)
        # Hacer commit primero para asegurar que todas las transacciones anteriores estén completas
        try:
            db.commit()
        except Exception:
            db.rollback()
        
        try:
            from sqlalchemy import text
            check_mv = db.execute(text("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_matviews 
                    WHERE schemaname = 'ops' 
                    AND matviewname = 'mv_cabinet_financial_14d'
                )
            """))
            mv_exists = check_mv.scalar()
            
            # #region agent log
            debug_log("run_identity_ingestion_scheduled.py:run_ingestion", "MV_EXISTS_CHECK", {"mv_exists": mv_exists}, "H1")
            # #endregion
            
            if mv_exists:
                logger.info("Refrescando vista materializada mv_cabinet_financial_14d...")
                db.execute(text("REFRESH MATERIALIZED VIEW ops.mv_cabinet_financial_14d;"))
                db.commit()
                # #region agent log
                debug_log("run_identity_ingestion_scheduled.py:run_ingestion", "MV_REFRESHED", {}, "H1")
                # #endregion
                logger.info("Vista materializada refrescada exitosamente")
            else:
                # #region agent log
                debug_log("run_identity_ingestion_scheduled.py:run_ingestion", "MV_NOT_EXISTS", {}, "H1")
                # #endregion
                logger.info("Vista materializada no existe, omitiendo refresh")
        except Exception as e:
            logger.warning(f"Error refrescando vista materializada: {e}")
            # #region agent log
            debug_log("run_identity_ingestion_scheduled.py:run_ingestion", "MV_REFRESH_ERROR", {"error": str(e)}, "H1")
            # #endregion
            try:
                db.rollback()
            except Exception:
                pass
        
        logger.info("")
        logger.info("=" * 60)
        logger.info("Proceso completo exitosamente")
        logger.info("=" * 60)
        
        # #region agent log
        debug_log("run_identity_ingestion_scheduled.py:run_ingestion", "EXIT_SUCCESS", {}, "H3")
        # #endregion
        
        return 0
            
    except Exception as e:
        logger.error(f"Error ejecutando proceso completo: {e}", exc_info=True)
        # #region agent log
        debug_log("run_identity_ingestion_scheduled.py:run_ingestion", "EXIT_ERROR", {"error": str(e)}, "H3")
        # #endregion
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    exit_code = run_ingestion()
    sys.exit(exit_code)

