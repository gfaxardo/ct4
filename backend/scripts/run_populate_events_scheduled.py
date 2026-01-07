#!/usr/bin/env python3
"""
Script para poblar lead_events de forma programada.
Este script solo ejecuta populate_events (no ingesta de identidad).
"""

import sys
import os
from pathlib import Path
from datetime import date, timedelta

# Agregar el directorio backend al path
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


def populate_events():
    """Pobla lead_events desde las tablas fuente."""
    db = SessionLocal()
    try:
        service = LeadAttributionService(db)
        
        # Usar últimos 30 días por defecto
        date_to = date.today()
        date_from = date_to - timedelta(days=30)
        
        logger.info(f"Poblando eventos desde {date_from} hasta {date_to}")
        
        # Poblar desde scouting_daily
        stats_scouting = service.populate_events_from_scouting(
            date_from=date_from,
            date_to=date_to,
            run_id=None
        )
        logger.info(f"Scouting: {stats_scouting}")
        
        # Poblar desde cabinet_leads
        try:
            stats_cabinet = service.populate_events_from_cabinet(
                date_from=date_from,
                date_to=date_to
            )
            logger.info(f"Cabinet: {stats_cabinet}")
        except Exception as e:
            logger.warning(f"Cabinet no disponible: {e}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    exit_code = populate_events()
    sys.exit(exit_code)


