#!/usr/bin/env python3
"""
Script para desplegar todas las vistas materializadas necesarias para optimizar
el rendimiento de las APIs de Cobranza Yango.

Ejecutar: python deploy_materialized_views.py
"""
import sys
import time
from datetime import datetime

from sqlalchemy import create_engine, text
from app.config import settings


def log(message: str):
    """Imprime mensaje con timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def execute_sql(engine, sql: str, description: str):
    """Ejecuta SQL con manejo de errores."""
    log(f"  Ejecutando: {description}...")
    start = time.time()
    try:
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        elapsed = time.time() - start
        log(f"  ✓ {description} completado ({elapsed:.2f}s)")
        return True
    except Exception as e:
        elapsed = time.time() - start
        log(f"  ✗ Error en {description}: {str(e)[:200]}")
        return False


def main():
    log("=" * 60)
    log("INICIO: Despliegue de Vistas Materializadas")
    log("=" * 60)
    
    # Conectar a la base de datos
    log(f"Conectando a la base de datos...")
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        log("✓ Conexión exitosa")
    except Exception as e:
        log(f"✗ Error de conexión: {e}")
        sys.exit(1)
    
    success_count = 0
    error_count = 0
    
    # ==========================================================================
    # PASO 1: Crear MV de cabinet_financial_14d
    # ==========================================================================
    log("")
    log(">>> PASO 1: Creando ops.mv_cabinet_financial_14d...")
    
    sql_drop_mv_cabinet = "DROP MATERIALIZED VIEW IF EXISTS ops.mv_cabinet_financial_14d CASCADE;"
    
    sql_create_mv_cabinet = """
    CREATE MATERIALIZED VIEW ops.mv_cabinet_financial_14d AS
    SELECT * FROM ops.v_cabinet_financial_14d;
    """
    
    sql_indexes_mv_cabinet = """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_cabinet_fin_driver_id_unique 
    ON ops.mv_cabinet_financial_14d(driver_id);
    
    CREATE INDEX IF NOT EXISTS idx_mv_cabinet_financial_14d_lead_date 
    ON ops.mv_cabinet_financial_14d(lead_date);
    
    CREATE INDEX IF NOT EXISTS idx_mv_cabinet_financial_14d_amount_due 
    ON ops.mv_cabinet_financial_14d(amount_due_yango DESC) 
    WHERE amount_due_yango > 0;
    """
    
    if execute_sql(engine, sql_drop_mv_cabinet, "DROP mv_cabinet_financial_14d"):
        if execute_sql(engine, sql_create_mv_cabinet, "CREATE mv_cabinet_financial_14d"):
            if execute_sql(engine, sql_indexes_mv_cabinet, "Índices mv_cabinet_financial_14d"):
                success_count += 1
            else:
                error_count += 1
        else:
            error_count += 1
    else:
        error_count += 1
    
    # ==========================================================================
    # PASO 2: Crear MV de claims_payment_status_cabinet
    # ==========================================================================
    log("")
    log(">>> PASO 2: Creando ops.mv_claims_payment_status_cabinet...")
    
    sql_drop_mv_claims = "DROP MATERIALIZED VIEW IF EXISTS ops.mv_claims_payment_status_cabinet CASCADE;"
    
    sql_create_mv_claims = """
    CREATE MATERIALIZED VIEW ops.mv_claims_payment_status_cabinet AS
    SELECT 
        driver_id,
        person_key,
        milestone_value,
        lead_date,
        due_date,
        expected_amount,
        days_overdue,
        bucket_overdue,
        paid_flag,
        paid_date,
        payment_key,
        payment_identity_status,
        payment_match_rule,
        payment_match_confidence,
        payment_status,
        payment_reason,
        reason_code,
        action_priority
    FROM ops.v_claims_payment_status_cabinet;
    """
    
    sql_indexes_mv_claims = """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_claims_driver_milestone 
    ON ops.mv_claims_payment_status_cabinet(driver_id, milestone_value) 
    WHERE driver_id IS NOT NULL;
    
    CREATE INDEX IF NOT EXISTS idx_mv_claims_person_key 
    ON ops.mv_claims_payment_status_cabinet(person_key) 
    WHERE person_key IS NOT NULL;
    
    CREATE INDEX IF NOT EXISTS idx_mv_claims_reason_code 
    ON ops.mv_claims_payment_status_cabinet(reason_code);
    
    CREATE INDEX IF NOT EXISTS idx_mv_claims_paid_flag 
    ON ops.mv_claims_payment_status_cabinet(paid_flag);
    """
    
    if execute_sql(engine, sql_drop_mv_claims, "DROP mv_claims_payment_status_cabinet"):
        if execute_sql(engine, sql_create_mv_claims, "CREATE mv_claims_payment_status_cabinet"):
            if execute_sql(engine, sql_indexes_mv_claims, "Índices mv_claims_payment_status_cabinet"):
                success_count += 1
            else:
                error_count += 1
        else:
            error_count += 1
    else:
        error_count += 1
    
    # ==========================================================================
    # PASO 3: Crear MV enriched de cobranza
    # ==========================================================================
    log("")
    log(">>> PASO 3: Creando ops.mv_yango_cabinet_cobranza_enriched_14d...")
    
    sql_drop_mv_enriched = "DROP MATERIALIZED VIEW IF EXISTS ops.mv_yango_cabinet_cobranza_enriched_14d CASCADE;"
    
    sql_create_mv_enriched = """
    CREATE MATERIALIZED VIEW ops.mv_yango_cabinet_cobranza_enriched_14d AS
    SELECT 
        cf.driver_id,
        cf.driver_name,
        cf.lead_date,
        cf.iso_week,
        DATE_TRUNC('week', cf.lead_date)::date AS week_start,
        cf.connected_flag,
        cf.connected_date,
        cf.total_trips_14d,
        cf.reached_m1_14d,
        cf.reached_m5_14d,
        cf.reached_m25_14d,
        cf.expected_amount_m1,
        cf.expected_amount_m5,
        cf.expected_amount_m25,
        cf.expected_total_yango,
        cf.claim_m1_exists,
        cf.claim_m1_paid,
        cf.claim_m5_exists,
        cf.claim_m5_paid,
        cf.claim_m25_exists,
        cf.claim_m25_paid,
        cf.paid_amount_m1,
        cf.paid_amount_m5,
        cf.paid_amount_m25,
        cf.total_paid_yango,
        cf.amount_due_yango,
        
        -- Scout fields (NULL por ahora, requiere v_scout_attribution)
        NULL::integer AS scout_id,
        NULL::text AS scout_name,
        NULL::text AS scout_name_normalized,
        NULL::boolean AS scout_is_active,
        'MISSING'::text AS scout_quality_bucket,
        false AS is_scout_resolved,
        NULL::text AS scout_source_table,
        NULL::date AS scout_attribution_date,
        NULL::integer AS scout_priority,
        
        -- Person key
        il_driver.person_key
    FROM ops.v_cabinet_financial_14d cf
    LEFT JOIN LATERAL (
        SELECT DISTINCT person_key
        FROM canon.identity_links il
        WHERE il.source_table = 'drivers'
            AND il.source_pk = cf.driver_id::TEXT
        LIMIT 1
    ) il_driver ON true;
    """
    
    sql_indexes_mv_enriched = """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_cobranza_enriched_driver_id_unique
    ON ops.mv_yango_cabinet_cobranza_enriched_14d(driver_id);
    
    CREATE INDEX IF NOT EXISTS idx_mv_cobranza_enriched_lead_date 
    ON ops.mv_yango_cabinet_cobranza_enriched_14d(lead_date DESC);
    
    CREATE INDEX IF NOT EXISTS idx_mv_cobranza_enriched_week_start 
    ON ops.mv_yango_cabinet_cobranza_enriched_14d(week_start DESC);
    
    CREATE INDEX IF NOT EXISTS idx_mv_cobranza_enriched_debt_partial 
    ON ops.mv_yango_cabinet_cobranza_enriched_14d(amount_due_yango DESC) 
    WHERE amount_due_yango > 0;
    
    CREATE INDEX IF NOT EXISTS idx_mv_cobranza_enriched_milestone_flags 
    ON ops.mv_yango_cabinet_cobranza_enriched_14d(reached_m1_14d, reached_m5_14d, reached_m25_14d);
    """
    
    if execute_sql(engine, sql_drop_mv_enriched, "DROP mv_yango_cabinet_cobranza_enriched_14d"):
        if execute_sql(engine, sql_create_mv_enriched, "CREATE mv_yango_cabinet_cobranza_enriched_14d"):
            if execute_sql(engine, sql_indexes_mv_enriched, "Índices mv_yango_cabinet_cobranza_enriched_14d"):
                success_count += 1
            else:
                error_count += 1
        else:
            error_count += 1
    else:
        error_count += 1
    
    # ==========================================================================
    # PASO 4: Crear índice en identity_links
    # ==========================================================================
    log("")
    log(">>> PASO 4: Creando índice en canon.identity_links...")
    
    sql_index_identity = """
    CREATE INDEX IF NOT EXISTS idx_identity_links_source_cabinet
    ON canon.identity_links(source_table, source_pk)
    WHERE source_table = 'module_ct_cabinet_leads';
    """
    
    if execute_sql(engine, sql_index_identity, "Índice identity_links"):
        success_count += 1
    else:
        error_count += 1
    
    # ==========================================================================
    # RESUMEN
    # ==========================================================================
    log("")
    log("=" * 60)
    log("DESPLIEGUE COMPLETADO")
    log("=" * 60)
    log(f"  Exitosos: {success_count}")
    log(f"  Errores: {error_count}")
    log("")
    log("Vistas materializadas creadas:")
    log("  1. ops.mv_cabinet_financial_14d")
    log("  2. ops.mv_claims_payment_status_cabinet")
    log("  3. ops.mv_yango_cabinet_cobranza_enriched_14d")
    log("")
    
    if error_count > 0:
        log("⚠️ Hubo errores. Revisar logs arriba.")
        sys.exit(1)
    else:
        log("✓ Todas las vistas materializadas creadas exitosamente.")


if __name__ == "__main__":
    main()
