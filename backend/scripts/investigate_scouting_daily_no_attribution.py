#!/usr/bin/env python3
"""Investigar por qué scouting_daily no tiene scout atribuido"""

import sys
from pathlib import Path

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.config import settings
from sqlalchemy import create_engine, text

engine = create_engine(settings.database_url)

queries = {
    "1. Verificar si scouting_daily tiene identity_links": """
        SELECT 
            COUNT(DISTINCT sd.id) AS total_scouting_daily,
            COUNT(DISTINCT il.source_pk) AS con_identity_links,
            COUNT(DISTINCT sd.id) - COUNT(DISTINCT il.source_pk) AS sin_identity_links
        FROM public.module_ct_scouting_daily sd
        LEFT JOIN canon.identity_links il 
            ON il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
        WHERE sd.scout_id IS NOT NULL
    """,
    
    "2. Verificar si tienen lead_events": """
        SELECT 
            COUNT(DISTINCT sd.id) AS total_scouting_daily,
            COUNT(DISTINCT le.source_pk) AS con_lead_events,
            COUNT(DISTINCT sd.id) - COUNT(DISTINCT le.source_pk) AS sin_lead_events
        FROM public.module_ct_scouting_daily sd
        LEFT JOIN observational.lead_events le
            ON le.source_table = 'module_ct_scouting_daily'
            AND le.source_pk = sd.id::TEXT
        WHERE sd.scout_id IS NOT NULL
    """,
    
    "3. Verificar si tienen lead_ledger": """
        SELECT 
            COUNT(DISTINCT sd.id) AS total_scouting_daily,
            COUNT(DISTINCT ll.person_key) AS con_lead_ledger,
            COUNT(DISTINCT sd.id) - COUNT(DISTINCT ll.person_key) AS sin_lead_ledger
        FROM public.module_ct_scouting_daily sd
        LEFT JOIN canon.identity_links il 
            ON il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
        LEFT JOIN observational.lead_ledger ll 
            ON ll.person_key = il.person_key
        WHERE sd.scout_id IS NOT NULL
    """,
    
    "4. Muestra de casos sin atribución": """
        SELECT 
            sd.id,
            sd.scout_id,
            sd.driver_phone,
            sd.registration_date,
            CASE WHEN il.person_key IS NOT NULL THEN 'YES' ELSE 'NO' END AS tiene_identity_link,
            CASE WHEN le.id IS NOT NULL THEN 'YES' ELSE 'NO' END AS tiene_lead_event,
            CASE WHEN ll.person_key IS NOT NULL THEN 'YES' ELSE 'NO' END AS tiene_lead_ledger,
            ll.attributed_scout_id
        FROM public.module_ct_scouting_daily sd
        LEFT JOIN canon.identity_links il 
            ON il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
        LEFT JOIN observational.lead_events le
            ON le.source_table = 'module_ct_scouting_daily'
            AND le.source_pk = sd.id::TEXT
        LEFT JOIN observational.lead_ledger ll 
            ON ll.person_key = il.person_key
        WHERE sd.scout_id IS NOT NULL
        ORDER BY sd.registration_date DESC
        LIMIT 10
    """,
    
    "5. Verificar scout_id en lead_events": """
        SELECT 
            COUNT(*) AS total_lead_events,
            COUNT(*) FILTER (WHERE le.scout_id IS NOT NULL) AS con_scout_id_directo,
            COUNT(*) FILTER (WHERE le.payload_json->>'scout_id' IS NOT NULL) AS con_scout_id_en_payload,
            COUNT(*) FILTER (WHERE le.scout_id IS NULL AND (le.payload_json IS NULL OR le.payload_json->>'scout_id' IS NULL)) AS sin_scout_id
        FROM observational.lead_events le
        WHERE le.source_table = 'module_ct_scouting_daily'
    """
}

print("="*70)
print("INVESTIGACION: POR QUE SCOUTING_DAILY NO TIENE SCOUT ATRIBUIDO")
print("="*70)

with engine.connect() as conn:
    for title, query in queries.items():
        print(f"\n{title}")
        print("-"*70)
        try:
            result = conn.execute(text(query))
            rows = result.fetchall()
            columns = result.keys()
            
            if len(rows) > 0:
                if len(columns) > 3:
                    import pandas as pd
                    df = pd.DataFrame(rows, columns=columns)
                    print(df.to_string(index=False))
                else:
                    for row in rows:
                        print("  " + " | ".join([f"{col}: {val}" for col, val in zip(columns, row)]))
        except Exception as e:
            print(f"[ERROR] {str(e)[:200]}")

print("\n" + "="*70)





