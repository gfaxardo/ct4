#!/usr/bin/env python3
"""
Verificación final de Scout Attribution Fix
Ejecuta queries de verificación y genera reporte detallado
"""

import sys
from pathlib import Path
from datetime import datetime
from sqlalchemy import create_engine, text
import psycopg2
from urllib.parse import urlparse

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.config import settings

database_url = settings.database_url
parsed = urlparse(database_url)
conn_params = {
    'host': parsed.hostname,
    'port': parsed.port or 5432,
    'database': parsed.path[1:] if parsed.path else None,
    'user': parsed.username,
    'password': parsed.password
}

print("="*80)
print("VERIFICACION FINAL: SCOUT ATTRIBUTION FIX")
print("="*80)
print()

with psycopg2.connect(**conn_params) as conn:
    with conn.cursor() as cur:
        # 1. Verificar vistas creadas
        print("1. VISTAS CREADAS:")
        print("-" * 80)
        cur.execute("""
            SELECT table_name 
            FROM information_schema.views 
            WHERE table_schema = 'ops' 
                AND table_name LIKE '%scout%'
            ORDER BY table_name
        """)
        views = cur.fetchall()
        for view in views:
            print(f"  [OK] {view[0]}")
        print()
        
        # 2. Verificar conflictos
        print("2. CONFLICTOS DETECTADOS:")
        print("-" * 80)
        try:
            cur.execute("SELECT COUNT(*) FROM ops.v_scout_attribution_conflicts")
            conflict_count = cur.fetchone()[0]
            print(f"  Total conflictos: {conflict_count}")
            if conflict_count > 0:
                cur.execute("""
                    SELECT person_key, distinct_scout_count, scout_ids, total_records
                    FROM ops.v_scout_attribution_conflicts
                    ORDER BY distinct_scout_count DESC, total_records DESC
                    LIMIT 10
                """)
                conflicts = cur.fetchall()
                print("  Top 10 conflictos:")
                for c in conflicts:
                    print(f"    Person: {c[0]}, Scouts: {c[2]}, Registros: {c[3]}")
        except Exception as e:
            print(f"  ERROR: {e}")
        print()
        
        # 3. Cobertura de scout satisfactorio
        print("3. COBERTURA SCOUT SATISFACTORIO:")
        print("-" * 80)
        cur.execute("""
            SELECT 
                COUNT(DISTINCT sd.id) AS total_scouting_daily_with_scout,
                COUNT(DISTINCT sd.id) FILTER (
                    WHERE EXISTS (
                        SELECT 1 FROM canon.identity_links il
                        JOIN observational.lead_ledger ll ON ll.person_key = il.person_key
                        WHERE il.source_table = 'module_ct_scouting_daily'
                            AND il.source_pk = sd.id::TEXT
                            AND ll.attributed_scout_id IS NOT NULL
                    )
                ) AS with_ledger_scout,
                ROUND(
                    (COUNT(DISTINCT sd.id) FILTER (
                        WHERE EXISTS (
                            SELECT 1 FROM canon.identity_links il
                            JOIN observational.lead_ledger ll ON ll.person_key = il.person_key
                            WHERE il.source_table = 'module_ct_scouting_daily'
                                AND il.source_pk = sd.id::TEXT
                                AND ll.attributed_scout_id IS NOT NULL
                        )
                    )::NUMERIC / NULLIF(COUNT(DISTINCT sd.id), 0)) * 100, 2
                ) AS pct_coverage
            FROM public.module_ct_scouting_daily sd
            WHERE sd.scout_id IS NOT NULL
        """)
        coverage = cur.fetchone()
        print(f"  Total scouting_daily con scout_id: {coverage[0]}")
        print(f"  Con lead_ledger scout satisfactorio: {coverage[1]}")
        print(f"  % Cobertura: {coverage[2]}%")
        print()
        
        # 4. Categorías de personas sin scout
        print("4. CATEGORÍAS DE PERSONAS SIN SCOUT:")
        print("-" * 80)
        try:
            cur.execute("""
                SELECT categoria, COUNT(*) AS count
                FROM ops.v_persons_without_scout_categorized
                GROUP BY categoria
                ORDER BY count DESC
            """)
            categories = cur.fetchall()
            for cat, count in categories:
                print(f"  {cat}: {count}")
        except Exception as e:
            print(f"  ERROR: {e}")
        print()
        
        # 5. Cobranza Yango con scout
        print("5. COBRANZA YANGO CON SCOUT:")
        print("-" * 80)
        try:
            cur.execute("""
                SELECT 
                    COUNT(*) AS total_claims,
                    COUNT(*) FILTER (WHERE is_scout_resolved = true) AS claims_with_scout,
                    ROUND((COUNT(*) FILTER (WHERE is_scout_resolved = true)::NUMERIC / COUNT(*) * 100), 2) AS pct_with_scout
                FROM ops.v_yango_collection_with_scout
            """)
            yango = cur.fetchone()
            print(f"  Total claims: {yango[0]}")
            print(f"  Claims con scout: {yango[1]}")
            print(f"  % Cobertura: {yango[2]}%")
            
            cur.execute("""
                SELECT scout_quality_bucket, COUNT(*) AS count
                FROM ops.v_yango_collection_with_scout
                GROUP BY scout_quality_bucket
                ORDER BY count DESC
            """)
            buckets = cur.fetchall()
            print("  Por calidad:")
            for bucket, count in buckets:
                print(f"    {bucket}: {count}")
        except Exception as e:
            print(f"  ERROR: {e}")
        print()
        
        # 6. Backfill audit summary
        print("6. RESUMEN DE BACKFILLS:")
        print("-" * 80)
        try:
            cur.execute("""
                SELECT 
                    'lead_ledger' AS tipo,
                    COUNT(*) AS registros_actualizados,
                    MIN(backfill_timestamp) AS primero,
                    MAX(backfill_timestamp) AS ultimo
                FROM ops.lead_ledger_scout_backfill_audit
                WHERE backfill_method = 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS'
            """)
            audit_ll = cur.fetchone()
            if audit_ll and audit_ll[1] > 0:
                print(f"  lead_ledger: {audit_ll[1]} registros actualizados")
                print(f"    Desde: {audit_ll[2]} hasta: {audit_ll[3]}")
            else:
                print(f"  lead_ledger: 0 registros (ya estaban actualizados o no había candidatos)")
        except Exception as e:
            print(f"  ERROR: {e}")
        
        try:
            cur.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE match_result = 'created') AS created,
                    COUNT(*) FILTER (WHERE match_result = 'skipped_exists') AS skipped,
                    COUNT(*) FILTER (WHERE match_result = 'ambiguous') AS ambiguous,
                    COUNT(*) FILTER (WHERE match_result = 'not_found') AS not_found
                FROM ops.identity_links_backfill_audit
                WHERE backfill_timestamp >= CURRENT_DATE
            """)
            audit_il = cur.fetchone()
            if audit_il:
                print(f"  identity_links: created={audit_il[0]}, skipped={audit_il[1]}, ambiguous={audit_il[2]}, not_found={audit_il[3]}")
        except Exception as e:
            print(f"  ERROR: {e}")
        print()

print("="*80)
print("VERIFICACION COMPLETA")
print("="*80)

