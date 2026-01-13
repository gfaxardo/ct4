"""
Script de diagnóstico para Identity Gap Recovery
Ejecuta análisis completo del estado actual del sistema de recovery.
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
from sqlalchemy import text

# Agregar el directorio raíz al path para imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal

def print_section(title: str):
    """Imprime un separador de sección"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def print_sql(sql: str):
    """Imprime SQL formateado"""
    print("SQL:")
    print("-" * 80)
    print(sql)
    print("-" * 80)

def diagnose_identity_gap():
    """Ejecuta diagnóstico completo del Identity Gap"""
    db = SessionLocal()
    
    try:
        # ============================================================
        # 0.1) MÉTRICAS ACTUALES DE BRECHA
        # ============================================================
        print_section("0.1) MÉTRICAS ACTUALES DE BRECHA")
        
        sql_gap_metrics = """
            SELECT 
                COUNT(*) as total_leads,
                COUNT(*) FILTER (WHERE gap_reason != 'resolved') as unresolved,
                COUNT(*) FILTER (WHERE gap_reason = 'resolved') as resolved,
                ROUND(100.0 * COUNT(*) FILTER (WHERE gap_reason != 'resolved') / NULLIF(COUNT(*), 0), 2) as pct_unresolved,
                COUNT(*) FILTER (WHERE risk_level = 'high') as high_risk
            FROM ops.v_identity_gap_analysis
        """
        print_sql(sql_gap_metrics)
        
        result = db.execute(text(sql_gap_metrics))
        row = result.fetchone()
        
        print("\nRESULTADOS:")
        print(f"  Total Leads: {row.total_leads:,}")
        print(f"  Unresolved: {row.unresolved:,}")
        print(f"  Resolved: {row.resolved:,}")
        print(f"  % Unresolved: {row.pct_unresolved}%")
        print(f"  High Risk: {row.high_risk:,}")
        
        # Breakdown por gap_reason
        sql_breakdown = """
            SELECT 
                gap_reason,
                risk_level,
                COUNT(*) as count
            FROM ops.v_identity_gap_analysis
            GROUP BY gap_reason, risk_level
            ORDER BY count DESC
        """
        print_sql(sql_breakdown)
        
        result = db.execute(text(sql_breakdown))
        rows = result.fetchall()
        
        print("\nBREAKDOWN POR GAP_REASON Y RISK_LEVEL:")
        for r in rows:
            print(f"  {r.gap_reason:30} | {r.risk_level:6} | {r.count:>8,}")
        
        # ============================================================
        # 0.2) FRESHNESS DEL JOB
        # ============================================================
        print_section("0.2) FRESHNESS DEL JOB (ops.identity_matching_jobs)")
        
        sql_job_freshness = """
            SELECT 
                COUNT(*) as total_jobs,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                COUNT(*) FILTER (WHERE status = 'matched') as matched,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                MAX(last_attempt_at) as last_run,
                COUNT(*) FILTER (WHERE last_attempt_at >= NOW() - INTERVAL '24 hours') as jobs_last_24h
            FROM ops.identity_matching_jobs
        """
        print_sql(sql_job_freshness)
        
        result = db.execute(text(sql_job_freshness))
        row = result.fetchone()
        
        print("\nRESULTADOS:")
        print(f"  Total Jobs: {row.total_jobs:,}")
        print(f"  Pending: {row.pending:,}")
        print(f"  Matched: {row.matched:,}")
        print(f"  Failed: {row.failed:,}")
        print(f"  Last Run: {row.last_run or 'NUNCA'}")
        print(f"  Jobs en últimas 24h: {row.jobs_last_24h:,}")
        
        if row.last_run:
            # Calcular horas desde último run (usar SQL para evitar problemas de timezone)
            hours_query = text("""
                SELECT EXTRACT(EPOCH FROM (NOW() - MAX(last_attempt_at)))/3600 as hours_ago
                FROM ops.identity_matching_jobs
            """)
            hours_result = db.execute(hours_query)
            hours_ago = hours_result.scalar() or 0
            print(f"  Horas desde ultimo run: {hours_ago:.1f}")
            if hours_ago > 24:
                print(f"  [WARNING] JOB STALE (mas de 24h sin correr)")
            else:
                print(f"  [OK] Job fresco (<24h)")
        else:
            print(f"  [WARNING] JOB NUNCA HA CORRIDO")
        
        # ============================================================
        # 0.3) TOP FAIL_REASONS Y ATTEMPT_COUNT
        # ============================================================
        print_section("0.3) TOP FAIL_REASONS Y ATTEMPT_COUNT")
        
        sql_fail_reasons = """
            SELECT 
                fail_reason,
                COUNT(*) as count,
                AVG(attempt_count)::int as avg_attempts,
                MAX(attempt_count) as max_attempts,
                COUNT(*) FILTER (WHERE attempt_count >= 5) as stuck_count
            FROM ops.identity_matching_jobs
            WHERE status = 'failed' OR (status = 'pending' AND attempt_count > 0)
            GROUP BY fail_reason
            ORDER BY count DESC
            LIMIT 10
        """
        print_sql(sql_fail_reasons)
        
        result = db.execute(text(sql_fail_reasons))
        rows = result.fetchall()
        
        print("\nTOP 10 FAIL_REASONS:")
        if rows:
            print(f"  {'FAIL_REASON':<40} | {'COUNT':>8} | {'AVG_ATTEMPTS':>12} | {'MAX_ATTEMPTS':>12} | {'STUCK':>8}")
            print("  " + "-" * 90)
            for r in rows:
                print(f"  {str(r.fail_reason or 'NULL'):<40} | {r.count:>8,} | {r.avg_attempts:>12} | {r.max_attempts:>12} | {r.stuck_count:>8,}")
        else:
            print("  No hay jobs fallidos o pendientes")
        
        # ============================================================
        # 0.4) VOLUMEN PROCESADO REAL (ÚLTIMAS 24H)
        # ============================================================
        print_section("0.4) VOLUMEN PROCESADO REAL (ÚLTIMAS 24H)")
        
        sql_volume_24h = """
            SELECT 
                COUNT(*) FILTER (WHERE last_attempt_at >= NOW() - INTERVAL '24 hours') as processed_24h,
                COUNT(*) FILTER (WHERE last_attempt_at >= NOW() - INTERVAL '24 hours' AND status = 'matched') as matched_24h,
                COUNT(*) FILTER (WHERE last_attempt_at >= NOW() - INTERVAL '24 hours' AND status = 'failed') as failed_24h
            FROM ops.identity_matching_jobs
        """
        print_sql(sql_volume_24h)
        
        result = db.execute(text(sql_volume_24h))
        row = result.fetchone()
        
        print("\nRESULTADOS:")
        print(f"  Procesados en últimas 24h: {row.processed_24h:,}")
        print(f"  Matched en últimas 24h: {row.matched_24h:,}")
        print(f"  Failed en últimas 24h: {row.failed_24h:,}")
        
        # Leads unresolved que deberían procesarse
        sql_unresolved_count = """
            SELECT COUNT(*) as unresolved_count
            FROM ops.v_identity_gap_analysis
            WHERE gap_reason != 'resolved'
        """
        result = db.execute(text(sql_unresolved_count))
        unresolved_count = result.scalar()
        
        print(f"\n  Leads unresolved totales: {unresolved_count:,}")
        if unresolved_count > 0 and row.processed_24h == 0:
            print(f"  [WARNING] PROBLEMA: Hay {unresolved_count:,} leads unresolved pero 0 procesados en 24h")
        elif unresolved_count > 0 and row.processed_24h > 0:
            print(f"  [OK] Job esta procesando ({row.processed_24h:,} en 24h)")
        
        # ============================================================
        # 0.5) VERIFICACIÓN DE VÍNCULOS CREADOS
        # ============================================================
        print_section("0.5) VERIFICACIÓN DE VÍNCULOS CREADOS")
        
        sql_links_created = """
            SELECT 
                COUNT(*) as total_links,
                COUNT(*) FILTER (WHERE linked_at >= NOW() - INTERVAL '24 hours') as links_24h,
                COUNT(*) FILTER (WHERE linked_at >= NOW() - INTERVAL '7 days') as links_7d
            FROM canon.identity_links
            WHERE source_table = 'module_ct_cabinet_leads'
        """
        print_sql(sql_links_created)
        
        result = db.execute(text(sql_links_created))
        row = result.fetchone()
        
        print("\nRESULTADOS:")
        print(f"  Total identity_links (cabinet_leads): {row.total_links:,}")
        print(f"  Creados en últimas 24h: {row.links_24h:,}")
        print(f"  Creados en últimos 7 días: {row.links_7d:,}")
        
        # Verificar si hay jobs matched pero sin links
        sql_matched_no_link = """
            SELECT COUNT(*) as count
            FROM ops.identity_matching_jobs j
            WHERE j.status = 'matched'
              AND NOT EXISTS (
                  SELECT 1
                  FROM canon.identity_links il
                  WHERE il.source_table = 'module_ct_cabinet_leads'
                    AND il.source_pk = j.source_id
              )
        """
        result = db.execute(text(sql_matched_no_link))
        matched_no_link = result.scalar()
        
        if matched_no_link > 0:
            print(f"\n  [WARNING] PROBLEMA: {matched_no_link:,} jobs marcados como 'matched' pero SIN identity_link")
        else:
            print(f"\n  [OK] Todos los jobs 'matched' tienen identity_link")
        
        # ============================================================
        # 0.6) VERIFICACIÓN DE ORIGINS CREADOS
        # ============================================================
        print_section("0.6) VERIFICACIÓN DE ORIGINS CREADOS")
        
        sql_origins_created = """
            SELECT 
                COUNT(*) as total_origins,
                COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '24 hours') as origins_24h,
                COUNT(*) FILTER (WHERE origin_tag = 'cabinet_lead') as cabinet_origins
            FROM canon.identity_origin
        """
        print_sql(sql_origins_created)
        
        result = db.execute(text(sql_origins_created))
        row = result.fetchone()
        
        print("\nRESULTADOS:")
        print(f"  Total identity_origin: {row.total_origins:,}")
        print(f"  Creados en últimas 24h: {row.origins_24h:,}")
        print(f"  Con origin_tag='cabinet_lead': {row.cabinet_origins:,}")
        
        # Verificar si hay links sin origin
        sql_links_no_origin = """
            SELECT COUNT(*) as count
            FROM canon.identity_links il
            WHERE il.source_table = 'module_ct_cabinet_leads'
              AND NOT EXISTS (
                  SELECT 1
                  FROM canon.identity_origin io
                  WHERE io.person_key = il.person_key
                    AND io.origin_tag = 'cabinet_lead'
                    AND io.origin_source_id = il.source_pk
              )
        """
        result = db.execute(text(sql_links_no_origin))
        links_no_origin = result.scalar()
        
        if links_no_origin > 0:
            print(f"\n  [WARNING] PROBLEMA: {links_no_origin:,} identity_links SIN identity_origin correspondiente")
        else:
            print(f"\n  [OK] Todos los identity_links tienen identity_origin")
        
        # ============================================================
        # RESUMEN Y RECOMENDACIONES
        # ============================================================
        print_section("RESUMEN Y RECOMENDACIONES")
        
        # Obtener métricas finales
        result = db.execute(text(sql_gap_metrics))
        gap_row = result.fetchone()
        
        result = db.execute(text(sql_job_freshness))
        job_row = result.fetchone()
        
        print("\nDIAGNÓSTICO:")
        print(f"  1. Gap actual: {gap_row.pct_unresolved}% unresolved ({gap_row.unresolved:,} de {gap_row.total_leads:,})")
        
        if job_row.last_run:
            hours_query = text("""
                SELECT EXTRACT(EPOCH FROM (NOW() - MAX(last_attempt_at)))/3600 as hours_ago
                FROM ops.identity_matching_jobs
            """)
            hours_result = db.execute(hours_query)
            hours_ago = hours_result.scalar() or 0
            print(f"  2. Job freshness: {hours_ago:.1f} horas desde ultimo run")
            if hours_ago > 24:
                print(f"     [WARNING] ACCION: Configurar scheduler para correr diariamente")
        else:
            print(f"  2. Job freshness: NUNCA HA CORRIDO")
            print(f"     [WARNING] ACCION: Ejecutar job manualmente primero")
        
        print(f"  3. Volumen procesado: {job_row.jobs_last_24h:,} jobs en ultimas 24h")
        if job_row.jobs_last_24h == 0 and gap_row.unresolved > 0:
            print(f"     [WARNING] ACCION: El job no esta procesando. Verificar scheduler o ejecutar manualmente")
        
        print(f"  4. Jobs matched: {job_row.matched:,} total")
        print(f"  5. Jobs failed: {job_row.failed:,} total")
        
        if job_row.failed > 0:
            print(f"     [WARNING] ACCION: Revisar top fail_reasons arriba para identificar problemas")
        
        print("\n" + "=" * 80)
        print("DIAGNÓSTICO COMPLETADO")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n[ERROR] ERROR en diagnostico: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    diagnose_identity_gap()
