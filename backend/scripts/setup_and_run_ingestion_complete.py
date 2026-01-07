#!/usr/bin/env python3
"""
Script completo para configurar y ejecutar ingesta de identidad.
1. Verifica estado actual
2. Ejecuta ingesta si es necesario
3. Verifica resultados
"""

import sys
import os
from pathlib import Path
from datetime import date, timedelta

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal
from app.services.ingestion import IngestionService
from app.models.ops import IngestionRun, RunStatus, JobType
from sqlalchemy import text
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_last_run(db):
    """Verifica la última corrida completada."""
    result = db.execute(text("""
        SELECT 
            id,
            scope_date_from,
            scope_date_to,
            completed_at,
            EXTRACT(EPOCH FROM (NOW() - completed_at))/3600 as hours_since
        FROM ops.ingestion_runs
        WHERE status = 'COMPLETED'
        ORDER BY completed_at DESC
        LIMIT 1
    """))
    row = result.fetchone()
    return row


def check_lead_events_max_date(db):
    """Verifica la fecha máxima en lead_events."""
    result = db.execute(text("""
        SELECT MAX(event_date) as max_date
        FROM observational.lead_events
    """))
    row = result.fetchone()
    return row[0] if row and row[0] else None


def run_ingestion_if_needed(db):
    """Ejecuta ingesta si es necesario."""
    last_run = check_last_run(db)
    max_date = check_lead_events_max_date(db)
    
    logger.info(f"Última corrida: {last_run.scope_date_to if last_run else 'Ninguna'}")
    logger.info(f"Fecha máxima en lead_events: {max_date}")
    
    # Si no hay última corrida o la fecha máxima es antigua, ejecutar ingesta
    if not last_run or (max_date and max_date < date.today() - timedelta(days=1)):
        logger.info("Ejecutando ingesta...")
        
        service = IngestionService(db)
        
        # Si hay última corrida, usar modo incremental desde esa fecha
        if last_run and last_run.scope_date_to:
            date_from = last_run.scope_date_to
            date_to = date.today()
            logger.info(f"Modo incremental: desde {date_from} hasta {date_to}")
            run = service.run_ingestion(
                scope_date_from=date_from,
                scope_date_to=date_to,
                incremental=True
            )
        else:
            # Primera corrida: usar últimos 30 días
            date_to = date.today()
            date_from = date_to - timedelta(days=30)
            logger.info(f"Primera corrida: desde {date_from} hasta {date_to}")
            run = service.run_ingestion(
                scope_date_from=date_from,
                scope_date_to=date_to,
                incremental=False
            )
        
        logger.info(f"Ingesta ejecutada: run_id={run.id}, status={run.status}")
        
        if run.status == RunStatus.COMPLETED:
            logger.info(f"Stats: {run.stats}")
            return True
        else:
            logger.error(f"Ingesta falló: {run.error_message}")
            return False
    else:
        logger.info("No se necesita ejecutar ingesta (datos recientes)")
        return True


def verify_results(db):
    """Verifica que los resultados sean correctos."""
    logger.info("Verificando resultados...")
    
    # Verificar lead_events
    max_date = check_lead_events_max_date(db)
    logger.info(f"Fecha máxima en lead_events: {max_date}")
    
    # Verificar v_conversion_metrics
    result = db.execute(text("""
        SELECT MAX(lead_date) as max_date
        FROM observational.v_conversion_metrics
        WHERE origin_tag = 'cabinet'
            AND driver_id IS NOT NULL
    """))
    row = result.fetchone()
    max_cm_date = row[0] if row and row[0] else None
    logger.info(f"Fecha máxima en v_conversion_metrics (cabinet): {max_cm_date}")
    
    return max_date, max_cm_date


def main():
    """Función principal."""
    db = SessionLocal()
    try:
        logger.info("=" * 60)
        logger.info("Configuración y Ejecución de Ingesta de Identidad")
        logger.info("=" * 60)
        
        # 1. Verificar estado actual
        logger.info("\n1. Verificando estado actual...")
        last_run = check_last_run(db)
        max_date = check_lead_events_max_date(db)
        
        # 2. Ejecutar ingesta si es necesario
        logger.info("\n2. Ejecutando ingesta si es necesario...")
        success = run_ingestion_if_needed(db)
        
        if not success:
            logger.error("La ingesta falló. Revisar logs.")
            return 1
        
        # 3. Verificar resultados
        logger.info("\n3. Verificando resultados...")
        max_date_after, max_cm_date = verify_results(db)
        
        logger.info("\n" + "=" * 60)
        logger.info("RESUMEN:")
        logger.info(f"  - lead_events fecha máxima: {max_date_after}")
        logger.info(f"  - v_conversion_metrics fecha máxima: {max_cm_date}")
        logger.info("=" * 60)
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)


