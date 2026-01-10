#!/usr/bin/env python3
"""
Script para resolver Categoría D: Backfill mejorado de scout desde events a ledger
Investiga y actualiza personas con scout único en events pero sin scout en ledger
"""
import sys
from pathlib import Path
from datetime import datetime
import json as json_lib

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.config import settings
from sqlalchemy import create_engine, text

engine = create_engine(settings.database_url)
conn = engine.connect()

print("="*80)
print("RESOLUCIÓN CATEGORÍA D: Backfill mejorado de scout desde events a ledger")
print("="*80)
print(f"Fecha: {datetime.now().isoformat()}\n")

try:
    # PASO 1: Identificar candidatos con scout único que tienen ledger pero attributed_scout_id es NULL
    print("PASO 1: Identificando candidatos...")
    
    query_candidates = text("""
        WITH events_scout_counts AS (
            SELECT 
                le.person_key,
                COUNT(DISTINCT COALESCE(le.scout_id, (le.payload_json->>'scout_id')::INTEGER)) AS distinct_scout_count,
                MAX(COALESCE(le.scout_id, (le.payload_json->>'scout_id')::INTEGER)) AS scout_id,
                MIN(le.event_date) AS first_event_date,
                MAX(le.event_date) AS last_event_date,
                COUNT(*) AS total_events,
                array_agg(DISTINCT le.source_table) AS source_tables
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
            c.person_key,
            c.scout_id,
            c.first_event_date,
            c.last_event_date,
            c.total_events,
            c.source_tables,
            ll.attributed_scout_id AS current_attributed_scout_id,
            ll.attribution_rule AS current_attribution_rule,
            ll.confidence_level AS current_confidence_level,
            ll.evidence_json AS current_evidence_json
        FROM events_scout_counts c
        INNER JOIN observational.lead_ledger ll ON ll.person_key = c.person_key
        WHERE ll.attributed_scout_id IS NULL
        ORDER BY c.total_events DESC, c.first_event_date ASC
    """)
    
    result = conn.execute(query_candidates)
    candidates = result.fetchall()
    
    print(f"  Candidatos encontrados: {len(candidates)}")
    
    if len(candidates) == 0:
        print("\n  No hay candidatos para actualizar. Verificar por qué no se encontraron.")
        print("  Posibles razones:")
        print("    - Ya tienen attributed_scout_id (aunque la vista dice que no)")
        print("    - No tienen entrada en lead_ledger")
        print("    - Tienen múltiples scouts (conflictos)")
        conn.close()
        sys.exit(0)
    
    # PASO 2: Actualizar lead_ledger para cada candidato
    print(f"\nPASO 2: Actualizando {len(candidates)} registros en lead_ledger...")
    
    updated_count = 0
    audit_count = 0
    
    for idx, rec in enumerate(candidates, 1):
        person_key = rec[0]
        scout_id = rec[1]
        first_event_date = rec[2]
        last_event_date = rec[3]
        total_events = rec[4]
        source_tables = rec[5]
        current_attributed_scout_id = rec[6]
        current_attribution_rule = rec[7]
        current_confidence_level = rec[8]
        current_evidence_json = rec[9]
        
        # Actualizar lead_ledger usando SQL directo para manejar JSONB correctamente
        update_query = text("""
            UPDATE observational.lead_ledger
            SET 
                attributed_scout_id = :scout_id,
                attribution_rule = COALESCE(attribution_rule, 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS_IMPROVED'),
                confidence_level = CASE 
                    WHEN confidence_level::TEXT = 'HIGH' THEN confidence_level
                    ELSE 'HIGH'::confidencelevel
                END,
                evidence_json = COALESCE(evidence_json, '{}'::JSONB) || jsonb_build_object(
                    'backfill_method', 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS_IMPROVED',
                    'backfill_timestamp', NOW(),
                    'source_tables', :source_tables,
                    'total_events', :total_events,
                    'first_event_date', :first_event_date,
                    'last_event_date', :last_event_date
                ),
                updated_at = NOW()
            WHERE person_key = :person_key
                AND attributed_scout_id IS NULL
            RETURNING person_key
        """)
        
        result_update = conn.execute(update_query, {
            'scout_id': scout_id,
            'person_key': person_key,
            'source_tables': source_tables if source_tables else [],
            'total_events': total_events,
            'first_event_date': first_event_date,
            'last_event_date': last_event_date
        })
        
        if result_update.rowcount > 0:
            updated_count += 1
            
            # Registrar en auditoría
            import json as json_lib
            audit_query = text("""
                INSERT INTO ops.lead_ledger_scout_backfill_audit (
                    person_key,
                    old_attributed_scout_id,
                    new_attributed_scout_id,
                    attribution_rule_old,
                    attribution_rule_new,
                    attribution_confidence_old,
                    attribution_confidence_new,
                    evidence_json_old,
                    evidence_json_new,
                    backfill_method,
                    notes
                )
                VALUES (
                    :person_key,
                    :old_attributed_scout_id,
                    :new_attributed_scout_id,
                    :attribution_rule_old,
                    :attribution_rule_new,
                    :attribution_confidence_old,
                    :attribution_confidence_new,
                    :evidence_json_old,
                    :evidence_json_new,
                    :backfill_method,
                    :notes
                )
            """)
            
            # Construir evidence_json_new para auditoría
            evidence_json_new = {
                'backfill_method': 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS_IMPROVED',
                'backfill_timestamp': datetime.now().isoformat(),
                'source_tables': source_tables if source_tables else [],
                'total_events': total_events,
                'first_event_date': first_event_date.isoformat() if first_event_date else None,
                'last_event_date': last_event_date.isoformat() if last_event_date else None
            }
            
            conn.execute(audit_query, {
                'person_key': person_key,
                'old_attributed_scout_id': current_attributed_scout_id,
                'new_attributed_scout_id': scout_id,
                'attribution_rule_old': current_attribution_rule,
                'attribution_rule_new': 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS_IMPROVED',
                'attribution_confidence_old': str(current_confidence_level) if current_confidence_level else None,
                'attribution_confidence_new': 'HIGH',
                'evidence_json_old': json_lib.dumps(current_evidence_json) if current_evidence_json else None,
                'evidence_json_new': json_lib.dumps(evidence_json_new),
                'backfill_method': 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS_IMPROVED',
                'notes': f'Backfill mejorado: {total_events} eventos, scout_id={scout_id}'
            })
            
            audit_count += 1
            
            if idx % 10 == 0:
                conn.commit()
                print(f"  Procesados {idx}/{len(candidates)}...")
    
    conn.commit()
    
    print(f"\nPASO 3: Resumen")
    print(f"  Registros actualizados en lead_ledger: {updated_count}")
    print(f"  Registros en auditoría: {audit_count}")
    
    # PASO 4: Verificar resultado
    print(f"\nPASO 4: Verificando resultado...")
    
    result_verify = conn.execute(text("""
        SELECT COUNT(*) 
        FROM ops.v_persons_without_scout_categorized
        WHERE categoria = 'D: Scout en events pero no en ledger'
    """))
    remaining_cat_d = result_verify.scalar()
    
    print(f"  Categoría D restante: {remaining_cat_d}")
    print(f"  Reducción: {len(candidates) - remaining_cat_d} personas")
    
    if remaining_cat_d > 0:
        print(f"\n  Nota: {remaining_cat_d} personas aún en Categoría D.")
        print(f"  Posibles razones:")
        print(f"    - No tienen entrada en lead_ledger")
        print(f"    - Tienen múltiples scouts (conflictos)")
        print(f"    - Ya tienen attributed_scout_id diferente")
    
    print("\n" + "="*80)
    print("RESOLUCIÓN COMPLETADA")
    print("="*80)
    
except Exception as e:
    print(f"\nERROR: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    conn.close()

