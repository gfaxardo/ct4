#!/usr/bin/env python3
"""
Script: create_missing_views.py
Propósito: Crear vistas faltantes en la base de datos PostgreSQL
Vistas a crear:
  - ops.v_yango_collection_with_scout
  - ops.v_claims_payment_status_cabinet
"""

import sys
import os
from pathlib import Path

# Agregar el directorio backend al path para poder importar app
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def execute_sql_file(engine, sql_file_path: Path, view_name: str, description: str):
    """Ejecuta un archivo SQL y crea una vista."""
    logger.info(f"Procesando: {view_name}")
    logger.info(f"Descripción: {description}")
    logger.info(f"Archivo: {sql_file_path}")
    
    if not sql_file_path.exists():
        logger.warning(f"⚠ ADVERTENCIA: Archivo no encontrado: {sql_file_path}")
        logger.warning("  Saltando esta vista...")
        return False
    
    try:
        # Leer el contenido del archivo SQL
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Ejecutar el SQL
        with engine.connect() as conn:
            # Ejecutar en una transacción
            with conn.begin():
                conn.execute(text(sql_content))
                conn.commit()
        
        logger.info(f"✓ Vista '{view_name}' creada exitosamente")
        return True
        
    except Exception as e:
        error_msg = str(e)
        # Verificar si el error es porque la vista ya existe (no es crítico)
        if "already exists" in error_msg.lower() or ("does not exist" in error_msg.lower() and "drop" in error_msg.lower()):
            logger.warning(f"⚠ La vista ya existe o hay dependencias. Continuando...")
            return True
        else:
            logger.error(f"✗ Error al crear la vista '{view_name}': {error_msg}")
            return False


def verify_views_exist(engine):
    """Verifica que las vistas existen en la base de datos."""
    logger.info("Verificando que las vistas existen...")
    
    verify_query = text("""
        SELECT 
            schemaname || '.' || viewname AS view_name,
            CASE WHEN viewname IS NOT NULL THEN 'EXISTE' ELSE 'NO EXISTE' END AS status
        FROM pg_views
        WHERE schemaname = 'ops'
            AND viewname IN (
                'v_payment_calculation',
                'v_cabinet_milestones_achieved_from_payment_calc',
                'v_claims_payment_status_cabinet',
                'v_yango_cabinet_claims_for_collection',
                'v_yango_collection_with_scout',
                'v_cabinet_financial_14d'
            )
        ORDER BY viewname;
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(verify_query)
            rows = result.fetchall()
            
            if rows:
                logger.info("\nEstado de las vistas:")
                for row in rows:
                    logger.info(f"  {row[0]}: {row[1]}")
            else:
                logger.warning("No se encontraron las vistas en la base de datos")
                
    except Exception as e:
        logger.warning(f"Error al verificar vistas: {e}")


def main():
    """Función principal."""
    logger.info("=" * 76)
    logger.info("Script: Crear Vistas Faltantes en PostgreSQL")
    logger.info("=" * 76)
    logger.info("")
    
    # Obtener el directorio raíz del proyecto
    project_root = backend_dir.parent
    
    # Archivos SQL a ejecutar en orden de dependencias
    # IMPORTANTE: El orden importa debido a las dependencias entre vistas
    sql_files = [
        {
            "path": backend_dir / "sql" / "ops" / "v_payment_calculation.sql",
            "name": "ops.v_payment_calculation",
            "description": "Vista canónica C2 - fuente base para cálculos de pagos",
            "required": True
        },
        {
            "path": backend_dir / "sql" / "ops" / "v_cabinet_milestones_achieved_from_payment_calc.sql",
            "name": "ops.v_cabinet_milestones_achieved_from_payment_calc",
            "description": "Vista de milestones achieved basada en v_payment_calculation",
            "required": True
        },
        {
            "path": backend_dir / "sql" / "ops" / "v_claims_payment_status_cabinet.sql",
            "name": "ops.v_claims_payment_status_cabinet",
            "description": "Vista de estado de pagos de claims cabinet",
            "required": True
        },
        {
            "path": backend_dir / "sql" / "ops" / "v_yango_cabinet_claims_for_collection.sql",
            "name": "ops.v_yango_cabinet_claims_for_collection",
            "description": "Vista de claims Yango para cobranza (base para collection)",
            "required": True
        },
        {
            "path": backend_dir / "scripts" / "sql" / "04_yango_collection_with_scout.sql",
            "name": "ops.v_yango_collection_with_scout",
            "description": "Vista de cobranza Yango con información de scout",
            "required": True
        },
        {
            "path": backend_dir / "sql" / "ops" / "v_cabinet_financial_14d.sql",
            "name": "ops.v_cabinet_financial_14d",
            "description": "Vista financiera de cabinet (14 días) - fuente de verdad para pagos",
            "required": True
        }
    ]
    
    # Crear engine de SQLAlchemy
    try:
        engine = create_engine(settings.database_url)
        logger.info("✓ Conexión exitosa a la base de datos")
    except Exception as e:
        logger.error(f"ERROR: No se pudo conectar a la base de datos: {e}")
        return 1
    
    logger.info("")
    logger.info("Ejecutando archivos SQL...")
    logger.info("")
    
    success_count = 0
    error_count = 0
    
    for sql_file in sql_files:
        logger.info("-" * 76)
        required = sql_file.get("required", True)
        success = execute_sql_file(
            engine,
            sql_file["path"],
            sql_file["name"],
            sql_file["description"]
        )
        
        if success:
            success_count += 1
        else:
            if required:
                logger.error(f"ERROR CRÍTICO: Vista requerida '{sql_file['name']}' no se pudo crear")
                logger.error("Las vistas siguientes pueden fallar debido a dependencias faltantes")
            error_count += 1
        
        logger.info("")
    
    # Resumen
    logger.info("=" * 76)
    logger.info("Resumen de Ejecución")
    logger.info("=" * 76)
    logger.info(f"Vistas creadas exitosamente: {success_count}")
    logger.info(f"Errores: {error_count}")
    logger.info("")
    
    # Verificar que las vistas existen
    verify_views_exist(engine)
    
    logger.info("")
    logger.info("=" * 76)
    logger.info("Script completado")
    logger.info("=" * 76)
    
    if error_count == 0:
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
