#!/usr/bin/env python3
"""
Script para aplicar el fix de claims Cabinet 14d (M1/M5/M25)
Ejecuta los scripts SQL necesarios usando SQLAlchemy
"""
import sys
import os
from pathlib import Path

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def execute_sql_file(engine, sql_file_path: Path, description: str):
    """Ejecuta un archivo SQL"""
    logger.info(f"\n{'='*50}")
    logger.info(f"Ejecutando: {description}")
    logger.info(f"Archivo: {sql_file_path}")
    logger.info(f"{'='*50}\n")
    
    if not sql_file_path.exists():
        logger.error(f"ERROR: No se encuentra el archivo: {sql_file_path}")
        return False
    
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        with engine.connect() as conn:
            # Ejecutar el SQL (puede tener múltiples statements)
            conn.execute(text(sql_content))
            conn.commit()
        
        logger.info(f"OK: {description} completado exitosamente")
        return True
    except Exception as e:
        logger.error(f"ERROR: Error al ejecutar {description}: {str(e)}")
        return False

def main():
    """Función principal"""
    logger.info("\n" + "="*50)
    logger.info("FIX CLAIMS CABINET 14D (M1/M5/M25)")
    logger.info("="*50)
    db_info = settings.database_url.split('@')[1] if '@' in settings.database_url else 'N/A'
    logger.info(f"Database: {db_info}")
    logger.info("="*50 + "\n")
    
    # Crear engine
    try:
        engine = create_engine(settings.database_url)
        logger.info("OK: Conexión a base de datos establecida")
    except Exception as e:
        logger.error(f"ERROR: No se pudo conectar a la base de datos: {str(e)}")
        return 1
    
    # Rutas de archivos SQL
    sql_dir = backend_dir / "sql" / "ops"
    
    success = True
    
    # Paso 1: Aplicar fix en v_claims_payment_status_cabinet
    logger.info("\nPASO 1: Aplicando fix en ops.v_claims_payment_status_cabinet...")
    fix_file = sql_dir / "v_claims_payment_status_cabinet.sql"
    result = execute_sql_file(engine, fix_file, "Fix de vista de claims")
    if not result:
        success = False
        logger.warning("\nADVERTENCIA: Error al aplicar el fix. Revisa los mensajes arriba.")
        response = input("¿Deseas continuar con la creación de la vista de auditoría? (s/N): ")
        if response.lower() != 's':
            return 1
    
    # Paso 2: Crear vista de auditoría
    logger.info("\nPASO 2: Creando vista de auditoría ops.v_cabinet_claims_audit_14d...")
    audit_file = sql_dir / "v_cabinet_claims_audit_14d.sql"
    result = execute_sql_file(engine, audit_file, "Creación de vista de auditoría")
    if not result:
        success = False
    
    # Paso 3: Validar el fix
    logger.info("\nPASO 3: Validando el fix...")
    validate_file = sql_dir / "validate_claims_fix.sql"
    if validate_file.exists():
        result = execute_sql_file(engine, validate_file, "Validación del fix")
        if not result:
            success = False
    else:
        logger.warning(f"ADVERTENCIA: Archivo de validación no encontrado: {validate_file}")
    
    # Resumen final
    logger.info("\n" + "="*50)
    if success:
        logger.info("PROCESO COMPLETADO")
        logger.info("\nPróximos pasos:")
        logger.info("1. Verifica los resultados de la validación arriba")
        logger.info("2. Consulta la vista de auditoría:")
        logger.info("   SELECT * FROM ops.v_cabinet_claims_audit_14d WHERE missing_claim_bucket != 'NONE' LIMIT 10;")
        logger.info("3. Usa el endpoint de auditoría:")
        logger.info("   GET /api/v1/ops/payments/cabinet-financial-14d/claims-audit-summary")
        logger.info("4. Monitorea que los missing claims bajan significativamente")
    else:
        logger.warning("PROCESO COMPLETADO CON ERRORES")
        logger.info("   Revisa los mensajes de error arriba")
    logger.info("="*50 + "\n")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
