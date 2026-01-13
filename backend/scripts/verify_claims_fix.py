#!/usr/bin/env python3
"""
Script para verificar que el fix de claims funcionó correctamente
"""
import sys
from pathlib import Path

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def execute_query(engine, query: str, description: str):
    """Ejecuta una query y muestra los resultados"""
    logger.info(f"\n{'='*60}")
    logger.info(f"{description}")
    logger.info(f"{'='*60}")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            rows = result.fetchall()
            
            if rows:
                # Mostrar headers
                if result.keys():
                    headers = list(result.keys())
                    logger.info(" | ".join(str(h) for h in headers))
                    logger.info("-" * 60)
                    
                    # Mostrar filas (limitado a 20)
                    for i, row in enumerate(rows[:20]):
                        logger.info(" | ".join(str(v) if v is not None else "NULL" for v in row))
                    
                    if len(rows) > 20:
                        logger.info(f"... y {len(rows) - 20} filas más")
                else:
                    for row in rows[:20]:
                        logger.info(str(row))
            else:
                logger.info("(Sin resultados)")
            
            return rows
    except Exception as e:
        logger.error(f"ERROR: {str(e)}")
        return None

def main():
    """Función principal"""
    logger.info("\n" + "="*60)
    logger.info("VERIFICACIÓN DEL FIX DE CLAIMS CABINET 14D")
    logger.info("="*60 + "\n")
    
    # Crear engine
    try:
        engine = create_engine(settings.database_url)
        logger.info("OK: Conexión a base de datos establecida\n")
    except Exception as e:
        logger.error(f"ERROR: No se pudo conectar a la base de datos: {str(e)}")
        return 1
    
    # 1. Resumen general de missing claims
    query1 = """
        SELECT 
            COUNT(*) AS total_drivers_elegibles,
            COUNT(*) FILTER (WHERE should_have_claim_m1 = true) AS total_should_have_m1,
            COUNT(*) FILTER (WHERE has_claim_m1 = true) AS total_has_m1,
            COUNT(*) FILTER (WHERE should_have_claim_m1 = true AND has_claim_m1 = false) AS missing_m1,
            COUNT(*) FILTER (WHERE should_have_claim_m5 = true) AS total_should_have_m5,
            COUNT(*) FILTER (WHERE has_claim_m5 = true) AS total_has_m5,
            COUNT(*) FILTER (WHERE should_have_claim_m5 = true AND has_claim_m5 = false) AS missing_m5,
            COUNT(*) FILTER (WHERE should_have_claim_m25 = true) AS total_should_have_m25,
            COUNT(*) FILTER (WHERE has_claim_m25 = true) AS total_has_m25,
            COUNT(*) FILTER (WHERE should_have_claim_m25 = true AND has_claim_m25 = false) AS missing_m25
        FROM ops.v_cabinet_claims_audit_14d;
    """
    execute_query(engine, query1, "1. RESUMEN GENERAL: Missing Claims")
    
    # 2. Top root causes
    query2 = """
        SELECT 
            root_cause,
            COUNT(*) AS count,
            COUNT(*) FILTER (WHERE missing_claim_bucket = 'M1_MISSING') AS m1_missing,
            COUNT(*) FILTER (WHERE missing_claim_bucket = 'M5_MISSING') AS m5_missing,
            COUNT(*) FILTER (WHERE missing_claim_bucket = 'M25_MISSING') AS m25_missing,
            COUNT(*) FILTER (WHERE missing_claim_bucket = 'MULTIPLE_MISSING') AS multiple_missing
        FROM ops.v_cabinet_claims_audit_14d
        WHERE missing_claim_bucket != 'NONE'
        GROUP BY root_cause
        ORDER BY count DESC
        LIMIT 10;
    """
    execute_query(engine, query2, "2. TOP ROOT CAUSES")
    
    # 3. Casos de ejemplo con missing claims
    query3 = """
        SELECT 
            driver_id,
            lead_date,
            trips_in_14d,
            should_have_claim_m1,
            has_claim_m1,
            should_have_claim_m5,
            has_claim_m5,
            missing_claim_bucket,
            root_cause
        FROM ops.v_cabinet_claims_audit_14d
        WHERE missing_claim_bucket != 'NONE'
        ORDER BY lead_date DESC
        LIMIT 10;
    """
    execute_query(engine, query3, "3. CASOS DE EJEMPLO: Drivers con Missing Claims")
    
    # 4. Verificación: Claims sin pago (no debe haber dependencia)
    query4 = """
        SELECT 
            COUNT(*) AS total_claims,
            COUNT(*) FILTER (WHERE paid_flag = false) AS claims_sin_pago,
            COUNT(*) FILTER (WHERE paid_flag = true) AS claims_con_pago,
            ROUND(100.0 * COUNT(*) FILTER (WHERE paid_flag = false) / COUNT(*), 2) AS pct_sin_pago
        FROM ops.v_claims_payment_status_cabinet;
    """
    execute_query(engine, query4, "4. VERIFICACIÓN: Claims sin pago (no debe haber dependencia)")
    
    # 5. Verificación: M5/M25 sin M1 (no debe haber dependencia)
    query5 = """
        SELECT 
            COUNT(*) FILTER (WHERE milestone_value = 5) AS total_m5,
            COUNT(*) FILTER (WHERE milestone_value = 5 AND driver_id NOT IN (
                SELECT driver_id FROM ops.v_claims_payment_status_cabinet WHERE milestone_value = 1
            )) AS m5_sin_m1,
            COUNT(*) FILTER (WHERE milestone_value = 25) AS total_m25,
            COUNT(*) FILTER (WHERE milestone_value = 25 AND driver_id NOT IN (
                SELECT driver_id FROM ops.v_claims_payment_status_cabinet WHERE milestone_value = 1
            )) AS m25_sin_m1
        FROM ops.v_claims_payment_status_cabinet;
    """
    execute_query(engine, query5, "5. VERIFICACIÓN: M5/M25 sin M1 (no debe haber dependencia)")
    
    # 6. Caso específico: trips>=5 debe tener M1 y M5
    query6 = """
        SELECT 
            a.driver_id,
            a.trips_in_14d,
            a.should_have_claim_m1,
            a.has_claim_m1,
            a.should_have_claim_m5,
            a.has_claim_m5,
            CASE 
                WHEN a.trips_in_14d >= 5 AND a.should_have_claim_m1 = true AND a.has_claim_m1 = true 
                     AND a.should_have_claim_m5 = true AND a.has_claim_m5 = true
                THEN 'OK'
                ELSE 'PROBLEMA'
            END AS status
        FROM ops.v_cabinet_claims_audit_14d a
        WHERE a.trips_in_14d >= 5
            AND (a.should_have_claim_m1 = true OR a.should_have_claim_m5 = true)
        ORDER BY a.trips_in_14d DESC
        LIMIT 10;
    """
    execute_query(engine, query6, "6. CASO ESPECÍFICO: Drivers con trips>=5 (deben tener M1 y M5)")
    
    logger.info("\n" + "="*60)
    logger.info("VERIFICACIÓN COMPLETADA")
    logger.info("="*60)
    logger.info("\nInterpretación:")
    logger.info("- Missing claims deberían ser bajos o cero después del fix")
    logger.info("- Root causes deberían mostrar principalmente 'VIEW_FILTERING_OUT' si el fix funcionó")
    logger.info("- Claims sin pago deberían existir (no hay dependencia de pago)")
    logger.info("- M5/M25 sin M1 deberían existir (no hay dependencia de M1)")
    logger.info("="*60 + "\n")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
