#!/usr/bin/env python3
"""
Script de validación end-to-end del sistema auditable Cabinet 14d.
Valida que todos los componentes funcionan correctamente.

Uso:
    python scripts/validate_system_end_to_end.py
    python scripts/validate_system_end_to_end.py --skip-ui
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


class SystemValidator:
    """Validador end-to-end del sistema."""
    
    def __init__(self, db_session):
        self.db = db_session
        self.results = {
            "vistas_sql": {},
            "endpoints": {},
            "jobs": {},
            "reglas_duras": {},
            "valid": True
        }
    
    def validate_vistas_sql(self) -> Dict[str, bool]:
        """Valida que todas las vistas SQL existen y son accesibles."""
        logger.info("=" * 80)
        logger.info("1. VALIDANDO VISTAS SQL")
        logger.info("=" * 80)
        
        vistas = [
            "ops.v_cabinet_leads_limbo",
            "ops.v_cabinet_claims_expected_14d",
            "ops.v_cabinet_claims_gap_14d"
        ]
        
        results = {}
        for vista in vistas:
            try:
                query = text(f"SELECT COUNT(*) FROM {vista} LIMIT 1")
                result = self.db.execute(query)
                count = result.scalar()
                
                # Verificar columnas críticas
                schema, name = vista.split('.')
                columns_query = text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = :schema 
                      AND table_name = :name
                """)
                cols_result = self.db.execute(columns_query, {"schema": schema, "name": name})
                columns = [row.column_name for row in cols_result]
                
                # Validaciones específicas por vista
                if vista == "ops.v_cabinet_leads_limbo":
                    required_cols = ['lead_id', 'lead_source_pk', 'limbo_stage', 'trips_14d', 'driver_id']
                    missing = [c for c in required_cols if c not in columns]
                    if missing:
                        logger.error(f"❌ {vista}: Faltan columnas: {missing}")
                        results[vista] = False
                    else:
                        logger.info(f"✅ {vista}: Existe y accesible ({len(columns)} columnas)")
                        results[vista] = True
                
                elif vista == "ops.v_cabinet_claims_gap_14d":
                    required_cols = ['lead_id', 'expected_amount', 'gap_reason', 'claim_status']
                    missing = [c for c in required_cols if c not in columns]
                    if missing:
                        logger.error(f"❌ {vista}: Faltan columnas: {missing}")
                        results[vista] = False
                    else:
                        # Verificar específicamente expected_amount
                        if 'expected_amount' not in columns:
                            logger.error(f"❌ {vista}: Columna 'expected_amount' no existe")
                            results[vista] = False
                        else:
                            logger.info(f"✅ {vista}: Existe y accesible, expected_amount presente")
                            results[vista] = True
                
                else:
                    logger.info(f"✅ {vista}: Existe y accesible")
                    results[vista] = True
                    
            except Exception as e:
                logger.error(f"❌ {vista}: Error - {e}")
                results[vista] = False
                self.results["valid"] = False
        
        self.results["vistas_sql"] = results
        return results
    
    def validate_reglas_duras(self) -> Dict[str, bool]:
        """Valida reglas duras del sistema."""
        logger.info("\n" + "=" * 80)
        logger.info("2. VALIDANDO REGLAS DURAS")
        logger.info("=" * 80)
        
        results = {}
        
        # Regla 1: trips_14d debe ser 0 cuando driver_id IS NULL
        logger.info("\n2.1 Regla: trips_14d debe ser 0 cuando driver_id IS NULL")
        try:
            query = text("""
                SELECT COUNT(*) 
                FROM ops.v_cabinet_leads_limbo
                WHERE driver_id IS NULL AND trips_14d > 0
            """)
            result = self.db.execute(query)
            violations = result.scalar() or 0
            
            if violations > 0:
                logger.error(f"❌ VIOLACIÓN: {violations} leads con driver_id NULL pero trips_14d > 0")
                results["trips_14d_zero_when_no_driver"] = False
                self.results["valid"] = False
            else:
                logger.info("✅ Regla cumplida")
                results["trips_14d_zero_when_no_driver"] = True
        except Exception as e:
            logger.error(f"❌ Error validando regla: {e}")
            results["trips_14d_zero_when_no_driver"] = False
            self.results["valid"] = False
        
        # Regla 2: TRIPS_NO_CLAIM solo con condiciones válidas
        logger.info("\n2.2 Regla: TRIPS_NO_CLAIM solo con driver_id NOT NULL y trips_14d > 0")
        try:
            query = text("""
                SELECT COUNT(*) 
                FROM ops.v_cabinet_leads_limbo
                WHERE limbo_stage = 'TRIPS_NO_CLAIM'
                  AND (driver_id IS NULL OR trips_14d = 0)
            """)
            result = self.db.execute(query)
            violations = result.scalar() or 0
            
            if violations > 0:
                logger.error(f"❌ VIOLACIÓN: {violations} leads en TRIPS_NO_CLAIM con condiciones inválidas")
                results["trips_no_claim_conditions"] = False
                self.results["valid"] = False
            else:
                logger.info("✅ Regla cumplida")
                results["trips_no_claim_conditions"] = True
        except Exception as e:
            logger.error(f"❌ Error validando regla: {e}")
            results["trips_no_claim_conditions"] = False
            self.results["valid"] = False
        
        # Regla 3: expected_amount siempre presente cuando claim_expected=true
        logger.info("\n2.3 Regla: expected_amount siempre presente cuando claim_expected=true")
        try:
            query = text("""
                SELECT COUNT(*) 
                FROM ops.v_cabinet_claims_gap_14d
                WHERE claim_expected = true 
                  AND (expected_amount IS NULL OR expected_amount = 0)
            """)
            result = self.db.execute(query)
            violations = result.scalar() or 0
            
            if violations > 0:
                logger.error(f"❌ VIOLACIÓN: {violations} gaps con claim_expected=true pero expected_amount NULL o 0")
                results["expected_amount_present"] = False
                self.results["valid"] = False
            else:
                logger.info("✅ Regla cumplida")
                results["expected_amount_present"] = True
        except Exception as e:
            logger.error(f"❌ Error validando regla: {e}")
            results["expected_amount_present"] = False
            self.results["valid"] = False
        
        self.results["reglas_duras"] = results
        return results
    
    def validate_endpoints(self, base_url: str = "http://localhost:8000") -> Dict[str, bool]:
        """Valida que los endpoints funcionan (requiere servidor corriendo)."""
        logger.info("\n" + "=" * 80)
        logger.info("3. VALIDANDO ENDPOINTS API")
        logger.info("=" * 80)
        
        results = {}
        
        try:
            import requests
            
            endpoints = [
                ("/api/v1/ops/payments/cabinet-financial-14d/limbo?limit=1", "Limbo"),
                ("/api/v1/ops/payments/cabinet-financial-14d/claims-gap?limit=1", "Claims Gap")
            ]
            
            for endpoint_path, name in endpoints:
                try:
                    url = f"{base_url}{endpoint_path}"
                    response = requests.get(url, timeout=10)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "data" in data or "meta" in data:
                            logger.info(f"✅ {name}: Endpoint funciona (200)")
                            results[name] = True
                        else:
                            logger.warning(f"⚠️ {name}: Endpoint responde pero estructura inesperada")
                            results[name] = False
                    elif response.status_code == 500:
                        logger.error(f"❌ {name}: Error 500 - {response.text[:200]}")
                        results[name] = False
                        self.results["valid"] = False
                    else:
                        logger.warning(f"⚠️ {name}: Status {response.status_code}")
                        results[name] = False
                        
                except requests.exceptions.ConnectionError:
                    logger.warning(f"⚠️ {name}: Servidor no disponible en {base_url}")
                    results[name] = None  # No es error, solo no disponible
                except Exception as e:
                    logger.error(f"❌ {name}: Error - {e}")
                    results[name] = False
                    self.results["valid"] = False
                    
        except ImportError:
            logger.warning("⚠️ requests no instalado, saltando validación de endpoints")
            results["skip"] = True
        
        self.results["endpoints"] = results
        return results
    
    def validate_jobs_importable(self) -> Dict[str, bool]:
        """Valida que los jobs son importables y tienen estructura correcta."""
        logger.info("\n" + "=" * 80)
        logger.info("4. VALIDANDO JOBS")
        logger.info("=" * 80)
        
        results = {}
        
        jobs = [
            "jobs.reconcile_cabinet_claims_14d",
            "jobs.reconcile_cabinet_leads_pipeline"
        ]
        
        for job_module in jobs:
            try:
                module = __import__(job_module, fromlist=[''])
                
                # Verificar que tiene clase principal
                if hasattr(module, 'ReconcileCabinetClaims14d') or hasattr(module, 'ReconcileCabinetLeadsPipeline'):
                    logger.info(f"✅ {job_module}: Importable y tiene clase principal")
                    results[job_module] = True
                else:
                    logger.warning(f"⚠️ {job_module}: Importable pero estructura inesperada")
                    results[job_module] = False
                    
            except Exception as e:
                logger.error(f"❌ {job_module}: Error importando - {e}")
                results[job_module] = False
                self.results["valid"] = False
        
        self.results["jobs"] = results
        return results
    
    def validate_scripts(self) -> Dict[str, bool]:
        """Valida que los scripts de validación existen y son ejecutables."""
        logger.info("\n" + "=" * 80)
        logger.info("5. VALIDANDO SCRIPTS DE VALIDACIÓN")
        logger.info("=" * 80)
        
        results = {}
        
        scripts = [
            "scripts/validate_limbo.py",
            "scripts/validate_claims_gap_before_after.py",
            "scripts/check_limbo_alerts.py"
        ]
        
        for script_path in scripts:
            full_path = project_root / "backend" / script_path
            if full_path.exists():
                # Verificar que es ejecutable (tiene shebang)
                content = full_path.read_text(encoding='utf-8')
                if content.startswith('#!/usr/bin/env python3'):
                    logger.info(f"✅ {script_path}: Existe y tiene shebang")
                    results[script_path] = True
                else:
                    logger.warning(f"⚠️ {script_path}: Existe pero sin shebang")
                    results[script_path] = False
            else:
                logger.error(f"❌ {script_path}: No existe")
                results[script_path] = False
                self.results["valid"] = False
        
        return results
    
    def run_full_validation(self, skip_ui: bool = False, base_url: str = "http://localhost:8000") -> Dict[str, Any]:
        """Ejecuta validación completa del sistema."""
        logger.info("=" * 80)
        logger.info("VALIDACIÓN END-TO-END - SISTEMA AUDITABLE CABINET 14D")
        logger.info("=" * 80)
        
        # 1. Vistas SQL
        self.validate_vistas_sql()
        
        # 2. Reglas duras
        self.validate_reglas_duras()
        
        # 3. Endpoints (opcional)
        if not skip_ui:
            self.validate_endpoints(base_url)
        else:
            logger.info("\n⚠️ Saltando validación de endpoints (--skip-ui)")
        
        # 4. Jobs
        self.validate_jobs_importable()
        
        # 5. Scripts
        self.validate_scripts()
        
        # Resumen final
        logger.info("\n" + "=" * 80)
        logger.info("RESUMEN FINAL")
        logger.info("=" * 80)
        
        all_valid = self.results["valid"]
        logger.info(f"Estado general: {'✅ VÁLIDO' if all_valid else '❌ ERRORES ENCONTRADOS'}")
        
        return self.results


def main():
    """Función principal."""
    parser = argparse.ArgumentParser(description='Validación end-to-end del sistema')
    parser.add_argument('--skip-ui', action='store_true', help='Saltar validación de endpoints UI')
    parser.add_argument('--base-url', type=str, default='http://localhost:8000', 
                       help='URL base del servidor (default: http://localhost:8000)')
    parser.add_argument('--output-json', type=str, help='Ruta para guardar resultados en JSON')
    
    args = parser.parse_args()
    
    db = SessionLocal()
    
    try:
        validator = SystemValidator(db)
        result = validator.run_full_validation(
            skip_ui=args.skip_ui,
            base_url=args.base_url
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
