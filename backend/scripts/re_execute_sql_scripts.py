#!/usr/bin/env python3
"""
Re-ejecución Automática de Scripts SQL Corregidos
==================================================
Ejecuta todos los scripts SQL corregidos para completar FASE 2-5
"""

import sys
import logging
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


def execute_sql_file(db_session, sql_file: Path):
    """Ejecuta un archivo SQL"""
    try:
        if not sql_file.exists():
            logger.warning(f"Archivo no existe: {sql_file}")
            return False, f"Archivo no existe: {sql_file.name}"
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Ejecutar SQL
        db_session.execute(text(sql_content))
        db_session.commit()
        
        logger.info(f"[OK] Ejecutado: {sql_file.name}")
        return True, f"Ejecutado: {sql_file.name}"
    
    except Exception as e:
        db_session.rollback()
        logger.error(f"[ERROR] Error en {sql_file.name}: {str(e)}")
        return False, f"Error en {sql_file.name}: {str(e)}"


def main():
    """Re-ejecuta todos los scripts SQL corregidos"""
    
    logger.info("="*80)
    logger.info("RE-EJECUCION AUTOMATICA: Scripts SQL Corregidos")
    logger.info("="*80)
    
    scripts_dir = Path(__file__).parent
    sql_dir = scripts_dir / "sql"
    db = SessionLocal()
    
    execution_log = []
    
    try:
        # Scripts a ejecutar en orden
        scripts = [
            "backfill_lead_ledger_attributed_scout.sql",
            "10_create_v_scout_attribution_raw.sql",  # Usar existente
            "11_create_v_scout_attribution.sql",  # Usar existente
            "create_v_scout_attribution_conflicts.sql",
            "create_v_persons_without_scout_categorized.sql",
            "create_v_cabinet_leads_missing_scout_alerts.sql",
            "create_v_scout_payment_base.sql"
        ]
        
        for script_file in scripts:
            script_path = sql_dir / script_file
            if not script_path.exists():
                logger.warning(f"\n{'='*80}")
                logger.warning(f"Script no existe: {script_file}")
                logger.warning(f"{'='*80}")
                execution_log.append((script_file, False, f"Archivo no existe"))
                continue
                
            logger.info(f"\n{'='*80}")
            logger.info(f"Ejecutando: {script_file}")
            logger.info(f"{'='*80}")
            
            success, msg = execute_sql_file(db, script_path)
            execution_log.append((script_file, success, msg))
            
            if not success:
                logger.warning(f"  {msg}")
                logger.warning("Continuando con siguiente script...")
        
        # Resumen final
        logger.info("\n" + "="*80)
        logger.info("RESUMEN FINAL")
        logger.info("="*80)
        
        success_count = sum(1 for _, success, _ in execution_log if success)
        total_count = len(execution_log)
        
        for script_file, success, msg in execution_log:
            status = "[OK]" if success else "[ERROR]"
            logger.info(f"{status} {script_file}: {msg}")
        
        logger.info(f"\nTotal: {success_count}/{total_count} scripts ejecutados exitosamente")
        
        # Verificación final
        if success_count == total_count:
            logger.info("\n[OK] Todos los scripts ejecutados exitosamente")
        else:
            logger.warning(f"\n[ADVERTENCIA] {total_count - success_count} scripts tuvieron errores")
        
    except Exception as e:
        logger.error(f"Error en re-ejecucion: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
