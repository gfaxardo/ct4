#!/usr/bin/env python3
"""
Job recurrente para reconciliar claims de cabinet 14d faltantes.
Responsabilidad: Identificar y forzar generación de claims faltantes cuando corresponde.

Uso:
    python -m jobs.reconcile_cabinet_claims_14d --days-back 21 --limit 1000
    python -m jobs.reconcile_cabinet_claims_14d --only-gaps --dry-run
"""

import sys
import os
import argparse
import json
from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional, List
import logging

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.db import SessionLocal

# Configuración
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"
)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ReconcileCabinetClaims14d:
    """Pipeline de reconciliación para claims de cabinet 14d faltantes."""
    
    def __init__(self, db_session):
        self.db = db_session
        self.stats = {
            "processed": 0,
            "gaps_found": 0,
            "claims_inserted": 0,
            "claims_updated": 0,
            "claims_skipped_paid": 0,
            "claims_skipped_rejected": 0,
            "claims_already_exist": 0,
            "invalid_conditions": 0,
            "errors": 0
        }
    
    def get_gaps(self, days_back: int = 21, limit: int = 1000, 
                 only_milestone: Optional[int] = None, week_start: Optional[str] = None) -> List[Dict[str, Any]]:
        """Obtiene gaps de claims desde v_cabinet_claims_gap_14d."""
        cutoff_date = date.today() - timedelta(days=days_back)
        
        where_conditions = ["lead_date >= :cutoff_date", "claim_status = 'CLAIM_NOT_GENERATED'"]
        params = {"cutoff_date": cutoff_date, "limit": limit}
        
        if only_milestone:
            where_conditions.append("milestone_value = :milestone_value")
            params["milestone_value"] = only_milestone
        
        if week_start:
            where_conditions.append("week_start = :week_start")
            params["week_start"] = week_start
        
        where_clause = " AND ".join(where_conditions)
        
        query = text(f"""
            SELECT 
                lead_id,
                lead_source_pk,
                driver_id,
                person_key,
                lead_date,
                week_start,
                milestone_value,
                trips_14d,
                milestone_achieved,
                expected_amount,
                claim_expected,
                claim_exists,
                claim_status,
                gap_reason
            FROM ops.v_cabinet_claims_gap_14d
            WHERE {where_clause}
            ORDER BY lead_date DESC, driver_id, milestone_value
            LIMIT :limit
        """)
        
        result = self.db.execute(query, params)
        rows = result.fetchall()
        
        return [
            {
                "lead_id": row.lead_id,
                "lead_source_pk": row.lead_source_pk,
                "driver_id": row.driver_id,
                "person_key": row.person_key,
                "lead_date": row.lead_date,
                "week_start": row.week_start,
                "milestone_value": row.milestone_value,
                "trips_14d": row.trips_14d,
                "milestone_achieved": row.milestone_achieved,
                "expected_amount": float(row.expected_amount) if row.expected_amount else 0,
                "claim_expected": row.claim_expected,
                "claim_exists": row.claim_exists,
                "claim_status": row.claim_status,
                "gap_reason": row.gap_reason
            }
            for row in rows
        ]
    
    def verify_claim_exists(self, person_key: str, lead_date: date, milestone: int) -> bool:
        """Verifica si un claim existe en tabla física canon.claims_yango_cabinet_14d."""
        query = text("""
            SELECT COUNT(*) > 0 AS exists
            FROM canon.claims_yango_cabinet_14d
            WHERE person_key::text = :person_key
                AND lead_date = :lead_date
                AND milestone = :milestone
        """)
        
        result = self.db.execute(query, {
            "person_key": person_key,
            "lead_date": lead_date,
            "milestone": milestone
        })
        return result.scalar() or False
    
    def insert_or_update_claim(self, gap: Dict[str, Any], dry_run: bool = False) -> Dict[str, str]:
        """
        Inserta o actualiza claim en tabla física canon.claims_yango_cabinet_14d.
        Idempotente: no duplica si existe, no pisa paid/rejected.
        """
        if dry_run:
            return {"action": "would_insert", "claim_id": None}
        
        person_key = gap.get("person_key")
        lead_date = gap.get("lead_date")
        milestone = gap.get("milestone_value")
        driver_id = gap.get("driver_id")
        lead_source_pk = gap.get("lead_source_pk")
        amount_expected = gap.get("expected_amount", 0)
        
        if not person_key or not lead_date or not milestone:
            return {"action": "skipped", "reason": "missing_required_fields"}
        
        # Verificar si existe claim
        check_query = text("""
            SELECT claim_id, status
            FROM canon.claims_yango_cabinet_14d
            WHERE person_key::text = :person_key
                AND lead_date = :lead_date
                AND milestone = :milestone
        """)
        
        result = self.db.execute(check_query, {
            "person_key": person_key,
            "lead_date": lead_date,
            "milestone": milestone
        })
        existing = result.fetchone()
        
        if existing:
            claim_id, status = existing
            # No pisar paid o rejected
            if status in ('paid', 'rejected'):
                return {"action": "skipped", "reason": f"status_is_{status}", "claim_id": claim_id}
            
            # Actualizar si es expected o generated
            update_query = text("""
                UPDATE canon.claims_yango_cabinet_14d
                SET status = 'generated',
                    generated_at = COALESCE(generated_at, NOW()),
                    updated_at = NOW()
                WHERE claim_id = :claim_id
                    AND status NOT IN ('paid', 'rejected')
            """)
            
            self.db.execute(update_query, {"claim_id": claim_id})
            self.db.commit()
            return {"action": "updated", "claim_id": claim_id}
        
        # Insertar nuevo claim
        insert_query = text("""
            INSERT INTO canon.claims_yango_cabinet_14d (
                person_key, driver_id, lead_source_pk, lead_date, milestone,
                amount_expected, status, expected_at, generated_at
            )
            VALUES (
                CAST(:person_key AS uuid), :driver_id, :lead_source_pk, :lead_date, :milestone,
                :amount_expected, 'generated', NOW(), NOW()
            )
            ON CONFLICT (person_key, lead_date, milestone) DO UPDATE
            SET status = 'generated',
                generated_at = COALESCE(canon.claims_yango_cabinet_14d.generated_at, NOW()),
                updated_at = NOW()
            WHERE canon.claims_yango_cabinet_14d.status NOT IN ('paid', 'rejected')
            RETURNING claim_id
        """)
        
        try:
            result = self.db.execute(insert_query, {
                "person_key": person_key,
                "driver_id": driver_id,
                "lead_source_pk": lead_source_pk,
                "lead_date": lead_date,
                "milestone": milestone,
                "amount_expected": amount_expected
            })
            claim_id = result.scalar()
            self.db.commit()
            return {"action": "inserted", "claim_id": claim_id}
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error insertando claim: {e}")
            return {"action": "error", "error": str(e)}
    
    def refresh_materialized_views(self) -> Dict[str, bool]:
        """Refresca vistas materializadas relacionadas a claims."""
        results = {}
        
        # Verificar si existen vistas materializadas
        check_query = text("""
            SELECT matviewname
            FROM pg_matviews
            WHERE schemaname = 'ops'
                AND matviewname IN (
                    'mv_claims_payment_status_cabinet',
                    'mv_yango_cabinet_claims_for_collection'
                )
        """)
        
        result = self.db.execute(check_query)
        existing_mvs = [row.matviewname for row in result]
        
        for mv_name in ['mv_claims_payment_status_cabinet', 'mv_yango_cabinet_claims_for_collection']:
            if mv_name in existing_mvs:
                try:
                    refresh_query = text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY ops.{mv_name}")
                    self.db.execute(refresh_query)
                    self.db.commit()
                    results[mv_name] = True
                    logger.info(f"Vista materializada {mv_name} refrescada")
                except Exception as e:
                    logger.error(f"Error refrescando {mv_name}: {e}")
                    results[mv_name] = False
            else:
                results[mv_name] = False
        
        return results
    
    def verify_milestone_achieved(self, driver_id: str, milestone_value: int, lead_date: date) -> bool:
        """Verifica si el milestone está achieved según v_payment_calculation."""
        query = text("""
            SELECT COUNT(*) > 0 AS achieved
            FROM ops.v_payment_calculation
            WHERE driver_id = :driver_id
                AND origin_tag = 'cabinet'
                AND rule_scope = 'partner'
                AND milestone_trips = :milestone_value
                AND milestone_achieved = true
                AND lead_date = :lead_date
                AND achieved_date::date <= (lead_date + INTERVAL '14 days')::date
                AND achieved_date::date >= lead_date
        """)
        
        result = self.db.execute(query, {
            "driver_id": driver_id,
            "milestone_value": milestone_value,
            "lead_date": lead_date
        })
        return result.scalar() or False
    
    def log_gap_analysis(self, gap: Dict[str, Any]) -> Dict[str, Any]:
        """Analiza un gap y determina si debe generarse claim."""
        analysis = {
            "should_generate": False,
            "reason": "",
            "details": {}
        }
        
        # Verificar condiciones canónicas
        if not gap.get("driver_id"):
            analysis["reason"] = "NO_DRIVER"
            analysis["details"] = {"driver_id": None}
            return analysis
        
        if not gap.get("lead_date"):
            analysis["reason"] = "NO_LEAD_DATE"
            analysis["details"] = {"lead_date": None}
            return analysis
        
        if not gap.get("milestone_achieved"):
            analysis["reason"] = "MILESTONE_NOT_ACHIEVED"
            analysis["details"] = {
                "trips_14d": gap.get("trips_14d", 0),
                "milestone_value": gap.get("milestone_value")
            }
            return analysis
        
        # Verificar si milestone está achieved según v_payment_calculation
        milestone_achieved = self.verify_milestone_achieved(
            gap["driver_id"],
            gap["milestone_value"],
            gap["lead_date"]
        )
        
        if not milestone_achieved:
            analysis["reason"] = "MILESTONE_NOT_ACHIEVED_IN_PAYMENT_CALC"
            analysis["details"] = {
                "trips_14d": gap.get("trips_14d", 0),
                "milestone_value": gap.get("milestone_value")
            }
            return analysis
        
        # Verificar si claim ya existe en tabla física
        person_key = gap.get("person_key")
        if person_key:
            claim_exists = self.verify_claim_exists(
                person_key,
                gap["lead_date"],
                gap["milestone_value"]
            )
            
            if claim_exists:
                analysis["reason"] = "CLAIM_ALREADY_EXISTS"
                analysis["details"] = {}
                return analysis
        
        # Todas las condiciones cumplidas: debe generarse
        analysis["should_generate"] = True
        analysis["reason"] = "SHOULD_GENERATE"
        analysis["details"] = {
            "driver_id": gap["driver_id"],
            "milestone_value": gap["milestone_value"],
            "lead_date": gap["lead_date"],
            "expected_amount": gap.get("expected_amount", 0)
        }
        
        return analysis
    
    def run_reconcile(self,
                     days_back: int = 21,
                     limit: int = 1000,
                     only_gaps: bool = False,
                     dry_run: bool = False,
                     only_milestone: Optional[int] = None,
                     week_start: Optional[str] = None) -> Dict[str, Any]:
        """Ejecuta el pipeline de reconciliación."""
        logger.info("=" * 80)
        logger.info("INICIANDO RECONCILE CABINET CLAIMS 14D")
        logger.info("=" * 80)
        
        if dry_run:
            logger.info("MODO DRY-RUN: No se ejecutarán acciones")
        
        # 1. Refrescar vistas materializadas (si existen)
        if not dry_run:
            logger.info("Refrescando vistas materializadas...")
            refresh_results = self.refresh_materialized_views()
            self.stats["refreshed_views"] = sum(1 for v in refresh_results.values() if v)
        
        # 2. Obtener gaps
        logger.info(f"Obteniendo gaps (últimos {days_back} días, límite {limit})...")
        gaps = self.get_gaps(days_back=days_back, limit=limit, 
                            only_milestone=only_milestone, week_start=week_start)
        logger.info(f"Encontrados {len(gaps)} gaps")
        self.stats["gaps_found"] = len(gaps)
        
        # 3. Analizar cada gap
        logger.info("Analizando gaps...")
        gaps_to_fix = []
        
        for gap in gaps:
            self.stats["processed"] += 1
            
            analysis = self.log_gap_analysis(gap)
            
            if analysis["should_generate"]:
                gaps_to_fix.append({
                    "gap": gap,
                    "analysis": analysis
                })
            elif analysis["reason"] == "CLAIM_ALREADY_EXISTS":
                self.stats["claims_already_exist"] += 1
            else:
                self.stats["invalid_conditions"] += 1
                logger.debug(f"Gap no debe generarse: {analysis['reason']} - {gap.get('driver_id')}, M{gap.get('milestone_value')}")
        
        logger.info(f"Gaps que deben generarse: {len(gaps_to_fix)}")
        
        # 4. Generar claims faltantes insertando en tabla física
        if gaps_to_fix and not dry_run:
            logger.info("=" * 80)
            logger.info("GENERANDO CLAIMS FALTANTES EN TABLA FÍSICA")
            logger.info("=" * 80)
            
            for gap_info in gaps_to_fix:
                gap = gap_info["gap"]
                try:
                    result = self.insert_or_update_claim(gap, dry_run=False)
                    action = result.get("action")
                    
                    if action == "inserted":
                        self.stats["claims_inserted"] += 1
                        logger.info(f"Claim insertado: person_key={gap.get('person_key')}, milestone={gap.get('milestone_value')}, claim_id={result.get('claim_id')}")
                    elif action == "updated":
                        self.stats["claims_updated"] += 1
                        logger.debug(f"Claim actualizado: claim_id={result.get('claim_id')}")
                    elif action == "skipped":
                        reason = result.get("reason", "unknown")
                        if "paid" in reason or "rejected" in reason:
                            self.stats["claims_skipped_paid"] += 1
                        else:
                            self.stats["claims_skipped_rejected"] += 1
                        logger.debug(f"Claim omitido: {reason}")
                    elif action == "error":
                        self.stats["errors"] += 1
                        logger.error(f"Error generando claim: {result.get('error')}")
                except Exception as e:
                    self.stats["errors"] += 1
                    logger.error(f"Error procesando gap: {e}", exc_info=True)
            
            logger.info(f"Claims insertados: {self.stats['claims_inserted']}")
            logger.info(f"Claims actualizados: {self.stats['claims_updated']}")
            logger.info(f"Claims omitidos (paid/rejected): {self.stats['claims_skipped_paid'] + self.stats['claims_skipped_rejected']}")
            logger.info(f"Errores: {self.stats['errors']}")
        
        # 5. Loggear métricas finales
        logger.info("=" * 80)
        logger.info("MÉTRICAS FINALES")
        logger.info("=" * 80)
        for key, value in self.stats.items():
            logger.info(f"  {key}: {value}")
        
        return {
            "stats": self.stats,
            "gaps_to_fix": gaps_to_fix if not dry_run else [],
            "dry_run": dry_run
        }


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description='Reconcile Cabinet Claims 14d Pipeline')
    parser.add_argument('--days-back', type=int, default=21, help='Días hacia atrás para procesar (default: 21)')
    parser.add_argument('--limit', type=int, default=1000, help='Límite de gaps a procesar (default: 1000)')
    parser.add_argument('--only-gaps', action='store_true', help='Solo procesar gaps (claim_status=CLAIM_NOT_GENERATED)')
    parser.add_argument('--dry-run', action='store_true', help='Modo dry-run (no ejecuta acciones)')
    parser.add_argument('--only-milestone', type=int, choices=[1, 5, 25], help='Solo procesar un milestone específico (1, 5, o 25)')
    parser.add_argument('--week-start', type=str, help='Filtrar por semana (YYYY-MM-DD, lunes de la semana)')
    parser.add_argument('--output-json', type=str, help='Ruta para guardar resultados en JSON')
    parser.add_argument('--output-csv', type=str, help='Ruta para guardar resultados en CSV')
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        pipeline = ReconcileCabinetClaims14d(db)
        
        result = pipeline.run_reconcile(
            days_back=args.days_back,
            limit=args.limit,
            only_gaps=args.only_gaps,
            dry_run=args.dry_run,
            only_milestone=args.only_milestone,
            week_start=args.week_start
        )
        
        logger.info("=" * 80)
        logger.info("RECONCILE COMPLETADO")
        logger.info("=" * 80)
        
        # Guardar resultados si se solicita
        if args.output_json:
            with open(args.output_json, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            logger.info(f"Resultados guardados en: {args.output_json}")
        
        if args.output_csv:
            import csv
            with open(args.output_csv, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['metric', 'value'])
                for key, value in result['stats'].items():
                    writer.writerow([key, value])
            logger.info(f"Resultados guardados en: {args.output_csv}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error en reconcile pipeline: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
