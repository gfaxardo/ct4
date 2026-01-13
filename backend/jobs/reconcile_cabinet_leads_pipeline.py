#!/usr/bin/env python3
"""
Job recurrente para reconciliar leads de cabinet en limbo.
Responsabilidad: Procesar leads nuevos y rezagados para crear/actualizar identity_links.

Uso:
    python -m jobs.reconcile_cabinet_leads_pipeline --days-back 30 --limit 2000
    python -m jobs.reconcile_cabinet_leads_pipeline --only-limbo --dry-run
"""

import sys
import os
import argparse
import json
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional
import logging

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.services.ingestion import IngestionService
from app.services.lead_attribution import LeadAttributionService
from app.db import SessionLocal

# Configuración
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"
)

# Configurar logging con UTF-8 (Windows friendly)
import sys
if sys.platform == 'win32':
    # Forzar UTF-8 en Windows
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ReconcileCabinetLeadsPipeline:
    """Pipeline de reconciliación para leads de cabinet en limbo."""
    
    def __init__(self, db_session):
        self.db = db_session
        self.ingestion_service = IngestionService(db_session)
        self.attribution_service = LeadAttributionService(db_session)
        self.stats = {
            "processed": 0,
            "newly_linked": 0,
            "newly_driver_mapped": 0,
            "still_no_candidates": 0,
            "conflicts": 0,
            "errors": 0,
            "skipped": 0
        }
    
    def get_recent_leads(self, days: int = 30) -> list:
        """Obtiene leads recientes (últimos N días)."""
        cutoff_date = date.today() - timedelta(days=days)
        
        query = text("""
            SELECT DISTINCT
                COALESCE(external_id::text, id::text) AS source_pk,
                lead_created_at::date AS lead_date
            FROM public.module_ct_cabinet_leads
            WHERE lead_created_at::date >= :cutoff_date
                AND lead_created_at IS NOT NULL
            ORDER BY lead_created_at DESC
        """)
        
        result = self.db.execute(query, {"cutoff_date": cutoff_date})
        return [{"source_pk": row.source_pk, "lead_date": row.lead_date} for row in result]
    
    def get_limbo_leads(self, limbo_stages: list = None) -> list:
        """Obtiene leads en limbo (NO_IDENTITY, NO_DRIVER, TRIPS_NO_CLAIM)."""
        if limbo_stages is None:
            limbo_stages = ['NO_IDENTITY', 'NO_DRIVER', 'TRIPS_NO_CLAIM']
        
        stages_str = "', '".join(limbo_stages)
        
        query = text(f"""
            SELECT DISTINCT
                lead_source_pk AS source_pk,
                lead_date,
                limbo_stage
            FROM ops.v_cabinet_leads_limbo
            WHERE limbo_stage IN ('{stages_str}')
            ORDER BY lead_date DESC
            LIMIT 500  -- Limitar para no sobrecargar
        """)
        
        result = self.db.execute(query)
        return [
            {
                "source_pk": row.source_pk,
                "lead_date": row.lead_date,
                "limbo_stage": row.limbo_stage
            }
            for row in result
        ]
    
    def check_identity_link(self, source_pk: str) -> Optional[str]:
        """Verifica si existe identity_link para un source_pk."""
        query = text("""
            SELECT person_key
            FROM canon.identity_links
            WHERE source_table = 'module_ct_cabinet_leads'
                AND source_pk = :source_pk
            LIMIT 1
        """)
        
        result = self.db.execute(query, {"source_pk": source_pk})
        row = result.fetchone()
        return str(row.person_key) if row and row.person_key else None
    
    def check_driver_id(self, person_key: str) -> Optional[str]:
        """Verifica si existe driver_id para un person_key."""
        # Evitar bug UUID: no llamar uuid.UUID(x) si x ya es UUID o string
        # Usar directamente el string en la query SQL
        query = text("""
            SELECT source_pk AS driver_id
            FROM canon.identity_links
            WHERE source_table = 'drivers'
                AND person_key = CAST(:person_key AS uuid)
            LIMIT 1
        """)
        
        result = self.db.execute(query, {"person_key": str(person_key)})
        row = result.fetchone()
        return row.driver_id if row else None
    
    def run_ingestion_for_leads(self, leads: list) -> Dict[str, int]:
        """Ejecuta ingestion/matching para una lista de leads."""
        if not leads:
            return {"processed": 0, "matched": 0, "unmatched": 0, "skipped": 0}
        
        # Obtener rango de fechas
        dates = [lead["lead_date"] for lead in leads if lead.get("lead_date")]
        if not dates:
            return {"processed": 0, "matched": 0, "unmatched": 0, "skipped": 0}
        
        date_from = min(dates)
        date_to = max(dates)
        
        try:
            # Ejecutar ingestion
            run = self.ingestion_service.run_ingestion(
                source_tables=['module_ct_cabinet_leads'],
                scope_date_from=date_from,
                scope_date_to=date_to,
                incremental=True,
                refresh_index=False
            )
            
            # Refrescar para obtener stats
            self.db.refresh(run)
            
            # Usar stats (JSON) en lugar de stats_json
            stats = run.stats.get('cabinet_leads', {}) if run.stats else {}
            return {
                "processed": stats.get("processed", 0),
                "matched": stats.get("matched", 0),
                "unmatched": stats.get("unmatched", 0),
                "skipped": stats.get("skipped", 0)
            }
        except Exception as e:
            logger.error(f"Error ejecutando ingestion: {e}", exc_info=True)
            return {"processed": 0, "matched": 0, "unmatched": 0, "skipped": 0, "error": str(e)}
    
    def run_reconcile(self, 
                     process_recent: bool = True,
                     recent_days: int = 30,
                     process_limbo: bool = True,
                     limbo_stages: list = None,
                     dry_run: bool = False,
                     limit: int = 2000) -> Dict[str, Any]:
        """Ejecuta el pipeline de reconciliación."""
        logger.info("=" * 80)
        logger.info("INICIANDO RECONCILE CABINET LEADS PIPELINE")
        logger.info("=" * 80)
        
        all_leads = []
        
        # 1. Leads recientes
        if process_recent:
            logger.info(f"Obteniendo leads recientes (últimos {recent_days} días)...")
            recent_leads = self.get_recent_leads(days=recent_days)
            logger.info(f"Encontrados {len(recent_leads)} leads recientes")
            all_leads.extend(recent_leads)
        
        # 2. Leads en limbo
        if process_limbo:
            logger.info("Obteniendo leads en limbo...")
            limbo_leads = self.get_limbo_leads(limbo_stages=limbo_stages)
            logger.info(f"Encontrados {len(limbo_leads)} leads en limbo")
            all_leads.extend(limbo_leads)
        
        # Deduplicar por source_pk
        unique_leads = {}
        for lead in all_leads:
            source_pk = lead["source_pk"]
            if source_pk not in unique_leads:
                unique_leads[source_pk] = lead
        
        unique_leads_list = list(unique_leads.values())
        
        # Aplicar límite
        if len(unique_leads_list) > limit:
            logger.info(f"Limitando a {limit} leads (de {len(unique_leads_list)} total)")
            unique_leads_list = unique_leads_list[:limit]
        
        logger.info(f"Total leads únicos a procesar: {len(unique_leads_list)}")
        
        # 3. Ejecutar ingestion/matching
        if unique_leads_list and not dry_run:
            logger.info("Ejecutando ingestion/matching...")
            ingestion_stats = self.run_ingestion_for_leads(unique_leads_list)
            self.stats.update(ingestion_stats)
            logger.info(f"Ingestion completada: {ingestion_stats}")
        elif dry_run:
            logger.info(f"[DRY-RUN] Se procesarían {len(unique_leads_list)} leads")
            self.stats["processed"] = len(unique_leads_list)
        
        # 4. Verificar resultados
        logger.info("Verificando resultados...")
        for lead in unique_leads_list[:100]:  # Verificar primeros 100
            source_pk = lead["source_pk"]
            
            # Verificar identity_link
            person_key_before = self.check_identity_link(source_pk)
            
            # Si no tiene identity_link, ya se intentó crear en ingestion
            # Si tiene, verificar driver_id
            if person_key_before:
                driver_id_before = self.check_driver_id(person_key_before)
                if not driver_id_before:
                    # Tiene person_key pero no driver_id - esto es NO_DRIVER
                    # No podemos hacer nada aquí, el driver debe registrarse primero
                    self.stats["still_no_candidates"] += 1
            else:
                # No tiene identity_link - verificar si está en unmatched
                query = text("""
                    SELECT reason_code
                    FROM canon.identity_unmatched
                    WHERE source_table = 'module_ct_cabinet_leads'
                        AND source_pk = :source_pk
                    LIMIT 1
                """)
                result = self.db.execute(query, {"source_pk": source_pk})
                row = result.fetchone()
                if row:
                    reason = row.reason_code
                    if reason == 'NO_CANDIDATES':
                        self.stats["still_no_candidates"] += 1
                    elif reason == 'AMBIGUOUS':
                        self.stats["conflicts"] += 1
        
        # 5. Loggear métricas finales
        logger.info("=" * 80)
        logger.info("MÉTRICAS FINALES")
        logger.info("=" * 80)
        for key, value in self.stats.items():
            logger.info(f"  {key}: {value}")
        
        return self.stats


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description='Reconcile Cabinet Leads Pipeline')
    parser.add_argument('--days-back', type=int, default=30, help='Días hacia atrás para leads recientes (default: 30)')
    parser.add_argument('--limit', type=int, default=2000, help='Límite de leads a procesar (default: 2000)')
    parser.add_argument('--only-limbo', action='store_true', help='Solo procesar leads en limbo (NO_IDENTITY, NO_DRIVER, TRIPS_NO_CLAIM)')
    parser.add_argument('--dry-run', action='store_true', help='Modo dry-run (no ejecuta ingestion, solo muestra qué se procesaría)')
    parser.add_argument('--output-json', type=str, help='Ruta para guardar resultados en JSON')
    parser.add_argument('--output-csv', type=str, help='Ruta para guardar resultados en CSV')
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        pipeline = ReconcileCabinetLeadsPipeline(db)
        
        if args.dry_run:
            logger.info("=" * 80)
            logger.info("MODO DRY-RUN: No se ejecutará ingestion")
            logger.info("=" * 80)
        
        # Ejecutar reconciliación
        stats = pipeline.run_reconcile(
            process_recent=not args.only_limbo,
            recent_days=args.days_back,
            process_limbo=True,
            limbo_stages=['NO_IDENTITY', 'NO_DRIVER', 'TRIPS_NO_CLAIM'],
            dry_run=args.dry_run,
            limit=args.limit
        )
        
        logger.info("=" * 80)
        logger.info("RECONCILE COMPLETADO")
        logger.info("=" * 80)
        
        # Guardar resultados si se solicita
        if args.output_json:
            with open(args.output_json, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
            logger.info(f"Resultados guardados en: {args.output_json}")
        
        if args.output_csv:
            import csv
            with open(args.output_csv, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['metric', 'value'])
                for key, value in stats.items():
                    writer.writerow([key, value])
            logger.info(f"Resultados guardados en: {args.output_csv}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error en reconcile pipeline: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
