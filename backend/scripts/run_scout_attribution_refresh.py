#!/usr/bin/env python3
"""
Job: Refresh Scout Attribution (Run Once)
=========================================
Ejecuta todos los backfills y refreshes necesarios para scout attribution.
Idempotente y seguro.
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, date, timezone
from typing import Dict, Any

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.models.ops import IngestionRun, RunStatus, JobType

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


def execute_sql_file(db_session, sql_file: Path) -> tuple[bool, str]:
    """Ejecuta un archivo SQL"""
    try:
        if not sql_file.exists():
            return False, f"Archivo no existe: {sql_file}"
        
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        db_session.execute(text(sql_content))
        db_session.commit()
        
        return True, f"Ejecutado: {sql_file.name}"
    
    except Exception as e:
        db_session.rollback()
        logger.error(f"Error en {sql_file.name}: {e}", exc_info=True)
        return False, f"Error: {str(e)}"


def run_identity_backfill(db_session) -> Dict[str, Any]:
    """Ejecuta backfill de identity_links para scouting_daily"""
    try:
        logger.info("Ejecutando backfill de identity_links para scouting_daily...")
        
        # Importar módulo desde el path correcto
        scripts_dir = Path(__file__).parent
        backfill_module_path = scripts_dir / "backfill_identity_links_scouting_daily.py"
        
        import importlib.util
        spec = importlib.util.spec_from_file_location("backfill_identity_links_scouting_daily", backfill_module_path)
        backfill_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(backfill_module)
        
        # Ejecutar (ya tiene su propia sesión)
        result = backfill_module.main()
        
        return {
            "status": "completed",
            "created": result.get("created", 0),
            "skipped": result.get("skipped", 0),
            "errors": result.get("errors", 0)
        }
    except Exception as e:
        logger.error(f"Error en backfill identity_links: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }


def run_lead_ledger_backfill(db_session) -> Dict[str, Any]:
    """Ejecuta backfill de lead_ledger attributed_scout"""
    try:
        logger.info("Ejecutando backfill de lead_ledger attributed_scout...")
        
        scripts_dir = Path(__file__).parent
        sql_file = scripts_dir / "sql" / "backfill_lead_ledger_attributed_scout.sql"
        
        success, msg = execute_sql_file(db_session, sql_file)
        
        if not success:
            return {"status": "failed", "error": msg}
        
        # Contar registros actualizados (último minuto)
        query = text("""
            SELECT COUNT(*) 
            FROM ops.lead_ledger_scout_backfill_audit
            WHERE backfill_timestamp >= NOW() - INTERVAL '1 minute'
        """)
        result = db_session.execute(query)
        updated_count = result.scalar()
        
        return {
            "status": "completed",
            "updated": updated_count
        }
    except Exception as e:
        logger.error(f"Error en backfill lead_ledger: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }


def refresh_views(db_session) -> Dict[str, Any]:
    """Refresca vistas de atribución scout"""
    try:
        logger.info("Refrescando vistas de atribución scout...")
        
        scripts_dir = Path(__file__).parent / "sql"
        
        # Lista de vistas a refrescar (en orden)
        views = [
            "10_create_v_scout_attribution_raw.sql",
            "11_create_v_scout_attribution.sql",
            "create_v_scout_attribution_conflicts.sql",
            "create_v_persons_without_scout_categorized.sql",
            "create_v_cabinet_leads_missing_scout_alerts.sql",
            "create_v_scout_payment_base.sql",
            "01_metrics_scout_attribution.sql",
        ]
        
        results = {}
        for view_file in views:
            view_path = scripts_dir / view_file
            if view_path.exists():
                success, msg = execute_sql_file(db_session, view_path)
                results[view_file] = {"success": success, "message": msg}
            else:
                results[view_file] = {"success": False, "message": "No existe"}
        
        return {
            "status": "completed",
            "views": results
        }
    except Exception as e:
        logger.error(f"Error refrescando vistas: {e}", exc_info=True)
        return {
            "status": "failed",
            "error": str(e)
        }


def main():
    """Ejecuta refresh completo de scout attribution"""
    db = SessionLocal()
    run_id = None
    
    try:
        # Crear registro de job run
        job_run = IngestionRun(
            job_type=JobType.IDENTITY_RUN,  # Usar campo existente como texto
            status=RunStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            stats={}
        )
        db.add(job_run)
        db.commit()
        db.refresh(job_run)
        run_id = job_run.id
        
        logger.info(f"Iniciando scout attribution refresh (run_id={run_id})...")
        
        summary = {
            "run_id": run_id,
            "started_at": job_run.started_at.isoformat(),
            "steps": {}
        }
        
        # Paso 1: Backfill identity_links
        summary["steps"]["identity_backfill"] = run_identity_backfill(db)
        
        # Paso 2: Backfill lead_ledger
        summary["steps"]["lead_ledger_backfill"] = run_lead_ledger_backfill(db)
        
        # Paso 3: Refresh vistas
        summary["steps"]["refresh_views"] = refresh_views(db)
        
        # Calcular estado final
        all_completed = all(
            step.get("status") == "completed"
            for step in summary["steps"].values()
        )
        any_failed = any(
            step.get("status") == "failed"
            for step in summary["steps"].values()
        )
        
        final_status = RunStatus.COMPLETED if all_completed and not any_failed else RunStatus.FAILED
        
        # Actualizar registro de job
        job_run.status = final_status
        job_run.completed_at = datetime.now(timezone.utc)
        job_run.stats = summary
        
        db.commit()
        
        logger.info(f"Scout attribution refresh completado (run_id={run_id}, status={final_status})")
        
        return summary
        
    except Exception as e:
        logger.error(f"Error en scout attribution refresh: {e}", exc_info=True)
        
        if run_id:
            job_run = db.query(IngestionRun).filter(IngestionRun.id == run_id).first()
            if job_run:
                job_run.status = RunStatus.FAILED
                job_run.completed_at = datetime.now(timezone.utc)
                job_run.error_message = str(e)
                db.commit()
        
        raise
        
    finally:
        db.close()


if __name__ == "__main__":
    import io
    import sys
    
    # Configurar encoding UTF-8 para Windows
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    try:
        result = main()
        print(f"\n[OK] Scout attribution refresh completado exitosamente")
        print(f"Run ID: {result['run_id']}")
        print(f"Summary: {result}")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] Error en scout attribution refresh: {e}")
        sys.exit(1)

