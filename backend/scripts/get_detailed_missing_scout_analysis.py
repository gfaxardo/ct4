#!/usr/bin/env python3
"""Análisis detallado de registros sin scout"""

import sys
from pathlib import Path

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.config import settings
from sqlalchemy import create_engine, text

engine = create_engine(settings.database_url)

queries = {
    "1. Total y distribución": """
        SELECT 
            'Total personas' AS metric,
            COUNT(*) AS count
        FROM canon.identity_registry
        UNION ALL
        SELECT 
            'Con scout (lead_ledger)' AS metric,
            COUNT(DISTINCT person_key) AS count
        FROM observational.lead_ledger
        WHERE attributed_scout_id IS NOT NULL
        UNION ALL
        SELECT 
            'Sin scout (lead_ledger)' AS metric,
            COUNT(DISTINCT person_key) AS count
        FROM observational.lead_ledger
        WHERE attributed_scout_id IS NULL
        UNION ALL
        SELECT 
            'Con scout en eventos' AS metric,
            COUNT(DISTINCT person_key) AS count
        FROM observational.lead_events
        WHERE person_key IS NOT NULL
            AND (scout_id IS NOT NULL OR (payload_json IS NOT NULL AND payload_json->>'scout_id' IS NOT NULL))
    """,
    
    "2. Razones en lead_ledger": """
        SELECT 
            COALESCE(attribution_rule, 'NULL') AS attribution_rule,
            confidence_level,
            decision_status,
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE attributed_scout_id IS NOT NULL) AS with_scout,
            COUNT(*) FILTER (WHERE attributed_scout_id IS NULL) AS without_scout
        FROM observational.lead_ledger
        GROUP BY attribution_rule, confidence_level, decision_status
        ORDER BY total DESC
    """,
    
    "3. Distribución por source_table": """
        SELECT 
            le.source_table,
            COUNT(*) AS total_events,
            COUNT(DISTINCT le.person_key) AS distinct_persons,
            COUNT(*) FILTER (WHERE le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL)) AS with_scout,
            COUNT(*) FILTER (WHERE le.scout_id IS NULL AND (le.payload_json IS NULL OR le.payload_json->>'scout_id' IS NULL)) AS without_scout,
            ROUND(
                COUNT(*) FILTER (WHERE le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL))::NUMERIC / 
                NULLIF(COUNT(*), 0) * 100, 
                2
            ) AS pct_with_scout
        FROM observational.lead_events le
        WHERE le.person_key IS NOT NULL
        GROUP BY le.source_table
        ORDER BY total_events DESC
    """,
    
    "4. Gap: Personas sin scout": """
        SELECT 
            COUNT(DISTINCT ir.person_key) AS personas_sin_scout,
            COUNT(DISTINCT il.person_key) AS tienen_identity_links,
            COUNT(DISTINCT le.person_key) AS tienen_lead_events,
            COUNT(DISTINCT ll.person_key) AS tienen_lead_ledger
        FROM canon.identity_registry ir
        LEFT JOIN observational.lead_ledger ll 
            ON ll.person_key = ir.person_key 
            AND ll.attributed_scout_id IS NOT NULL
        LEFT JOIN canon.identity_links il ON il.person_key = ir.person_key
        LEFT JOIN observational.lead_events le ON le.person_key = ir.person_key
        WHERE ll.person_key IS NULL
    """,
    
    "5. Muestra de casos sin scout": """
        SELECT 
            ir.person_key,
            ir.primary_full_name,
            ir.created_at::DATE AS identity_created,
            (SELECT COUNT(*) FROM canon.identity_links il WHERE il.person_key = ir.person_key) AS identity_links_count,
            (SELECT COUNT(*) FROM observational.lead_events le WHERE le.person_key = ir.person_key) AS lead_events_count,
            CASE WHEN ll.person_key IS NOT NULL THEN 'YES' ELSE 'NO' END AS has_lead_ledger,
            ll.attribution_rule,
            ll.confidence_level
        FROM canon.identity_registry ir
        LEFT JOIN observational.lead_ledger ll ON ll.person_key = ir.person_key
        LEFT JOIN observational.lead_ledger ll_with_scout 
            ON ll_with_scout.person_key = ir.person_key 
            AND ll_with_scout.attributed_scout_id IS NOT NULL
        WHERE ll_with_scout.person_key IS NULL
        ORDER BY ir.created_at DESC
        LIMIT 10
    """
}

print("="*70)
print("ANALISIS DETALLADO: REGISTROS SIN SCOUT")
print("="*70)

with engine.connect() as conn:
    for title, query in queries.items():
        print(f"\n{title}")
        print("-"*70)
        try:
            result = conn.execute(text(query))
            rows = result.fetchall()
            columns = result.keys()
            
            # Mostrar resultados
            for row in rows:
                print(" | ".join([f"{col}: {val}" for col, val in zip(columns, row)]))
        except Exception as e:
            print(f"[ERROR] {str(e)[:200]}")

print("\n" + "="*70)
print("ANALISIS COMPLETADO")
print("="*70)


