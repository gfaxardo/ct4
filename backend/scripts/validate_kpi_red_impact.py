#!/usr/bin/env python
"""
Script de validación del impacto real del recovery en el KPI rojo.
Ejecuta seed, recovery y verifica before/after.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from sqlalchemy import text
from jobs.seed_kpi_red_queue import run_job as run_seed_job
from jobs.recover_kpi_red_leads import run_job as run_recover_job

def get_backlog_count():
    """Obtiene el conteo actual del backlog del KPI rojo"""
    db = SessionLocal()
    try:
        query = text("""
            WITH leads_with_identity AS (
                SELECT DISTINCT
                    COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk
                FROM public.module_ct_cabinet_leads mcl
                INNER JOIN canon.identity_links il
                    ON il.source_table = 'module_ct_cabinet_leads'
                    AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
            ),
            leads_with_claims AS (
                SELECT DISTINCT
                    COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk
                FROM public.module_ct_cabinet_leads mcl
                INNER JOIN canon.identity_links il
                    ON il.source_table = 'module_ct_cabinet_leads'
                    AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
                INNER JOIN ops.v_claims_payment_status_cabinet c
                    ON c.person_key = il.person_key
                    AND c.driver_id IS NOT NULL
            )
            SELECT 
                COUNT(*) - COUNT(DISTINCT COALESCE(li.lead_source_pk, lc.lead_source_pk)) AS leads_without_both
            FROM public.module_ct_cabinet_leads mcl
            LEFT JOIN leads_with_identity li
                ON li.lead_source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
            LEFT JOIN leads_with_claims lc
                ON lc.lead_source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
        """)
        result = db.execute(query)
        row = result.fetchone()
        return row.leads_without_both if row else 0
    finally:
        db.close()

def get_matched_leads_from_queue():
    """Obtiene leads matched de la queue"""
    db = SessionLocal()
    try:
        query = text("""
            SELECT lead_source_pk, matched_person_key, fail_reason
            FROM ops.cabinet_kpi_red_recovery_queue
            WHERE status = 'matched'
            ORDER BY updated_at DESC
            LIMIT 100
        """)
        result = db.execute(query)
        return [dict(row._mapping) if hasattr(row, '_mapping') else dict(row) for row in result.fetchall()]
    finally:
        db.close()

def get_failed_leads_from_queue():
    """Obtiene leads failed de la queue con sus razones"""
    db = SessionLocal()
    try:
        query = text("""
            SELECT 
                fail_reason,
                COUNT(*) as count
            FROM ops.cabinet_kpi_red_recovery_queue
            WHERE status = 'failed'
            GROUP BY fail_reason
            ORDER BY count DESC
        """)
        result = db.execute(query)
        return {row.fail_reason: row.count for row in result.fetchall()}
    finally:
        db.close()

def validate_kpi_red_impact(limit: int = 1000):
    """Ejecuta seed, recovery y valida impacto"""
    print("=" * 80)
    print("VALIDACIÓN CRÍTICA: Impacto Real en el KPI Rojo")
    print("=" * 80)
    print()
    
    # 1. Obtener backlog ANTES
    print("1. Obteniendo backlog ANTES...")
    backlog_before = get_backlog_count()
    print(f"   BACKLOG ANTES: {backlog_before}")
    print()
    
    # 2. Ejecutar seed
    print("2. Ejecutando seed_kpi_red_queue...")
    seed_result = run_seed_job()
    print(f"   Seed result: processed={seed_result.get('processed', 0)}, inserted={seed_result.get('inserted', 0)}, updated={seed_result.get('updated', 0)}")
    print()
    
    # 3. Ejecutar recovery
    print(f"3. Ejecutando recover_kpi_red_leads (limit={limit})...")
    recover_result = run_recover_job(limit=limit)
    print(f"   Recovery result: processed={recover_result.get('processed', 0)}, matched={recover_result.get('matched', 0)}, failed={recover_result.get('failed', 0)}, skipped={recover_result.get('skipped', 0)}")
    print()
    
    # 4. Obtener backlog DESPUÉS
    print("4. Obteniendo backlog DESPUÉS...")
    backlog_after = get_backlog_count()
    print(f"   BACKLOG DESPUÉS: {backlog_after}")
    print()
    
    # 5. Calcular diferencia
    backlog_delta = backlog_before - backlog_after
    print(f"5. DIFERENCIA: {backlog_delta} (antes: {backlog_before}, después: {backlog_after})")
    print()
    
    # 6. Obtener leads matched de la queue
    print("6. Leads matched en queue (primeros 10):")
    matched_leads = get_matched_leads_from_queue()
    for i, lead in enumerate(matched_leads[:10], 1):
        print(f"   {i}. lead_source_pk={lead['lead_source_pk'][:30]}..., person_key={lead.get('matched_person_key')}")
    print(f"   Total matched: {len(matched_leads)}")
    print()
    
    # 7. Obtener leads failed con razones
    print("7. Leads failed por razón:")
    failed_by_reason = get_failed_leads_from_queue()
    for reason, count in failed_by_reason.items():
        print(f"   {reason}: {count}")
    print()
    
    # 8. Resumen
    print("=" * 80)
    print("RESUMEN")
    print("=" * 80)
    print(f"Backlog ANTES: {backlog_before}")
    print(f"Backlog DESPUÉS: {backlog_after}")
    print(f"Delta: {backlog_delta} ({'+' if backlog_delta > 0 else ''}{backlog_delta})")
    print(f"Leads matched en queue: {recover_result.get('matched', 0)}")
    print(f"Leads failed en queue: {recover_result.get('failed', 0)}")
    print()
    
    if backlog_delta > 0:
        print("[OK] EXITO: El backlog BAJO despues del recovery")
    elif backlog_delta == 0:
        print("[WARNING] ADVERTENCIA: El backlog NO cambio")
    else:
        print("[WARNING] ADVERTENCIA: El backlog SUBIO (puede ser normal si entraron nuevos leads)")
    print()
    
    return {
        "backlog_before": backlog_before,
        "backlog_after": backlog_after,
        "backlog_delta": backlog_delta,
        "matched_count": recover_result.get('matched', 0),
        "failed_count": recover_result.get('failed', 0),
        "failed_by_reason": failed_by_reason
    }

if __name__ == "__main__":
    import sys
    limit = 1000
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
        except ValueError:
            pass
    
    result = validate_kpi_red_impact(limit=limit)
    print(f"Validación completa. Resultado: {result}")
