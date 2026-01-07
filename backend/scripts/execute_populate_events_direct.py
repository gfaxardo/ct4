#!/usr/bin/env python3
"""
Script para ejecutar populate_events directamente (sin API).
Requiere entorno virtual activado.
"""

import sys
from pathlib import Path
from datetime import date, timedelta

# Agregar backend al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal
from app.services.lead_attribution import LeadAttributionService
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Ejecuta populate_events directamente."""
    db = SessionLocal()
    try:
        service = LeadAttributionService(db)
        
        # Usar últimos 30 días
        date_to = date.today()
        date_from = date_to - timedelta(days=30)
        
        logger.info(f"Poblando eventos desde {date_from} hasta {date_to}")
        
        # Poblar desde scouting_daily
        logger.info("Procesando module_ct_scouting_daily...")
        stats_scouting = service.populate_events_from_scouting(
            date_from=date_from,
            date_to=date_to,
            run_id=None
        )
        logger.info(f"Scouting completado: {stats_scouting}")
        
        # Poblar desde cabinet_leads (si existe)
        try:
            logger.info("Procesando module_ct_cabinet_leads...")
            stats_cabinet = service.populate_events_from_cabinet(
                date_from=date_from,
                date_to=date_to
            )
            logger.info(f"Cabinet completado: {stats_cabinet}")
        except Exception as e:
            logger.warning(f"Cabinet no disponible o error: {e}")
        
        logger.info("Proceso completado exitosamente")
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

