#!/usr/bin/env python3
"""
Script para aplicar fix de expected_amount directamente.
Ejecutar este script si la migración Alembic tiene problemas de merge.

Uso:
    python scripts/apply_claims_gap_fix.py
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import text
from app.db import SessionLocal
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def apply_fix():
    """Aplica el fix de expected_amount directamente."""
    logger.info("=" * 80)
    logger.info("APLICANDO FIX DE expected_amount EN v_cabinet_claims_gap_14d")
    logger.info("=" * 80)
    
    db = SessionLocal()
    
    try:
        # Leer el archivo SQL de la vista
        sql_file = project_root / "backend" / "sql" / "ops" / "v_cabinet_claims_gap_14d.sql"
        
        if not sql_file.exists():
            logger.error(f"❌ Archivo SQL no encontrado: {sql_file}")
            return False
        
        sql_content = sql_file.read_text(encoding='utf-8')
        
        logger.info("Ejecutando CREATE OR REPLACE VIEW...")
        db.execute(text(sql_content))
        db.commit()
        
        logger.info("✅ Vista actualizada correctamente")
        
        # Verificar que la columna existe
        logger.info("Verificando que expected_amount existe...")
        check_query = text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'ops' 
              AND table_name = 'v_cabinet_claims_gap_14d' 
              AND column_name = 'expected_amount'
        """)
        result = db.execute(check_query)
        exists = result.rowcount > 0
        
        if exists:
            logger.info("✅ Columna expected_amount existe")
            return True
        else:
            logger.error("❌ Columna expected_amount NO existe después del fix")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error aplicando fix: {e}", exc_info=True)
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    success = apply_fix()
    sys.exit(0 if success else 1)
