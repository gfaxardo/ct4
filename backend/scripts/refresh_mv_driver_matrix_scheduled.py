#!/usr/bin/env python3
"""
Script para refrescar la vista materializada ops.mv_payments_driver_matrix_cabinet
Diseñado para ejecutarse periódicamente (cron, scheduler, etc.)
"""
import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('refresh_mv_driver_matrix.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def get_database_url():
    """Obtener DATABASE_URL desde variable de entorno o config"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        # Intentar leer desde config
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from app.config import DATABASE_URL
            database_url = DATABASE_URL
        except ImportError:
            logger.error("DATABASE_URL no encontrada. Configurar variable de entorno o en app.config")
            sys.exit(1)
    return database_url

def refresh_materialized_view():
    """Refrescar la vista materializada"""
    database_url = get_database_url()
    script_path = Path(__file__).parent.parent / "scripts" / "sql" / "refresh_mv_driver_matrix.sql"
    
    if not script_path.exists():
        logger.error(f"Script no encontrado: {script_path}")
        sys.exit(1)
    
    psql_path = os.getenv("PSQL_PATH", "psql")
    
    try:
        logger.info(f"Iniciando refresh de vista materializada a las {datetime.now()}")
        logger.info(f"Usando script: {script_path}")
        
        result = subprocess.run(
            [psql_path, database_url, "-f", str(script_path)],
            capture_output=True,
            text=True,
            check=True,
            timeout=600  # 10 minutos timeout
        )
        
        logger.info("Refresh completado exitosamente")
        if result.stdout:
            logger.info(f"Output: {result.stdout}")
        
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("Refresh timeout después de 10 minutos")
        sys.exit(1)
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Error en refresh: {e}")
        logger.error(f"Stderr: {e.stderr}")
        sys.exit(1)
        
    except FileNotFoundError:
        logger.error(f"psql no encontrado en: {psql_path}")
        logger.error("Configurar PSQL_PATH o agregar psql al PATH")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"Error inesperado: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    refresh_materialized_view()

