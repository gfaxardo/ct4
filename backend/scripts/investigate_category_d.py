#!/usr/bin/env python3
"""Investiga categoría D: Por qué no se propagaron scouts desde events a ledger"""
import sys
from pathlib import Path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))
from app.config import settings
from sqlalchemy import create_engine, text

engine = create_engine(settings.database_url)
conn = engine.connect()

print("INVESTIGACION: Categoria D - Scout en events pero no en ledger")
print("="*80)

# Contar categoría D
result = conn.execute(text("""
    SELECT COUNT(*) 
    FROM ops.v_persons_without_scout_categorized 
    WHERE categoria = 'D: Scout en events pero no en ledger'
"""))
cat_d_count = result.scalar()
print(f"\nTotal categoria D: {cat_d_count}")

# Verificar cuántos tienen scout único vs múltiples scouts
result = conn.execute(text("""
    WITH events_scout_counts AS (
        SELECT 
            le.person_key,
            COUNT(DISTINCT COALESCE(le.scout_id, (le.payload_json->>'scout_id')::INTEGER)) AS distinct_scout_count,
            MAX(COALESCE(le.scout_id, (le.payload_json->>'scout_id')::INTEGER)) AS scout_id
        FROM observational.lead_events le
        WHERE le.person_key IS NOT NULL
            AND (le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL))
            AND le.person_key IN (
                SELECT person_key FROM ops.v_persons_without_scout_categorized
                WHERE categoria = 'D: Scout en events pero no en ledger'
            )
        GROUP BY le.person_key
    )
    SELECT 
        COUNT(*) FILTER (WHERE distinct_scout_count = 1) AS with_single_scout,
        COUNT(*) FILTER (WHERE distinct_scout_count > 1) AS with_multiple_scouts
    FROM events_scout_counts
"""))
scout_counts = result.fetchone()
print(f"  Con scout unico (candidatos para backfill): {scout_counts[0]}")
print(f"  Con multiples scouts (conflictos): {scout_counts[1]}")

# Verificar si tienen lead_ledger y estado de attributed_scout_id
result = conn.execute(text("""
    SELECT 
        COUNT(DISTINCT cat.person_key) AS total_cat_d,
        COUNT(DISTINCT cat.person_key) FILTER (
            WHERE EXISTS (SELECT 1 FROM observational.lead_ledger ll WHERE ll.person_key = cat.person_key)
        ) AS with_ledger,
        COUNT(DISTINCT cat.person_key) FILTER (
            WHERE EXISTS (
                SELECT 1 FROM observational.lead_ledger ll
                WHERE ll.person_key = cat.person_key
                    AND ll.attributed_scout_id IS NULL
            )
        ) AS with_ledger_null_scout,
        COUNT(DISTINCT cat.person_key) FILTER (
            WHERE EXISTS (
                SELECT 1 FROM observational.lead_ledger ll
                WHERE ll.person_key = cat.person_key
                    AND ll.attributed_scout_id IS NOT NULL
            )
        ) AS with_ledger_with_scout,
        COUNT(DISTINCT cat.person_key) FILTER (
            WHERE NOT EXISTS (SELECT 1 FROM observational.lead_ledger ll WHERE ll.person_key = cat.person_key)
        ) AS without_ledger
    FROM ops.v_persons_without_scout_categorized cat
    WHERE cat.categoria = 'D: Scout en events pero no en ledger'
"""))
ledger_info = result.fetchone()
print(f"\nEstado de lead_ledger para Categoría D:")
print(f"  Total: {ledger_info[0]}")
print(f"  Con lead_ledger: {ledger_info[1]}")
print(f"  Con lead_ledger pero attributed_scout_id NULL: {ledger_info[2]}")
print(f"  Con lead_ledger y attributed_scout_id (debería ser 0): {ledger_info[3]}")
print(f"  Sin lead_ledger: {ledger_info[4]}")

# Analizar por qué no se propagaron (candidatos con scout único y ledger NULL)
result = conn.execute(text("""
    WITH candidates AS (
        SELECT 
            le.person_key,
            COUNT(DISTINCT COALESCE(le.scout_id, (le.payload_json->>'scout_id')::INTEGER)) AS distinct_scout_count,
            MAX(COALESCE(le.scout_id, (le.payload_json->>'scout_id')::INTEGER)) AS scout_id
        FROM observational.lead_events le
        WHERE le.person_key IS NOT NULL
            AND (le.scout_id IS NOT NULL OR (le.payload_json IS NOT NULL AND le.payload_json->>'scout_id' IS NOT NULL))
            AND le.person_key IN (
                SELECT person_key FROM ops.v_persons_without_scout_categorized
                WHERE categoria = 'D: Scout en events pero no en ledger'
            )
        GROUP BY le.person_key
        HAVING COUNT(DISTINCT COALESCE(le.scout_id, (le.payload_json->>'scout_id')::INTEGER)) = 1
    )
    SELECT 
        COUNT(*) AS candidates_with_single_scout,
        COUNT(*) FILTER (
            WHERE EXISTS (
                SELECT 1 FROM observational.lead_ledger ll
                WHERE ll.person_key = candidates.person_key
                    AND ll.attributed_scout_id IS NULL
            )
        ) AS candidates_with_ledger_null,
        COUNT(*) FILTER (
            WHERE NOT EXISTS (
                SELECT 1 FROM observational.lead_ledger ll
                WHERE ll.person_key = candidates.person_key
            )
        ) AS candidates_without_ledger
    FROM candidates
"""))
candidates_analysis = result.fetchone()
print(f"\nAnálisis de candidatos (scout único):")
print(f"  Total con scout único: {candidates_analysis[0]}")
print(f"  Con ledger y attributed_scout_id NULL (deberían actualizarse): {candidates_analysis[1]}")
print(f"  Sin ledger (no se pueden actualizar): {candidates_analysis[2]}")

# Muestra de ejemplos
print("\nEjemplos categoria D (top 10):")
result = conn.execute(text("""
    SELECT 
        cat.person_key,
        cat.scout_id_from_events,
        cat.events_with_scout_count,
        cat.lead_events_count,
        EXISTS (SELECT 1 FROM observational.lead_ledger ll WHERE ll.person_key = cat.person_key) AS has_ledger,
        (SELECT attributed_scout_id FROM observational.lead_ledger ll WHERE ll.person_key = cat.person_key LIMIT 1) AS current_ledger_scout,
        (SELECT attribution_rule FROM observational.lead_ledger ll WHERE ll.person_key = cat.person_key LIMIT 1) AS ledger_attribution_rule
    FROM ops.v_persons_without_scout_categorized cat
    WHERE cat.categoria = 'D: Scout en events pero no en ledger'
    ORDER BY cat.events_with_scout_count DESC, cat.lead_events_count DESC
    LIMIT 10
"""))
examples = result.fetchall()
for idx, ex in enumerate(examples, 1):
    print(f"  {idx}. Person: {ex[0]}")
    print(f"     Scout events: {ex[1]}, Events con scout: {ex[2]}, Total events: {ex[3]}")
    print(f"     Has ledger: {ex[4]}, Ledger scout: {ex[5]}, Attribution rule: {ex[6]}")

# Verificar si hay registros en audit table
result = conn.execute(text("""
    SELECT COUNT(*) 
    FROM ops.lead_ledger_scout_backfill_audit
    WHERE backfill_method = 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS'
"""))
audit_count = result.scalar()
print(f"\nRegistros en audit table (BACKFILL_SINGLE_SCOUT_FROM_EVENTS): {audit_count}")

conn.close()

