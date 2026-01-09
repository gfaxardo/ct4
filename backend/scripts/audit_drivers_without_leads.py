"""
Script de Auditoría: Drivers sin Leads
========================================

Identifica drivers que están en el sistema de identidad pero NO tienen
un lead asociado (ni cabinet, ni scouting, ni migrations).

Estos drivers NO deberían estar en el sistema según el diseño:
- Los drivers solo deberían agregarse cuando matchean con un lead
- O cuando vienen de migrations (que es un tipo de lead)

Este script identifica:
1. Personas que solo tienen links de tipo "drivers"
2. Qué regla los creó (driver_direct, drivers_backfill, DRIVER_MATCH, etc.)
3. Si tienen lead_events asociados que deberían tener links
4. Estadísticas por regla de creación
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db import SessionLocal
from collections import defaultdict
import json
from datetime import datetime


def audit_drivers_without_leads():
    """
    Identifica drivers que están en identity_links pero NO tienen
    un lead asociado (cabinet, scouting, o migrations).
    """
    db = SessionLocal()
    
    try:
        # Query 1: Personas que solo tienen links de drivers (sin leads)
        query_only_drivers = text("""
            SELECT DISTINCT
                ir.person_key,
                ir.primary_phone,
                ir.primary_license,
                ir.primary_full_name,
                ir.confidence_level,
                ir.created_at
            FROM canon.identity_registry ir
            WHERE ir.person_key IN (
                -- Personas que tienen links de drivers
                SELECT DISTINCT person_key
                FROM canon.identity_links
                WHERE source_table = 'drivers'
            )
            AND ir.person_key NOT IN (
                -- Excluir personas que tienen links de leads
                SELECT DISTINCT person_key
                FROM canon.identity_links
                WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
            )
        """)
        
        result_only_drivers = db.execute(query_only_drivers)
        persons_only_drivers = result_only_drivers.fetchall()
        
        print(f"\n{'='*80}")
        print(f"AUDITORÍA: Drivers sin Leads")
        print(f"{'='*80}")
        print(f"\nTotal de personas que solo tienen links de drivers (sin leads): {len(persons_only_drivers)}")
        
        # Query 2: Links de drivers de estas personas, agrupados por regla
        if persons_only_drivers:
            person_keys = [str(p.person_key) for p in persons_only_drivers]
            person_keys_str = "', '".join(person_keys)
            
            query_links_by_rule = text(f"""
                SELECT 
                    il.match_rule,
                    COUNT(*) as count,
                    COUNT(DISTINCT il.person_key) as distinct_persons,
                    MIN(il.linked_at) as first_linked,
                    MAX(il.linked_at) as last_linked
                FROM canon.identity_links il
                WHERE il.source_table = 'drivers'
                AND il.person_key IN ('{person_keys_str}')
                GROUP BY il.match_rule
                ORDER BY count DESC
            """)
            
            result_by_rule = db.execute(query_links_by_rule)
            links_by_rule = result_by_rule.fetchall()
            
            print(f"\n{'='*80}")
            print(f"Desglose por Regla de Creación:")
            print(f"{'='*80}")
            print(f"{'Regla':<30} {'Links':<10} {'Personas':<10} {'Primer Link':<20} {'Último Link':<20}")
            print(f"{'-'*80}")
            
            for row in links_by_rule:
                print(f"{row.match_rule:<30} {row.count:<10} {row.distinct_persons:<10} {str(row.first_linked)[:19]:<20} {str(row.last_linked)[:19]:<20}")
            
            # Query 3: Verificar si estos drivers tienen lead_events asociados
            query_with_lead_events = text(f"""
                WITH drivers_without_leads AS (
                    SELECT DISTINCT il.source_pk as driver_id
                    FROM canon.identity_links il
                    WHERE il.source_table = 'drivers'
                    AND il.person_key IN ('{person_keys_str}')
                ),
                drivers_with_events AS (
                    SELECT DISTINCT
                        d.driver_id,
                        COUNT(DISTINCT le.id) as events_count,
                        COUNT(DISTINCT le.source_table) as source_tables_count,
                        STRING_AGG(DISTINCT le.source_table, ', ') as source_tables
                    FROM drivers_without_leads d
                    LEFT JOIN observational.lead_events le
                        ON (le.payload_json->>'driver_id')::text = d.driver_id
                    GROUP BY d.driver_id
                )
                SELECT 
                    COUNT(*) FILTER (WHERE events_count > 0) as drivers_with_events,
                    COUNT(*) FILTER (WHERE events_count = 0) as drivers_without_events,
                    COALESCE(SUM(events_count), 0) as total_events,
                    COUNT(*) as total_drivers
                FROM drivers_with_events
            """)
            
            result_events = db.execute(query_with_lead_events)
            events_stats = result_events.fetchone()
            
            print(f"\n{'='*80}")
            print(f"Análisis de Lead Events:")
            print(f"{'='*80}")
            print(f"Drivers CON lead_events: {events_stats.drivers_with_events}")
            print(f"Drivers SIN lead_events: {events_stats.drivers_without_events}")
            print(f"Total de eventos encontrados: {events_stats.total_events}")
            print(f"Total de drivers analizados: {events_stats.total_drivers}")
            
            # Query 4: Detalle de drivers con eventos pero sin links
            query_missing_links = text(f"""
                WITH drivers_without_leads AS (
                    SELECT DISTINCT 
                        il.person_key,
                        il.source_pk as driver_id,
                        il.match_rule,
                        il.linked_at
                    FROM canon.identity_links il
                    WHERE il.source_table = 'drivers'
                    AND il.person_key IN ('{person_keys_str}')
                ),
                drivers_with_events_detail AS (
                    SELECT 
                        d.driver_id,
                        d.person_key,
                        d.match_rule,
                        d.linked_at,
                        le.source_table as event_source_table,
                        le.event_date,
                        le.id as event_id
                    FROM drivers_without_leads d
                    INNER JOIN observational.lead_events le
                        ON (le.payload_json->>'driver_id')::text = d.driver_id
                    WHERE NOT EXISTS (
                        SELECT 1
                        FROM canon.identity_links il2
                        WHERE il2.person_key = d.person_key
                        AND il2.source_table = le.source_table
                    )
                )
                SELECT 
                    event_source_table,
                    COUNT(DISTINCT driver_id) as drivers_count,
                    COUNT(*) as events_count,
                    MIN(event_date) as earliest_event,
                    MAX(event_date) as latest_event
                FROM drivers_with_events_detail
                GROUP BY event_source_table
                ORDER BY drivers_count DESC
            """)
            
            result_missing = db.execute(query_missing_links)
            missing_links = result_missing.fetchall()
            
            if missing_links:
                print(f"\n{'='*80}")
                print(f"Drivers con Lead Events pero SIN Links Correspondientes:")
                print(f"{'='*80}")
                print(f"{'Source Table':<30} {'Drivers':<10} {'Events':<10} {'Earliest':<15} {'Latest':<15}")
                print(f"{'-'*80}")
                
                for row in missing_links:
                    print(f"{row.event_source_table:<30} {row.drivers_count:<10} {row.events_count:<10} {str(row.earliest_event)[:14]:<15} {str(row.latest_event)[:14]:<15}")
            
            # Query 5: Muestra de casos específicos
            query_samples = text(f"""
                WITH drivers_without_leads AS (
                    SELECT DISTINCT 
                        il.person_key,
                        il.source_pk as driver_id,
                        il.match_rule,
                        il.linked_at,
                        il.evidence
                    FROM canon.identity_links il
                    WHERE il.source_table = 'drivers'
                    AND il.person_key IN ('{person_keys_str}')
                    LIMIT 10
                )
                SELECT 
                    d.driver_id,
                    d.match_rule,
                    d.linked_at,
                    d.evidence,
                    ir.primary_phone,
                    ir.primary_license,
                    ir.primary_full_name,
                    (SELECT COUNT(*) 
                     FROM observational.lead_events le 
                     WHERE (le.payload_json->>'driver_id')::text = d.driver_id) as events_count
                FROM drivers_without_leads d
                JOIN canon.identity_registry ir ON ir.person_key = d.person_key
                ORDER BY d.linked_at DESC
            """)
            
            result_samples = db.execute(query_samples)
            samples = result_samples.fetchall()
            
            if samples:
                print(f"\n{'='*80}")
                print(f"Muestra de Casos (Top 10 más recientes):")
                print(f"{'='*80}")
                for idx, row in enumerate(samples, 1):
                    print(f"\n{idx}. Driver ID: {row.driver_id}")
                    print(f"   Regla: {row.match_rule}")
                    print(f"   Linked at: {row.linked_at}")
                    print(f"   Phone: {row.primary_phone or 'N/A'}")
                    print(f"   License: {row.primary_license or 'N/A'}")
                    print(f"   Name: {row.primary_full_name or 'N/A'}")
                    print(f"   Lead Events encontrados: {row.events_count}")
                    if row.evidence:
                        print(f"   Evidence: {json.dumps(row.evidence, indent=2)}")
        
        else:
            print("\n✅ No se encontraron drivers sin leads. El sistema está correcto.")
        
        print(f"\n{'='*80}")
        print(f"Auditoría completada: {datetime.now()}")
        print(f"{'='*80}\n")
        
    except Exception as e:
        print(f"\n❌ Error en auditoría: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    audit_drivers_without_leads()

