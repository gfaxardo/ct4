#!/usr/bin/env python3
"""
Ejecutar todos los scripts SQL de Scout Attribution en orden
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
            logger.warning(f"⚠️ Archivo no existe: {sql_file}")
            return False, f"Archivo no existe"
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Ejecutar SQL
        db_session.execute(text(sql_content))
        db_session.commit()
        
        logger.info(f"✅ Ejecutado: {sql_file.name}")
        return True, f"Ejecutado exitosamente"
    
    except Exception as e:
        db_session.rollback()
        logger.error(f"❌ Error en {sql_file.name}: {str(e)[:200]}")
        return False, f"Error: {str(e)[:200]}"

def main():
    """Ejecuta todos los scripts SQL en orden"""
    logger.info("="*80)
    logger.info("EJECUTANDO SCRIPTS SQL: Scout Attribution")
    logger.info("="*80)
    
    scripts_dir = Path(__file__).parent / "sql"
    db = SessionLocal()
    
    # Scripts en orden de ejecución
    scripts = [
        # Auditoría primero
        "20_create_audit_tables.sql",
        # Vistas base
        "10_create_v_scout_attribution_raw.sql",
        "11_create_v_scout_attribution.sql",
        # Vistas de conflictos y categorización
        "create_v_scout_attribution_conflicts.sql",
        "create_v_persons_without_scout_categorized.sql",
        # Vistas de métricas (dependen de las anteriores)
        "01_metrics_scout_attribution.sql",
        # Vistas de integración
        "04_yango_collection_with_scout.sql",
        "create_v_scout_payment_base.sql",
        # Verificaciones (al final)
        "07_verify_scout_attribution.sql",
    ]
    
    results = []
    
    for script_file in scripts:
        script_path = scripts_dir / script_file
        logger.info(f"\n{'='*80}")
        logger.info(f"Ejecutando: {script_file}")
        logger.info(f"{'='*80}")
        
        success, msg = execute_sql_file(db, script_path)
        results.append((script_file, success, msg))
        
        if not success:
            logger.warning(f"  {msg}")
            # Continuar con siguiente script
    
    # Resumen
    logger.info("\n" + "="*80)
    logger.info("RESUMEN")
    logger.info("="*80)
    
    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)
    
    for script_file, success, msg in results:
        status = "✅" if success else "❌"
        logger.info(f"{status} {script_file}: {msg}")
    
    logger.info(f"\nTotal: {success_count}/{total_count} scripts ejecutados exitosamente")
    
    if success_count == total_count:
        logger.info("\n✅ TODOS LOS SCRIPTS EJECUTADOS EXITOSAMENTE")
    else:
        logger.warning(f"\n⚠️ {total_count - success_count} scripts tuvieron errores")
    
    db.close()
    return 0 if success_count == total_count else 1

if __name__ == "__main__":
    sys.exit(main())

