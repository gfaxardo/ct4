#!/usr/bin/env python3
"""
Script de validación para Leads en Limbo.
Valida reglas duras y consistencia de datos.

Uso:
    python scripts/validate_limbo.py
    python scripts/validate_limbo.py --stage NO_IDENTITY
    python scripts/validate_limbo.py --check-rules-only
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import date, datetime
from typing import Dict, Any, List
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


class LimboValidator:
    """Validador de reglas duras para Leads en Limbo."""
    
    def __init__(self, db_session):
        self.db = db_session
        self.errors = []
        self.warnings = []
        self.stats = {
            "total_leads": 0,
            "no_identity": 0,
            "no_driver": 0,
            "no_trips_14d": 0,
            "trips_no_claim": 0,
            "ok": 0,
            "violations": 0
        }
    
    def validate_rule_trips_14d_zero_when_no_driver(self) -> List[Dict[str, Any]]:
        """
        REGLA DURA: trips_14d debe ser 0 cuando driver_id IS NULL
        """
        logger.info("Validando regla: trips_14d debe ser 0 cuando driver_id IS NULL...")
        
        query = text("""
            SELECT 
                lead_id,
                lead_source_pk,
                lead_date,
                driver_id,
                trips_14d,
                limbo_stage
            FROM ops.v_cabinet_leads_limbo
            WHERE driver_id IS NULL 
                AND trips_14d > 0
        """)
        
        result = self.db.execute(query)
        rows = result.fetchall()
        
        violations = []
        for row in rows:
            violations.append({
                "lead_id": row.lead_id,
                "lead_source_pk": row.lead_source_pk,
                "lead_date": row.lead_date,
                "driver_id": row.driver_id,
                "trips_14d": row.trips_14d,
                "limbo_stage": row.limbo_stage,
                "rule": "trips_14d debe ser 0 cuando driver_id IS NULL"
            })
        
        if violations:
            logger.error(f"❌ VIOLACIÓN: {len(violations)} leads con driver_id NULL pero trips_14d > 0")
            self.errors.extend(violations)
            self.stats["violations"] += len(violations)
        else:
            logger.info("✅ Regla cumplida: trips_14d = 0 cuando driver_id IS NULL")
        
        return violations
    
    def validate_rule_trips_no_claim_conditions(self) -> List[Dict[str, Any]]:
        """
        REGLA DURA: TRIPS_NO_CLAIM solo puede ocurrir cuando:
        - driver_id IS NOT NULL
        - trips_14d > 0
        - claim_exists = false (o claim_missing)
        """
        logger.info("Validando regla: TRIPS_NO_CLAIM solo con driver_id NOT NULL y trips_14d > 0...")
        
        query = text("""
            SELECT 
                lead_id,
                lead_source_pk,
                lead_date,
                driver_id,
                trips_14d,
                limbo_stage,
                has_claim_m1,
                has_claim_m5,
                has_claim_m25
            FROM ops.v_cabinet_leads_limbo
            WHERE limbo_stage = 'TRIPS_NO_CLAIM'
                AND (
                    driver_id IS NULL 
                    OR trips_14d = 0
                    OR (has_claim_m1 = true AND has_claim_m5 = true AND has_claim_m25 = true)
                )
        """)
        
        result = self.db.execute(query)
        rows = result.fetchall()
        
        violations = []
        for row in rows:
            reason = []
            if row.driver_id is None:
                reason.append("driver_id IS NULL")
            if row.trips_14d == 0:
                reason.append("trips_14d = 0")
            if row.has_claim_m1 and row.has_claim_m5 and row.has_claim_m25:
                reason.append("todos los claims existen")
            
            violations.append({
                "lead_id": row.lead_id,
                "lead_source_pk": row.lead_source_pk,
                "lead_date": row.lead_date,
                "driver_id": row.driver_id,
                "trips_14d": row.trips_14d,
                "limbo_stage": row.limbo_stage,
                "reason": ", ".join(reason),
                "rule": "TRIPS_NO_CLAIM requiere driver_id NOT NULL, trips_14d > 0, y claim_missing"
            })
        
        if violations:
            logger.error(f"❌ VIOLACIÓN: {len(violations)} leads en TRIPS_NO_CLAIM con condiciones inválidas")
            self.errors.extend(violations)
            self.stats["violations"] += len(violations)
        else:
            logger.info("✅ Regla cumplida: TRIPS_NO_CLAIM solo con condiciones válidas")
        
        return violations
    
    def validate_stage_consistency(self) -> Dict[str, Any]:
        """
        Valida consistencia de limbo_stage con datos subyacentes.
        """
        logger.info("Validando consistencia de limbo_stage...")
        
        query = text("""
            SELECT 
                limbo_stage,
                COUNT(*) as count,
                COUNT(*) FILTER (WHERE person_key IS NULL) as no_person_key,
                COUNT(*) FILTER (WHERE driver_id IS NULL) as no_driver_id,
                COUNT(*) FILTER (WHERE trips_14d = 0) as no_trips,
                COUNT(*) FILTER (WHERE trips_14d > 0) as has_trips,
                COUNT(*) FILTER (WHERE has_claim_m1 = true OR has_claim_m5 = true OR has_claim_m25 = true) as has_claims
            FROM ops.v_cabinet_leads_limbo
            GROUP BY limbo_stage
            ORDER BY limbo_stage
        """)
        
        result = self.db.execute(query)
        rows = result.fetchall()
        
        summary = {}
        for row in rows:
            summary[row.limbo_stage] = {
                "count": row.count,
                "no_person_key": row.no_person_key,
                "no_driver_id": row.no_driver_id,
                "no_trips": row.no_trips,
                "has_trips": row.has_trips,
                "has_claims": row.has_claims
            }
            
            # Validar consistencia por etapa
            if row.limbo_stage == 'NO_IDENTITY' and row.no_person_key != row.count:
                self.warnings.append({
                    "stage": row.limbo_stage,
                    "issue": f"NO_IDENTITY debería tener person_key NULL, pero {row.count - row.no_person_key} tienen person_key"
                })
            
            if row.limbo_stage == 'NO_DRIVER' and row.no_driver_id != row.count:
                self.warnings.append({
                    "stage": row.limbo_stage,
                    "issue": f"NO_DRIVER debería tener driver_id NULL, pero {row.count - row.no_driver_id} tienen driver_id"
                })
            
            if row.limbo_stage == 'NO_TRIPS_14D' and row.no_trips != row.count:
                self.warnings.append({
                    "stage": row.limbo_stage,
                    "issue": f"NO_TRIPS_14D debería tener trips_14d = 0, pero {row.count - row.no_trips} tienen trips_14d > 0"
                })
        
        logger.info("Resumen por etapa:")
        for stage, data in summary.items():
            logger.info(f"  {stage}: {data['count']} leads")
            self.stats[stage.lower().replace('_', '_')] = data['count']
        
        return summary
    
    def get_summary_stats(self, limbo_stage: str = None) -> Dict[str, Any]:
        """Obtiene estadísticas generales de limbo."""
        where_clause = f"WHERE limbo_stage = '{limbo_stage}'" if limbo_stage else ""
        
        query = text(f"""
            SELECT 
                COUNT(*) AS total_leads,
                COUNT(*) FILTER (WHERE limbo_stage = 'NO_IDENTITY') AS limbo_no_identity,
                COUNT(*) FILTER (WHERE limbo_stage = 'NO_DRIVER') AS limbo_no_driver,
                COUNT(*) FILTER (WHERE limbo_stage = 'NO_TRIPS_14D') AS limbo_no_trips_14d,
                COUNT(*) FILTER (WHERE limbo_stage = 'TRIPS_NO_CLAIM') AS limbo_trips_no_claim,
                COUNT(*) FILTER (WHERE limbo_stage = 'OK') AS limbo_ok,
                COUNT(*) FILTER (WHERE person_key IS NOT NULL) AS with_identity,
                ROUND(100.0 * COUNT(*) FILTER (WHERE person_key IS NOT NULL) / COUNT(*), 2) AS pct_with_identity
            FROM ops.v_cabinet_leads_limbo
            {where_clause}
        """)
        
        result = self.db.execute(query)
        row = result.fetchone()
        
        return {
            "total_leads": row.total_leads or 0,
            "limbo_no_identity": row.limbo_no_identity or 0,
            "limbo_no_driver": row.limbo_no_driver or 0,
            "limbo_no_trips_14d": row.limbo_no_trips_14d or 0,
            "limbo_trips_no_claim": row.limbo_trips_no_claim or 0,
            "limbo_ok": row.limbo_ok or 0,
            "with_identity": row.with_identity or 0,
            "pct_with_identity": row.pct_with_identity or 0
        }
    
    def run_validation(self, limbo_stage: str = None, check_rules_only: bool = False) -> Dict[str, Any]:
        """Ejecuta todas las validaciones."""
        logger.info("=" * 80)
        logger.info("VALIDACIÓN DE LEADS EN LIMBO")
        logger.info("=" * 80)
        
        # 1. Estadísticas generales
        if not check_rules_only:
            logger.info("\n1. Estadísticas generales:")
            stats = self.get_summary_stats(limbo_stage)
            self.stats.update(stats)
            for key, value in stats.items():
                logger.info(f"   {key}: {value}")
        
        # 2. Validar reglas duras
        logger.info("\n2. Validando reglas duras:")
        violations_rule1 = self.validate_rule_trips_14d_zero_when_no_driver()
        violations_rule2 = self.validate_rule_trips_no_claim_conditions()
        
        # 3. Validar consistencia de etapas
        if not check_rules_only:
            logger.info("\n3. Validando consistencia de etapas:")
            stage_summary = self.validate_stage_consistency()
        
        # 4. Resumen final
        logger.info("\n" + "=" * 80)
        logger.info("RESUMEN DE VALIDACIÓN")
        logger.info("=" * 80)
        logger.info(f"Errores encontrados: {len(self.errors)}")
        logger.info(f"Advertencias: {len(self.warnings)}")
        
        if self.errors:
            logger.error("\nErrores:")
            for i, error in enumerate(self.errors[:10], 1):  # Mostrar primeros 10
                logger.error(f"  {i}. Lead {error['lead_source_pk']}: {error['rule']}")
            if len(self.errors) > 10:
                logger.error(f"  ... y {len(self.errors) - 10} errores más")
        
        if self.warnings:
            logger.warning("\nAdvertencias:")
            for i, warning in enumerate(self.warnings[:10], 1):
                logger.warning(f"  {i}. {warning['stage']}: {warning['issue']}")
        
        return {
            "stats": self.stats,
            "errors": self.errors,
            "warnings": self.warnings,
            "valid": len(self.errors) == 0
        }


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description='Validar Leads en Limbo')
    parser.add_argument('--stage', type=str, help='Filtrar por limbo_stage específico')
    parser.add_argument('--check-rules-only', action='store_true', help='Solo validar reglas duras, no estadísticas')
    parser.add_argument('--output-json', type=str, help='Ruta para guardar resultados en JSON')
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        validator = LimboValidator(db)
        result = validator.run_validation(
            limbo_stage=args.stage,
            check_rules_only=args.check_rules_only
        )
        
        if args.output_json:
            import json
            with open(args.output_json, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            logger.info(f"\nResultados guardados en: {args.output_json}")
        
        # Exit code: 0 si válido, 1 si hay errores
        exit_code = 0 if result["valid"] else 1
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"Error en validación: {e}", exc_info=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
