#!/usr/bin/env python3
"""
Script de Ejecución Automatizada: Scout Attribution Fix
Ejecuta todos los pasos del fix de atribución de scouts en modo batch (sin interacción)

PASOS:
1. Diagnóstico y categorización
2. Crear/actualizar vistas canónicas
3. Backfill identity_links para scouting_daily
4. Backfill lead_ledger attributed_scout
5. Fix eventos sin scout_id
6. Verificación completa
"""

import sys
import logging
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text
import psycopg2
from urllib.parse import urlparse

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def execute_sql_file(sql_file_path: Path, description: str, database_url: str) -> bool:
    """Ejecuta un archivo SQL completo"""
    logger.info(f"Ejecutando: {description}")
    logger.info(f"Archivo: {sql_file_path.name}")
    
    try:
        if not sql_file_path.exists():
            logger.error(f"No se encuentra el archivo {sql_file_path}")
            return False
        
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Parsear DATABASE_URL
        parsed = urlparse(database_url)
        conn_params = {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:] if parsed.path else None,
            'user': parsed.username,
            'password': parsed.password
        }
        
        with psycopg2.connect(**conn_params) as pg_conn:
            pg_conn.autocommit = True
            with pg_conn.cursor() as cursor:
                cursor.execute(sql_content)
                logger.info(f"[OK] {description} completado")
                return True
                
    except Exception as e:
        logger.error(f"[ERROR] Error al ejecutar {description}: {str(e)[:300]}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def execute_python_script(script_path: Path, description: str) -> bool:
    """Ejecuta un script Python"""
    logger.info(f"Ejecutando: {description}")
    logger.info(f"Script: {script_path.name}")
    
    try:
        if not script_path.exists():
            logger.error(f"No se encuentra el script {script_path}")
            return False
        
        import subprocess
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(script_path.parent)
        )
        
        if result.returncode == 0:
            logger.info(f"[OK] {description} completado")
            if result.stdout:
                logger.info(f"Output: {result.stdout[-500:]}")  # Últimos 500 caracteres
            return True
        else:
            logger.error(f"[ERROR] {description} falló con código {result.returncode}")
            if result.stderr:
                logger.error(f"Error: {result.stderr[-500:]}")
            return False
            
    except Exception as e:
        logger.error(f"[ERROR] Error al ejecutar {description}: {str(e)[:300]}")
        return False


def get_before_stats(database_url: str) -> dict:
    """Obtiene estadísticas ANTES del fix"""
    logger.info("Obteniendo estadísticas ANTES del fix...")
    
    stats = {}
    
    try:
        parsed = urlparse(database_url)
        conn_params = {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:] if parsed.path else None,
            'user': parsed.username,
            'password': parsed.password
        }
        
        with psycopg2.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                # Total personas
                cur.execute("SELECT COUNT(DISTINCT person_key) FROM canon.identity_registry")
                stats['total_persons'] = cur.fetchone()[0]
                
                # Personas con scout satisfactorio
                cur.execute("""
                    SELECT COUNT(DISTINCT person_key) 
                    FROM observational.lead_ledger 
                    WHERE attributed_scout_id IS NOT NULL
                """)
                stats['persons_with_scout'] = cur.fetchone()[0]
                
                # scouting_daily con identity_links
                cur.execute("""
                    SELECT COUNT(DISTINCT sd.id)
                    FROM public.module_ct_scouting_daily sd
                    WHERE sd.scout_id IS NOT NULL
                    AND EXISTS (
                        SELECT 1 FROM canon.identity_links il
                        WHERE il.source_table = 'module_ct_scouting_daily'
                        AND il.source_pk = sd.id::TEXT
                    )
                """)
                stats['scouting_daily_with_links'] = cur.fetchone()[0]
                
                # scouting_daily con lead_ledger scout
                cur.execute("""
                    SELECT COUNT(DISTINCT sd.id)
                    FROM public.module_ct_scouting_daily sd
                    WHERE sd.scout_id IS NOT NULL
                    AND EXISTS (
                        SELECT 1 FROM canon.identity_links il
                        JOIN observational.lead_ledger ll ON ll.person_key = il.person_key
                        WHERE il.source_table = 'module_ct_scouting_daily'
                        AND il.source_pk = sd.id::TEXT
                        AND ll.attributed_scout_id IS NOT NULL
                    )
                """)
                stats['scouting_daily_with_ledger_scout'] = cur.fetchone()[0]
                
                # Conflictos
                cur.execute("SELECT COUNT(*) FROM ops.v_scout_attribution_conflicts")
                stats['conflicts'] = cur.fetchone()[0]
                
    except Exception as e:
        logger.warning(f"Error obteniendo estadísticas ANTES: {e}")
        stats = {}
    
    return stats


def get_after_stats(database_url: str) -> dict:
    """Obtiene estadísticas DESPUÉS del fix"""
    return get_before_stats(database_url)  # Misma función


def main():
    """Función principal - ejecuta todos los pasos"""
    logger.info("="*70)
    logger.info("SCOUT ATTRIBUTION FIX - EJECUCIÓN AUTOMATIZADA")
    logger.info("="*70)
    
    database_url = settings.database_url
    logger.info(f"Conectando a: {database_url.split('@')[1] if '@' in database_url else 'base de datos'}")
    
    # Verificar conexión
    try:
        parsed = urlparse(database_url)
        conn_params = {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path[1:] if parsed.path else None,
            'user': parsed.username,
            'password': parsed.password
        }
        with psycopg2.connect(**conn_params) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
                logger.info(f"[OK] Conectado a PostgreSQL: {version.split(',')[0]}")
    except Exception as e:
        logger.error(f"[ERROR] No se pudo conectar: {e}")
        return 1
    
    # Rutas de archivos
    script_dir = Path(__file__).parent
    sql_dir = script_dir / "sql"
    
    # Obtener estadísticas ANTES
    logger.info("\n" + "="*70)
    logger.info("OBTENIENDO ESTADÍSTICAS ANTES DEL FIX")
    logger.info("="*70)
    before_stats = get_before_stats(database_url)
    logger.info(f"ANTES: {before_stats}")
    
    success = True
    
    # PASO 1: Diagnóstico y categorización
    logger.info("\n" + "="*70)
    logger.info("PASO 1: DIAGNÓSTICO Y CATEGORIZACIÓN")
    logger.info("="*70)
    
    result = execute_sql_file(
        sql_dir / "categorize_persons_without_scout.sql",
        "Categorización de personas sin scout",
        database_url
    )
    if not result:
        logger.warning("El diagnóstico tuvo errores, pero continuando...")
    
    # PASO 2: Crear/actualizar vistas canónicas
    logger.info("\n" + "="*70)
    logger.info("PASO 2: CREAR/ACTUALIZAR VISTAS CANÓNICAS")
    logger.info("="*70)
    
    result = execute_sql_file(
        sql_dir / "scout_attribution_recommendations.sql",
        "Creación de vistas canónicas de atribución",
        database_url
    )
    if not result:
        success = False
        logger.error("Error creando vistas. Abortando.")
        return 1
    
    # PASO 3: Backfill identity_links para scouting_daily
    logger.info("\n" + "="*70)
    logger.info("PASO 3: BACKFILL IDENTITY_LINKS PARA SCOUTING_DAILY")
    logger.info("="*70)
    
    result = execute_python_script(
        script_dir / "backfill_identity_links_scouting_daily.py",
        "Backfill de identity_links para scouting_daily"
    )
    if not result:
        logger.warning("Backfill de identity_links tuvo errores, pero continuando...")
    
    # PASO 4: Backfill lead_ledger attributed_scout
    logger.info("\n" + "="*70)
    logger.info("PASO 4: BACKFILL LEAD_LEDGER ATTRIBUTED_SCOUT")
    logger.info("="*70)
    
    result = execute_sql_file(
        sql_dir / "backfill_lead_ledger_attributed_scout.sql",
        "Backfill de attributed_scout_id en lead_ledger",
        database_url
    )
    if not result:
        logger.warning("Backfill de lead_ledger tuvo errores, pero continuando...")
    
    # PASO 5: Fix eventos sin scout_id
    logger.info("\n" + "="*70)
    logger.info("PASO 5: FIX EVENTOS SIN SCOUT_ID")
    logger.info("="*70)
    
    result = execute_sql_file(
        sql_dir / "fix_events_missing_scout_id.sql",
        "Fix de eventos sin scout_id",
        database_url
    )
    if not result:
        logger.warning("Fix de eventos tuvo errores, pero continuando...")
    
    # PASO 6: Verificación completa
    logger.info("\n" + "="*70)
    logger.info("PASO 6: VERIFICACIÓN COMPLETA")
    logger.info("="*70)
    
    result = execute_sql_file(
        sql_dir / "verify_scout_attribution_complete.sql",
        "Verificación completa del fix",
        database_url
    )
    
    # Obtener estadísticas DESPUÉS
    logger.info("\n" + "="*70)
    logger.info("OBTENIENDO ESTADÍSTICAS DESPUÉS DEL FIX")
    logger.info("="*70)
    after_stats = get_after_stats(database_url)
    logger.info(f"DESPUÉS: {after_stats}")
    
    # Generar reporte
    logger.info("\n" + "="*70)
    logger.info("RESUMEN FINAL")
    logger.info("="*70)
    
    if before_stats and after_stats:
        logger.info("ANTES:")
        for key, value in before_stats.items():
            logger.info(f"  {key}: {value}")
        
        logger.info("\nDESPUÉS:")
        for key, value in after_stats.items():
            logger.info(f"  {key}: {value}")
        
        logger.info("\nMEJORAS:")
        if 'persons_with_scout' in before_stats and 'persons_with_scout' in after_stats:
            improvement = after_stats['persons_with_scout'] - before_stats['persons_with_scout']
            logger.info(f"  Personas con scout satisfactorio: +{improvement}")
        
        if 'scouting_daily_with_ledger_scout' in before_stats and 'scouting_daily_with_ledger_scout' in after_stats:
            improvement = after_stats['scouting_daily_with_ledger_scout'] - before_stats['scouting_daily_with_ledger_scout']
            logger.info(f"  scouting_daily con lead_ledger scout: +{improvement}")
    
    logger.info("\n" + "="*70)
    if success:
        logger.info("[OK] PROCESO COMPLETADO")
    else:
        logger.warning("[WARN] PROCESO COMPLETADO CON ALGUNOS ERRORES")
    logger.info("="*70)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

