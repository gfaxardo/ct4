#!/usr/bin/env python3
"""
Script de alertas para Leads en Limbo.
Verifica umbrales y genera alertas si se exceden.

Uso:
    python scripts/check_limbo_alerts.py
    python scripts/check_limbo_alerts.py --threshold-no-identity 100
    python scripts/check_limbo_alerts.py --threshold-pct-identity 80
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


class LimboAlerts:
    """Sistema de alertas para Leads en Limbo."""
    
    def __init__(self, db_session):
        self.db = db_session
        self.alerts = []
        self.stats = {}
    
    def check_limbo_no_identity_threshold(self, threshold: int = 100) -> Dict[str, Any]:
        """
        Alerta si limbo_no_identity total > umbral
        """
        logger.info(f"Verificando umbral de NO_IDENTITY (threshold={threshold})...")
        
        query = text("""
            SELECT 
                COUNT(*) FILTER (WHERE limbo_stage = 'NO_IDENTITY') AS limbo_no_identity,
                COUNT(*) AS total_leads
            FROM ops.v_cabinet_leads_limbo
        """)
        
        result = self.db.execute(query)
        row = result.fetchone()
        
        limbo_no_identity = row.limbo_no_identity or 0
        total_leads = row.total_leads or 0
        
        alert = {
            "type": "LIMBO_NO_IDENTITY_THRESHOLD",
            "threshold": threshold,
            "current": limbo_no_identity,
            "total_leads": total_leads,
            "triggered": limbo_no_identity > threshold
        }
        
        if alert["triggered"]:
            logger.warning(f"⚠️ ALERTA: limbo_no_identity ({limbo_no_identity}) > umbral ({threshold})")
            self.alerts.append(alert)
        else:
            logger.info(f"✅ OK: limbo_no_identity ({limbo_no_identity}) <= umbral ({threshold})")
        
        return alert
    
    def check_pct_with_identity_threshold(self, threshold: float = 80.0) -> Dict[str, Any]:
        """
        Alerta si pct_with_identity < umbral
        """
        logger.info(f"Verificando umbral de pct_with_identity (threshold={threshold}%)...")
        
        query = text("""
            SELECT 
                COUNT(*) AS total_leads,
                COUNT(*) FILTER (WHERE person_key IS NOT NULL) AS with_identity,
                ROUND(100.0 * COUNT(*) FILTER (WHERE person_key IS NOT NULL) / COUNT(*), 2) AS pct_with_identity
            FROM ops.v_cabinet_leads_limbo
        """)
        
        result = self.db.execute(query)
        row = result.fetchone()
        
        total_leads = row.total_leads or 0
        with_identity = row.with_identity or 0
        pct_with_identity = float(row.pct_with_identity) if row.pct_with_identity else 0.0
        
        alert = {
            "type": "PCT_WITH_IDENTITY_THRESHOLD",
            "threshold": threshold,
            "current": pct_with_identity,
            "total_leads": total_leads,
            "with_identity": with_identity,
            "triggered": pct_with_identity < threshold
        }
        
        if alert["triggered"]:
            logger.warning(f"⚠️ ALERTA: pct_with_identity ({pct_with_identity:.2f}%) < umbral ({threshold}%)")
            self.alerts.append(alert)
        else:
            logger.info(f"✅ OK: pct_with_identity ({pct_with_identity:.2f}%) >= umbral ({threshold}%)")
        
        return alert
    
    def check_trips_no_claim_persistent(self, days: int = 3) -> Dict[str, Any]:
        """
        Alerta si TRIPS_NO_CLAIM > 0 por N días consecutivos
        (indica que claims generator está fallando)
        """
        logger.info(f"Verificando TRIPS_NO_CLAIM persistente (días={days})...")
        
        # Obtener conteo actual de TRIPS_NO_CLAIM
        query = text("""
            SELECT 
                COUNT(*) FILTER (WHERE limbo_stage = 'TRIPS_NO_CLAIM') AS trips_no_claim,
                COUNT(*) AS total_leads
            FROM ops.v_cabinet_leads_limbo
        """)
        
        result = self.db.execute(query)
        row = result.fetchone()
        
        trips_no_claim = row.trips_no_claim or 0
        total_leads = row.total_leads or 0
        
        # NOTA: Para verificar persistencia por días, necesitaríamos una tabla de historial
        # Por ahora, solo verificamos si hay TRIPS_NO_CLAIM actualmente
        alert = {
            "type": "TRIPS_NO_CLAIM_PERSISTENT",
            "days_threshold": days,
            "current": trips_no_claim,
            "total_leads": total_leads,
            "triggered": trips_no_claim > 0,
            "note": "Verificar persistencia requiere tabla de historial (no implementado aún)"
        }
        
        if alert["triggered"]:
            logger.warning(f"⚠️ ALERTA: TRIPS_NO_CLAIM ({trips_no_claim}) > 0 (indica claims generator puede estar fallando)")
            self.alerts.append(alert)
        else:
            logger.info(f"✅ OK: TRIPS_NO_CLAIM ({trips_no_claim}) = 0")
        
        return alert
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas generales."""
        query = text("""
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
        """)
        
        result = self.db.execute(query)
        row = result.fetchone()
        
        stats = {
            "total_leads": row.total_leads or 0,
            "limbo_no_identity": row.limbo_no_identity or 0,
            "limbo_no_driver": row.limbo_no_driver or 0,
            "limbo_no_trips_14d": row.limbo_no_trips_14d or 0,
            "limbo_trips_no_claim": row.limbo_trips_no_claim or 0,
            "limbo_ok": row.limbo_ok or 0,
            "with_identity": row.with_identity or 0,
            "pct_with_identity": float(row.pct_with_identity) if row.pct_with_identity else 0.0
        }
        
        self.stats = stats
        return stats
    
    def run_checks(self, 
                   threshold_no_identity: int = 100,
                   threshold_pct_identity: float = 80.0,
                   days_trips_no_claim: int = 3) -> Dict[str, Any]:
        """Ejecuta todas las verificaciones de alertas."""
        logger.info("=" * 80)
        logger.info("VERIFICACIÓN DE ALERTAS - LEADS EN LIMBO")
        logger.info("=" * 80)
        
        # 1. Estadísticas generales
        logger.info("\n1. Estadísticas generales:")
        stats = self.get_summary_stats()
        for key, value in stats.items():
            logger.info(f"   {key}: {value}")
        
        # 2. Verificar umbrales
        logger.info("\n2. Verificando umbrales:")
        alert1 = self.check_limbo_no_identity_threshold(threshold_no_identity)
        alert2 = self.check_pct_with_identity_threshold(threshold_pct_identity)
        alert3 = self.check_trips_no_claim_persistent(days_trips_no_claim)
        
        # 3. Resumen final
        logger.info("\n" + "=" * 80)
        logger.info("RESUMEN DE ALERTAS")
        logger.info("=" * 80)
        logger.info(f"Total alertas: {len(self.alerts)}")
        
        if self.alerts:
            logger.warning("\nAlertas activas:")
            for i, alert in enumerate(self.alerts, 1):
                logger.warning(f"  {i}. {alert['type']}: {alert.get('current', 'N/A')}")
        else:
            logger.info("✅ No hay alertas activas")
        
        return {
            "stats": stats,
            "alerts": self.alerts,
            "has_alerts": len(self.alerts) > 0
        }


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description='Verificar alertas de Leads en Limbo')
    parser.add_argument('--threshold-no-identity', type=int, default=100, 
                       help='Umbral para limbo_no_identity (default: 100)')
    parser.add_argument('--threshold-pct-identity', type=float, default=80.0,
                       help='Umbral para pct_with_identity (default: 80.0)')
    parser.add_argument('--days-trips-no-claim', type=int, default=3,
                       help='Días para considerar TRIPS_NO_CLAIM persistente (default: 3)')
    parser.add_argument('--output-json', type=str, help='Ruta para guardar resultados en JSON')
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        alerts = LimboAlerts(db)
        result = alerts.run_checks(
            threshold_no_identity=args.threshold_no_identity,
            threshold_pct_identity=args.threshold_pct_identity,
            days_trips_no_claim=args.days_trips_no_claim
        )
        
        if args.output_json:
            import json
            with open(args.output_json, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            logger.info(f"\nResultados guardados en: {args.output_json}")
        
        # Exit code: 0 si no hay alertas, 1 si hay alertas
        exit_code = 0 if not result["has_alerts"] else 1
        sys.exit(exit_code)
        
    except Exception as e:
        logger.error(f"Error verificando alertas: {e}", exc_info=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
