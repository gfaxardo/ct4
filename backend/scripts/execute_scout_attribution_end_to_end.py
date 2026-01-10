#!/usr/bin/env python3
"""
Ejecución End-to-End: Atribución de Scouts Completa
===================================================

Ejecuta en orden:
1) Diagnóstico inicial
2) Identity backfill scouting_daily
3) Lead_ledger backfill
4) Crear/actualizar vistas
5) Verificación final

SALIDA FINAL:
- Métricas BEFORE / AFTER
- % scouting_daily con identity
- % scout satisfactorio global
"""

import sys
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


def get_diagnostic_metrics(db_session) -> Dict[str, Any]:
    """Obtiene métricas diagnósticas iniciales"""
    metrics = {}
    
    try:
        # Total scouting_daily con scout_id
        query1 = text("""
            SELECT COUNT(*) as total
            FROM public.module_ct_scouting_daily
            WHERE scout_id IS NOT NULL
        """)
        result1 = db_session.execute(query1)
        metrics['scouting_daily_with_scout'] = result1.scalar()
        
        # Scouting_daily con identity_links
        query2 = text("""
            SELECT COUNT(DISTINCT sd.id) as total
            FROM public.module_ct_scouting_daily sd
            WHERE sd.scout_id IS NOT NULL
                AND EXISTS (
                    SELECT 1 FROM canon.identity_links il
                    WHERE il.source_table = 'module_ct_scouting_daily'
                        AND il.source_pk = sd.id::TEXT
                )
        """)
        result2 = db_session.execute(query2)
        metrics['scouting_daily_with_identity'] = result2.scalar()
        
        # Scout satisfactorio (lead_ledger)
        query3 = text("""
            SELECT COUNT(DISTINCT il.person_key) as total
            FROM canon.identity_links il
            WHERE il.source_table = 'module_ct_scouting_daily'
                AND EXISTS (
                    SELECT 1 FROM observational.lead_ledger ll
                    WHERE ll.person_key = il.person_key
                        AND ll.attributed_scout_id IS NOT NULL
                )
        """)
        result3 = db_session.execute(query3)
        metrics['scouting_daily_with_satisfactory'] = result3.scalar()
        
        # Total personas con scout satisfactorio
        query4 = text("""
            SELECT COUNT(DISTINCT person_key) as total
            FROM observational.lead_ledger
            WHERE attributed_scout_id IS NOT NULL
        """)
        result4 = db_session.execute(query4)
        metrics['total_satisfactory_scout'] = result4.scalar()
        
        # Categoría D
        query5 = text("""
            SELECT COUNT(DISTINCT le.person_key) as total
            FROM observational.lead_events le
            WHERE le.person_key IS NOT NULL
                AND (
                    le.scout_id IS NOT NULL 
                    OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL)
                )
                AND NOT EXISTS (
                    SELECT 1 FROM observational.lead_ledger ll
                    WHERE ll.person_key = le.person_key
                        AND ll.attributed_scout_id IS NOT NULL
                )
        """)
        result5 = db_session.execute(query5)
        metrics['category_d_count'] = result5.scalar()
        
        # Conflictos
        query6 = text("""
            SELECT COUNT(*) as total
            FROM ops.v_scout_attribution_conflicts
        """)
        try:
            result6 = db_session.execute(query6)
            metrics['conflicts_count'] = result6.scalar()
        except:
            metrics['conflicts_count'] = 0
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {e}", exc_info=True)
    
    return metrics


def execute_sql_file(db_session, sql_file: Path):
    """Ejecuta un archivo SQL"""
    try:
        if not sql_file.exists():
            return False, f"Archivo no existe: {sql_file}"
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Ejecutar SQL
        db_session.execute(text(sql_content))
        db_session.commit()
        
        return True, f"Ejecutado: {sql_file.name}"
    
    except Exception as e:
        db_session.rollback()
        return False, f"Error en {sql_file.name}: {str(e)}"


def execute_python_script(script_path: Path):
    """Ejecuta un script Python"""
    try:
        if not script_path.exists():
            return False, f"Archivo no existe: {script_path}"
        
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            cwd=str(script_path.parent.parent)
        )
        
        if result.returncode == 0:
            return True, f"Ejecutado: {script_path.name}"
        else:
            return False, f"Error en {script_path.name}: {result.stderr}"
    
    except Exception as e:
        return False, f"Error ejecutando {script_path.name}: {str(e)}"


def main():
    """Ejecuta el pipeline end-to-end completo"""
    
    logger.info("="*80)
    logger.info("EJECUCIÓN END-TO-END: ATRIBUCIÓN DE SCOUTS COMPLETA")
    logger.info("="*80)
    
    scripts_dir = Path(__file__).parent
    sql_dir = scripts_dir / "sql"
    db = SessionLocal()
    
    execution_log = []
    
    try:
        # ====================================================================
        # PASO 1: Diagnóstico inicial
        # ====================================================================
        logger.info("\n" + "="*80)
        logger.info("PASO 1: DIAGNÓSTICO INICIAL")
        logger.info("="*80)
        
        metrics_before = get_diagnostic_metrics(db)
        
        logger.info("Métricas ANTES:")
        logger.info(f"  - scouting_daily con scout_id: {metrics_before.get('scouting_daily_with_scout', 0):,}")
        logger.info(f"  - scouting_daily con identity: {metrics_before.get('scouting_daily_with_identity', 0):,}")
        logger.info(f"  - scouting_daily scout satisfactorio: {metrics_before.get('scouting_daily_with_satisfactory', 0):,}")
        logger.info(f"  - Total scout satisfactorio: {metrics_before.get('total_satisfactory_scout', 0):,}")
        logger.info(f"  - Categoría D: {metrics_before.get('category_d_count', 0):,}")
        logger.info(f"  - Conflictos: {metrics_before.get('conflicts_count', 0):,}")
        
        if metrics_before.get('scouting_daily_with_scout', 0) > 0:
            pct_identity = (metrics_before.get('scouting_daily_with_identity', 0) / metrics_before['scouting_daily_with_scout']) * 100
            pct_satisfactory = (metrics_before.get('scouting_daily_with_satisfactory', 0) / metrics_before['scouting_daily_with_scout']) * 100
            logger.info(f"  - % con identity: {pct_identity:.1f}%")
            logger.info(f"  - % scout satisfactorio: {pct_satisfactory:.1f}%")
        
        execution_log.append(("diagnóstico", True, "Métricas iniciales obtenidas"))
        
        # ====================================================================
        # PASO 2: Identity backfill scouting_daily
        # ====================================================================
        logger.info("\n" + "="*80)
        logger.info("PASO 2: IDENTITY BACKFILL SCOUTING_DAILY")
        logger.info("="*80)
        
        backfill_script = scripts_dir / "backfill_identity_links_scouting_daily.py"
        success, msg = execute_python_script(backfill_script)
        execution_log.append(("backfill_identity_links_scouting_daily", success, msg))
        
        if success:
            logger.info(f"✓ {msg}")
        else:
            logger.warning(f"✗ {msg}")
            logger.warning("Continuando aunque haya errores...")
        
        # ====================================================================
        # PASO 3: Lead_ledger backfill
        # ====================================================================
        logger.info("\n" + "="*80)
        logger.info("PASO 3: LEAD_LEDGER BACKFILL")
        logger.info("="*80)
        
        backfill_sql = sql_dir / "backfill_lead_ledger_attributed_scout.sql"
        success, msg = execute_sql_file(db, backfill_sql)
        execution_log.append(("backfill_lead_ledger_attributed_scout", success, msg))
        
        if success:
            logger.info(f"✓ {msg}")
        else:
            logger.warning(f"✗ {msg}")
            logger.warning("Continuando aunque haya errores...")
        
        # ====================================================================
        # PASO 4: Crear/actualizar vistas
        # ====================================================================
        logger.info("\n" + "="*80)
        logger.info("PASO 4: CREAR/ACTUALIZAR VISTAS")
        logger.info("="*80)
        
        views = [
            "create_v_scout_attribution_raw.sql",
            "create_v_scout_attribution.sql",
            "create_v_scout_attribution_conflicts.sql",
            "create_v_persons_without_scout_categorized.sql",
            "create_v_cabinet_leads_missing_scout_alerts.sql",
            "create_v_scout_payment_base.sql"
        ]
        
        for view_file in views:
            view_path = sql_dir / view_file
            success, msg = execute_sql_file(db, view_path)
            execution_log.append((view_file.replace('.sql', ''), success, msg))
            
            if success:
                logger.info(f"✓ {msg}")
            else:
                logger.warning(f"✗ {msg}")
        
        # ====================================================================
        # PASO 5: Verificación final
        # ====================================================================
        logger.info("\n" + "="*80)
        logger.info("PASO 5: VERIFICACIÓN FINAL")
        logger.info("="*80)
        
        metrics_after = get_diagnostic_metrics(db)
        
        logger.info("Métricas DESPUÉS:")
        logger.info(f"  - scouting_daily con scout_id: {metrics_after.get('scouting_daily_with_scout', 0):,}")
        logger.info(f"  - scouting_daily con identity: {metrics_after.get('scouting_daily_with_identity', 0):,}")
        logger.info(f"  - scouting_daily scout satisfactorio: {metrics_after.get('scouting_daily_with_satisfactory', 0):,}")
        logger.info(f"  - Total scout satisfactorio: {metrics_after.get('total_satisfactory_scout', 0):,}")
        logger.info(f"  - Categoría D: {metrics_after.get('category_d_count', 0):,}")
        logger.info(f"  - Conflictos: {metrics_after.get('conflicts_count', 0):,}")
        
        if metrics_after.get('scouting_daily_with_scout', 0) > 0:
            pct_identity = (metrics_after.get('scouting_daily_with_identity', 0) / metrics_after['scouting_daily_with_scout']) * 100
            pct_satisfactory = (metrics_after.get('scouting_daily_with_satisfactory', 0) / metrics_after['scouting_daily_with_scout']) * 100
            logger.info(f"  - % con identity: {pct_identity:.1f}%")
            logger.info(f"  - % scout satisfactorio: {pct_satisfactory:.1f}%")
        
        # Comparación
        logger.info("\n" + "-"*80)
        logger.info("COMPARACIÓN BEFORE / AFTER:")
        logger.info("-"*80)
        
        if metrics_before.get('scouting_daily_with_identity', 0) > 0:
            improvement_identity = metrics_after.get('scouting_daily_with_identity', 0) - metrics_before.get('scouting_daily_with_identity', 0)
            logger.info(f"  - Identity links creados: +{improvement_identity:,}")
        
        if metrics_before.get('scouting_daily_with_satisfactory', 0) > 0:
            improvement_satisfactory = metrics_after.get('scouting_daily_with_satisfactory', 0) - metrics_before.get('scouting_daily_with_satisfactory', 0)
            logger.info(f"  - Scout satisfactorio mejorado: +{improvement_satisfactory:,}")
        
        category_d_reduction = metrics_before.get('category_d_count', 0) - metrics_after.get('category_d_count', 0)
        if category_d_reduction > 0:
            logger.info(f"  - Categoría D reducida: -{category_d_reduction:,}")
        
        # ====================================================================
        # RESUMEN FINAL
        # ====================================================================
        logger.info("\n" + "="*80)
        logger.info("RESUMEN FINAL")
        logger.info("="*80)
        
        for step, success, msg in execution_log:
            status = "✓" if success else "✗"
            logger.info(f"{status} {step}: {msg}")
        
        # Validaciones finales
        logger.info("\n" + "-"*80)
        logger.info("VALIDACIONES FINALES:")
        logger.info("-"*80)
        
        if metrics_after.get('scouting_daily_with_identity', 0) > metrics_before.get('scouting_daily_with_identity', 0):
            logger.info("✓ scouting_daily scout satisfactorio > 0%")
        else:
            logger.warning("✗ scouting_daily scout satisfactorio no mejoró")
        
        if metrics_after.get('category_d_count', 0) < metrics_before.get('category_d_count', 0):
            logger.info("✓ categoría D reducida")
        else:
            logger.warning("✗ categoría D no se redujo")
        
        if metrics_after.get('conflicts_count', 0) <= metrics_before.get('conflicts_count', 0):
            logger.info("✓ conflictos no crecieron sin razón")
        else:
            logger.warning("✗ conflictos aumentaron")
        
        logger.info("\n" + "="*80)
        logger.info("EJECUCIÓN COMPLETADA")
        logger.info("="*80)
        
    except Exception as e:
        logger.error(f"Error en ejecución end-to-end: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
