#!/usr/bin/env python3
"""
Script de Ejecución Automatizada: Scout Attribution Fix
Ejecuta todos los pasos del fix de atribución de scouts en modo batch (sin interacción)

PASOS:
1. Inventory (00)
2. Create/replace vistas (10-12)
3. Diagnose (baseline)
4. Backfill audit tables (22)
5. Backfill identity_links scouting_daily (si existe tabla)
6. Backfill lead_ledger attributed_scout (20)
7. Backfill cabinet leads -> events (si posible) (21)
8. Recreate/refresh vistas
9. Verify (03)
10. Genera SCOUT_ATTRIBUTION_AFTER_REPORT.md con antes/después + métricas + warnings

Debe funcionar en Windows (encoding UTF-8, sin emojis, sin input()).
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
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)


def execute_sql_file(sql_file_path: Path, description: str, database_url: str):
    """Ejecuta un archivo SQL completo. Retorna (success, output)"""
    logger.info(f"Ejecutando: {description}")
    logger.info(f"Archivo: {sql_file_path.name}")
    
    try:
        if not sql_file_path.exists():
            logger.warning(f"No se encuentra el archivo {sql_file_path}")
            return False, f"Archivo no encontrado: {sql_file_path}"
        
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
                return True, "OK"
                
    except Exception as e:
        error_msg = f"Error al ejecutar {description}: {str(e)[:300]}"
        logger.error(f"[ERROR] {error_msg}")
        import traceback
        logger.error(traceback.format_exc())
        return False, error_msg


def execute_python_script(script_path: Path, description: str):
    """Ejecuta un script Python. Retorna (success, output)"""
    logger.info(f"Ejecutando: {description}")
    logger.info(f"Script: {script_path.name}")
    
    try:
        if not script_path.exists():
            logger.warning(f"No se encuentra el script {script_path}")
            return False, f"Script no encontrado: {script_path}"
        
        import subprocess
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=str(script_path.parent)
        )
        
        if result.returncode == 0:
            logger.info(f"[OK] {description} completado")
            output = result.stdout[-500:] if result.stdout else ""
            return True, output
        else:
            error_msg = f"{description} falló con código {result.returncode}"
            logger.error(f"[ERROR] {error_msg}")
            if result.stderr:
                logger.error(f"Error: {result.stderr[-500:]}")
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Error al ejecutar {description}: {str(e)[:300]}"
        logger.error(f"[ERROR] {error_msg}")
        return False, error_msg


def get_stats(database_url: str) -> dict:
    """Obtiene estadísticas de scout attribution"""
    logger.info("Obteniendo estadísticas...")
    
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
                    WHERE EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
                    )
                    AND sd.scout_id IS NOT NULL
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
                    WHERE EXISTS (
                        SELECT 1 FROM information_schema.tables 
                        WHERE table_schema = 'public' AND table_name = 'module_ct_scouting_daily'
                    )
                    AND sd.scout_id IS NOT NULL
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
                try:
                    cur.execute("SELECT COUNT(*) FROM ops.v_scout_attribution_conflicts")
                    stats['conflicts'] = cur.fetchone()[0]
                except:
                    stats['conflicts'] = -1  # Vista no existe aún
                
    except Exception as e:
        logger.warning(f"Error obteniendo estadísticas: {e}")
        stats = {}
    
    return stats


def generate_report(before_stats: dict, after_stats: dict, execution_log: list, output_file: Path):
    """Genera reporte markdown con resultados"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("# Scout Attribution Fix - Reporte de Ejecución\n\n")
        f.write(f"**Fecha de ejecución**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Estadísticas Antes del Fix\n\n")
        if before_stats:
            for key, value in before_stats.items():
                f.write(f"- **{key}**: {value}\n")
        else:
            f.write("- No disponibles\n")
        f.write("\n")
        
        f.write("## Estadísticas Después del Fix\n\n")
        if after_stats:
            for key, value in after_stats.items():
                f.write(f"- **{key}**: {value}\n")
        else:
            f.write("- No disponibles\n")
        f.write("\n")
        
        f.write("## Mejoras\n\n")
        if before_stats and after_stats:
            if 'persons_with_scout' in before_stats and 'persons_with_scout' in after_stats:
                improvement = after_stats['persons_with_scout'] - before_stats['persons_with_scout']
                f.write(f"- **Personas con scout satisfactorio**: +{improvement}\n")
            
            if 'scouting_daily_with_ledger_scout' in before_stats and 'scouting_daily_with_ledger_scout' in after_stats:
                improvement = after_stats['scouting_daily_with_ledger_scout'] - before_stats['scouting_daily_with_ledger_scout']
                f.write(f"- **scouting_daily con lead_ledger scout**: +{improvement}\n")
        f.write("\n")
        
        f.write("## Log de Ejecución\n\n")
        for step, success, message in execution_log:
            status = "OK" if success else "ERROR"
            f.write(f"- **{step}**: {status} - {message[:100]}\n")
        f.write("\n")
        
        f.write("## Warnings\n\n")
        warnings = [msg for step, success, msg in execution_log if not success]
        if warnings:
            for warning in warnings:
                f.write(f"- {warning}\n")
        else:
            f.write("- Ninguno\n")
        f.write("\n")


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
    reports_dir = sql_dir
    
    # Obtener estadísticas ANTES
    logger.info("\n" + "="*70)
    logger.info("OBTENIENDO ESTADÍSTICAS ANTES DEL FIX")
    logger.info("="*70)
    before_stats = get_stats(database_url)
    logger.info(f"ANTES: {before_stats}")
    
    execution_log = []
    success = True
    
    # PASO 1: Inventory
    logger.info("\n" + "="*70)
    logger.info("PASO 1: INVENTORY SCOUT SOURCES")
    logger.info("="*70)
    result, msg = execute_sql_file(
        sql_dir / "00_inventory_scout_sources.sql",
        "Inventario de fuentes scout",
        database_url
    )
    execution_log.append(("00_inventory_scout_sources", result, msg))
    if not result:
        logger.warning("El inventario tuvo errores, pero continuando...")
    
    # PASO 2: Create/replace vistas canónicas
    logger.info("\n" + "="*70)
    logger.info("PASO 2: CREAR/ACTUALIZAR VISTAS CANÓNICAS")
    logger.info("="*70)
    for view_file in ["10_create_v_scout_attribution_raw.sql", "11_create_v_scout_attribution.sql", 
                      "12_create_v_scout_attribution_conflicts.sql"]:
        result, msg = execute_sql_file(
            sql_dir / view_file,
            f"Crear vista {view_file}",
            database_url
        )
        execution_log.append((view_file, result, msg))
        if not result:
            logger.warning(f"Error creando {view_file}, pero continuando...")
    
    # PASO 3: Diagnose (baseline)
    logger.info("\n" + "="*70)
    logger.info("PASO 3: DIAGNÓSTICO (BASELINE)")
    logger.info("="*70)
    result, msg = execute_sql_file(
        sql_dir / "01_diagnose_scout_attribution.sql",
        "Diagnóstico de atribución scout",
        database_url
    )
    execution_log.append(("01_diagnose_scout_attribution", result, msg))
    if not result:
        logger.warning("El diagnóstico tuvo errores, pero continuando...")
    
    # PASO 4: Backfill audit tables
    logger.info("\n" + "="*70)
    logger.info("PASO 4: CREAR TABLAS DE AUDITORÍA")
    logger.info("="*70)
    result, msg = execute_sql_file(
        sql_dir / "22_create_backfill_audit_tables.sql",
        "Crear tablas de auditoría",
        database_url
    )
    execution_log.append(("22_create_backfill_audit_tables", result, msg))
    
    # PASO 5: Backfill identity_links scouting_daily
    logger.info("\n" + "="*70)
    logger.info("PASO 5: BACKFILL IDENTITY_LINKS SCOUTING_DAILY")
    logger.info("="*70)
    result, msg = execute_python_script(
        script_dir / "backfill_identity_links_scouting_daily.py",
        "Backfill de identity_links para scouting_daily"
    )
    execution_log.append(("backfill_identity_links_scouting_daily", result, msg))
    if not result:
        logger.warning("Backfill de identity_links tuvo errores, pero continuando...")
    
    # PASO 6: Backfill lead_ledger attributed_scout
    logger.info("\n" + "="*70)
    logger.info("PASO 6: BACKFILL LEAD_LEDGER ATTRIBUTED_SCOUT")
    logger.info("="*70)
    result, msg = execute_sql_file(
        sql_dir / "20_backfill_lead_ledger_attributed_scout.sql",
        "Backfill de attributed_scout_id en lead_ledger",
        database_url
    )
    execution_log.append(("20_backfill_lead_ledger_attributed_scout", result, msg))
    if not result:
        logger.warning("Backfill de lead_ledger tuvo errores, pero continuando...")
    
    # PASO 7: Backfill cabinet leads -> events (si posible)
    logger.info("\n" + "="*70)
    logger.info("PASO 7: BACKFILL CABINET LEADS -> EVENTS")
    logger.info("="*70)
    result, msg = execute_sql_file(
        sql_dir / "21_backfill_lead_events_scout_from_cabinet_leads.sql",
        "Backfill de scout_id en lead_events desde cabinet_leads",
        database_url
    )
    execution_log.append(("21_backfill_lead_events_scout_from_cabinet_leads", result, msg))
    if not result:
        logger.warning("Backfill de cabinet leads tuvo errores, pero continuando...")
    
    # PASO 8: Recreate/refresh vistas (incluyendo integración Yango)
    logger.info("\n" + "="*70)
    logger.info("PASO 8: RECREAR/ACTUALIZAR VISTAS")
    logger.info("="*70)
    for view_file in ["04_yango_collection_with_scout.sql", "13_create_v_scout_daily_expected_base.sql",
                      "02_categorize_persons_without_scout.sql"]:
        result, msg = execute_sql_file(
            sql_dir / view_file,
            f"Crear/actualizar vista {view_file}",
            database_url
        )
        execution_log.append((view_file, result, msg))
        if not result:
            logger.warning(f"Error creando {view_file}, pero continuando...")
    
    # PASO 9: Verify
    logger.info("\n" + "="*70)
    logger.info("PASO 9: VERIFICACIÓN")
    logger.info("="*70)
    result, msg = execute_sql_file(
        sql_dir / "03_verify_scout_attribution_views.sql",
        "Verificación de vistas de scout attribution",
        database_url
    )
    execution_log.append(("03_verify_scout_attribution_views", result, msg))
    
    # Obtener estadísticas DESPUÉS
    logger.info("\n" + "="*70)
    logger.info("OBTENIENDO ESTADÍSTICAS DESPUÉS DEL FIX")
    logger.info("="*70)
    after_stats = get_stats(database_url)
    logger.info(f"DESPUÉS: {after_stats}")
    
    # Generar reporte
    logger.info("\n" + "="*70)
    logger.info("GENERANDO REPORTE")
    logger.info("="*70)
    report_file = reports_dir / "SCOUT_ATTRIBUTION_AFTER_REPORT.md"
    generate_report(before_stats, after_stats, execution_log, report_file)
    logger.info(f"Reporte generado: {report_file}")
    
    # Resumen final
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
