#!/usr/bin/env python3
"""
Script para procesar registros pendientes de scouting_daily que no están en lead_events.
"""

import sys
from pathlib import Path

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal
from app.services.lead_attribution import LeadAttributionService
from datetime import date, timedelta
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Procesa registros pendientes de scouting_daily."""
    db = SessionLocal()
    try:
        logger.info("=" * 70)
        logger.info("PROCESANDO REGISTROS PENDIENTES DE SCOUTING_DAILY")
        logger.info("=" * 70)
        
        attribution_service = LeadAttributionService(db)
        
        # Procesar últimos 30 días para capturar todos los registros pendientes
        date_to = date.today()
        date_from = date_to - timedelta(days=30)
        
        logger.info(f"Procesando eventos desde {date_from} hasta {date_to}")
        
        # Poblar eventos desde scouting_daily (cabinet)
        stats_scouting = attribution_service.populate_events_from_scouting(
            date_from=date_from,
            date_to=date_to,
            run_id=None
        )
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("RESULTADOS:")
        logger.info(f"  - Eventos procesados: {stats_scouting.get('processed', 0)}")
        logger.info(f"  - Eventos insertados: {stats_scouting.get('inserted', 0)}")
        logger.info(f"  - Eventos actualizados: {stats_scouting.get('updated', 0)}")
        logger.info(f"  - Eventos omitidos: {stats_scouting.get('skipped', 0)}")
        logger.info("=" * 70)
        
        return 0
            
    except Exception as e:
        logger.error(f"Error procesando eventos: {e}", exc_info=True)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)



