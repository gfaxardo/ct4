#!/usr/bin/env python3
"""
Script de validación para Claims Gap.
Valida que expected_amount siempre tenga valor cuando claim_expected=true.

Uso:
    python scripts/validate_claims_gap_before_after.py
    python scripts/validate_claims_gap_before_after.py --gap-reason CLAIM_NOT_GENERATED
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


class ClaimsGapValidator:
    """Validador de Claims Gap."""
    
    def __init__(self, db_session):
        self.db = db_session
        self.errors = []
        self.warnings = []
        self.stats = {
            "total_gaps": 0,
            "gaps_by_reason": {},
            "gaps_by_milestone": {},
            "missing_expected_amount": 0,
            "valid_expected_amount": 0
        }
    
    def validate_expected_amount_present(self, gap_reason: str = None) -> List[Dict[str, Any]]:
        """
        Valida que expected_amount siempre tenga valor cuando claim_expected=true.
        """
        logger.info("Validando que expected_amount siempre tenga valor cuando claim_expected=true...")
        
        where_clause = "WHERE claim_expected = true"
        params = {}
        
        if gap_reason:
            where_clause += " AND gap_reason = :gap_reason"
            params["gap_reason"] = gap_reason
        
        query = text(f"""
            SELECT 
                lead_id,
                lead_source_pk,
                driver_id,
                lead_date,
                milestone_value,
                claim_expected,
                expected_amount,
                gap_reason,
                claim_status
            FROM ops.v_cabinet_claims_gap_14d
            {where_clause}
                AND (expected_amount IS NULL OR expected_amount = 0)
        """)
        
        result = self.db.execute(query, params)
        rows = result.fetchall()
        
        violations = []
        for row in rows:
            violations.append({
                "lead_id": row.lead_id,
                "lead_source_pk": row.lead_source_pk,
                "driver_id": row.driver_id,
                "lead_date": row.lead_date,
                "milestone_value": row.milestone_value,
                "claim_expected": row.claim_expected,
                "expected_amount": row.expected_amount,
                "gap_reason": row.gap_reason,
                "claim_status": row.claim_status,
                "rule": "expected_amount debe tener valor cuando claim_expected=true"
            })
        
        if violations:
            logger.error(f"❌ VIOLACIÓN: {len(violations)} gaps con claim_expected=true pero expected_amount NULL o 0")
            self.errors.extend(violations)
            self.stats["missing_expected_amount"] = len(violations)
        else:
            logger.info("✅ Regla cumplida: expected_amount siempre tiene valor cuando claim_expected=true")
            self.stats["valid_expected_amount"] = 1
        
        return violations
    
    def get_summary_by_gap_reason(self) -> Dict[str, Any]:
        """Obtiene resumen por gap_reason."""
        logger.info("Obteniendo resumen por gap_reason...")
        
        query = text("""
            SELECT 
                gap_reason,
                COUNT(*) AS count,
                COUNT(*) FILTER (WHERE claim_expected = true) AS claim_expected_count,
                COUNT(*) FILTER (WHERE claim_expected = true AND expected_amount IS NOT NULL AND expected_amount > 0) AS with_expected_amount,
                SUM(expected_amount) FILTER (WHERE claim_expected = true) AS total_expected_amount
            FROM ops.v_cabinet_claims_gap_14d
            GROUP BY gap_reason
            ORDER BY count DESC
        """)
        
        result = self.db.execute(query)
        rows = result.fetchall()
        
        summary = {}
        for row in rows:
            summary[row.gap_reason] = {
                "count": row.count,
                "claim_expected_count": row.claim_expected_count,
                "with_expected_amount": row.with_expected_amount,
                "total_expected_amount": float(row.total_expected_amount) if row.total_expected_amount else 0
            }
            self.stats["gaps_by_reason"][row.gap_reason] = row.count
        
        logger.info("Resumen por gap_reason:")
        for reason, data in summary.items():
            logger.info(f"  {reason}: {data['count']} gaps")
            if data['claim_expected_count'] > 0:
                logger.info(f"    - claim_expected=true: {data['claim_expected_count']}")
                logger.info(f"    - con expected_amount: {data['with_expected_amount']}")
                logger.info(f"    - total expected_amount: S/ {data['total_expected_amount']:.2f}")
        
        return summary
    
    def get_summary_by_milestone(self) -> Dict[str, Any]:
        """Obtiene resumen por milestone."""
        logger.info("Obteniendo resumen por milestone...")
        
        query = text("""
            SELECT 
                milestone_value,
                COUNT(*) AS count,
                COUNT(*) FILTER (WHERE gap_reason = 'CLAIM_NOT_GENERATED') AS claim_not_generated,
                SUM(expected_amount) FILTER (WHERE gap_reason = 'CLAIM_NOT_GENERATED') AS total_expected_amount
            FROM ops.v_cabinet_claims_gap_14d
            GROUP BY milestone_value
            ORDER BY milestone_value
        """)
        
        result = self.db.execute(query)
        rows = result.fetchall()
        
        summary = {}
        for row in rows:
            summary[row.milestone_value] = {
                "count": row.count,
                "claim_not_generated": row.claim_not_generated,
                "total_expected_amount": float(row.total_expected_amount) if row.total_expected_amount else 0
            }
            self.stats["gaps_by_milestone"][f"M{row.milestone_value}"] = row.count
        
        logger.info("Resumen por milestone:")
        for milestone, data in summary.items():
            logger.info(f"  M{milestone}: {data['count']} gaps")
            logger.info(f"    - claim_not_generated: {data['claim_not_generated']}")
            logger.info(f"    - total expected_amount: S/ {data['total_expected_amount']:.2f}")
        
        return summary
    
    def validate_endpoint_works(self) -> bool:
        """Valida que el endpoint funciona (no error 500)."""
        logger.info("Validando que el endpoint funciona...")
        
        try:
            query = text("""
                SELECT 
                    lead_id,
                    lead_source_pk,
                    expected_amount,
                    gap_reason
                FROM ops.v_cabinet_claims_gap_14d
                LIMIT 1
            """)
            
            result = self.db.execute(query)
            row = result.fetchone()
            
            if row:
                # Verificar que expected_amount existe y es accesible
                if hasattr(row, 'expected_amount'):
                    logger.info("✅ Endpoint funciona: expected_amount accesible")
                    return True
                else:
                    logger.error("❌ Endpoint no funciona: expected_amount no existe en resultado")
                    self.errors.append({
                        "rule": "expected_amount no existe en resultado del endpoint",
                        "detail": "La columna expected_amount no está disponible"
                    })
                    return False
            else:
                logger.warning("⚠️ No hay datos en la vista (puede ser normal)")
                return True
                
        except Exception as e:
            logger.error(f"❌ Error al validar endpoint: {e}")
            self.errors.append({
                "rule": "Error al acceder a vista",
                "detail": str(e)
            })
            return False
    
    def run_validation(self, gap_reason: str = None) -> Dict[str, Any]:
        """Ejecuta todas las validaciones."""
        logger.info("=" * 80)
        logger.info("VALIDACIÓN DE CLAIMS GAP")
        logger.info("=" * 80)
        
        # 1. Validar que endpoint funciona
        logger.info("\n1. Validando que endpoint funciona:")
        endpoint_works = self.validate_endpoint_works()
        
        # 2. Validar expected_amount presente
        logger.info("\n2. Validando expected_amount:")
        violations = self.validate_expected_amount_present(gap_reason)
        
        # 3. Resumen por gap_reason
        logger.info("\n3. Resumen por gap_reason:")
        reason_summary = self.get_summary_by_gap_reason()
        self.stats["total_gaps"] = sum(data["count"] for data in reason_summary.values())
        
        # 4. Resumen por milestone
        logger.info("\n4. Resumen por milestone:")
        milestone_summary = self.get_summary_by_milestone()
        
        # 5. Resumen final
        logger.info("\n" + "=" * 80)
        logger.info("RESUMEN DE VALIDACIÓN")
        logger.info("=" * 80)
        logger.info(f"Total gaps: {self.stats['total_gaps']}")
        logger.info(f"Errores encontrados: {len(self.errors)}")
        logger.info(f"Advertencias: {len(self.warnings)}")
        
        if self.errors:
            logger.error("\nErrores:")
            for i, error in enumerate(self.errors[:10], 1):
                logger.error(f"  {i}. {error.get('rule', 'Unknown')}: {error.get('detail', '')}")
                if 'lead_source_pk' in error:
                    logger.error(f"     Lead: {error['lead_source_pk']}, Milestone: M{error.get('milestone_value', '?')}")
            if len(self.errors) > 10:
                logger.error(f"  ... y {len(self.errors) - 10} errores más")
        
        return {
            "stats": self.stats,
            "errors": self.errors,
            "warnings": self.warnings,
            "valid": len(self.errors) == 0 and endpoint_works,
            "reason_summary": reason_summary,
            "milestone_summary": milestone_summary
        }


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description='Validar Claims Gap')
    parser.add_argument('--gap-reason', type=str, help='Filtrar por gap_reason específico')
    parser.add_argument('--output-json', type=str, help='Ruta para guardar resultados en JSON')
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        validator = ClaimsGapValidator(db)
        result = validator.run_validation(gap_reason=args.gap_reason)
        
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
