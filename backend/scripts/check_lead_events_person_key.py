#!/usr/bin/env python3
"""
Script para verificar si los eventos de lead_events tienen person_key asignado
"""

import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    'host': '168.119.226.236',
    'port': '5432',
    'database': 'yego_integral',
    'user': 'yego_user',
    'password': '37>MNA&-35+'
}

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    
    try:
        print("=" * 70)
        print("VERIFICACIÓN DE PERSON_KEY EN LEAD_EVENTS")
        print("=" * 70)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Verificar eventos de scouting_daily con y sin person_key
            cur.execute("""
                SELECT 
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE person_key IS NOT NULL) AS with_person_key,
                    COUNT(*) FILTER (WHERE person_key IS NULL) AS without_person_key,
                    COUNT(*) FILTER (WHERE payload_json->>'origin_tag' = 'cabinet') AS cabinet_count,
                    COUNT(*) FILTER (WHERE payload_json->>'origin_tag' = 'cabinet' AND person_key IS NOT NULL) AS cabinet_with_person_key
                FROM observational.lead_events
                WHERE source_table = 'module_ct_scouting_daily';
            """)
            
            row = cur.fetchone()
            if row:
                print(f"\nEventos de scouting_daily:")
                print(f"  Total: {row['total']}")
                print(f"  Con person_key: {row['with_person_key']}")
                print(f"  Sin person_key: {row['without_person_key']}")
                print(f"  Con origin_tag='cabinet': {row['cabinet_count']}")
                print(f"  Con origin_tag='cabinet' Y person_key: {row['cabinet_with_person_key']}")
            
            # Verificar distribución por fecha
            cur.execute("""
                SELECT 
                    event_date,
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE person_key IS NOT NULL) AS with_person_key,
                    COUNT(*) FILTER (WHERE payload_json->>'origin_tag' = 'cabinet') AS cabinet_count,
                    COUNT(*) FILTER (WHERE payload_json->>'origin_tag' = 'cabinet' AND person_key IS NOT NULL) AS cabinet_with_person_key
                FROM observational.lead_events
                WHERE source_table = 'module_ct_scouting_daily'
                    AND event_date >= '2025-12-10'
                GROUP BY event_date
                ORDER BY event_date DESC;
            """)
            
            rows = cur.fetchall()
            if rows:
                print(f"\nDistribución por fecha (desde 10/12):")
                print(f"{'Fecha':<12} {'Total':<8} {'Con PK':<8} {'Cabinet':<8} {'Cab+PK':<8}")
                print("-" * 50)
                for r in rows:
                    print(f"{r['event_date']} {r['total']:<8} {r['with_person_key']:<8} {r['cabinet_count']:<8} {r['cabinet_with_person_key']:<8}")
            
            # Verificar cuántos eventos tienen person_key pero no aparecen en v_conversion_metrics
            cur.execute("""
                SELECT 
                    COUNT(*) AS events_not_in_conversion
                FROM observational.lead_events le
                WHERE le.source_table = 'module_ct_scouting_daily'
                    AND le.payload_json->>'origin_tag' = 'cabinet'
                    AND le.person_key IS NOT NULL
                    AND NOT EXISTS (
                        SELECT 1
                        FROM observational.v_conversion_metrics vcm
                        WHERE vcm.driver_id = (
                            SELECT driver_id
                            FROM canon.identity_registry
                            WHERE person_key = le.person_key
                            LIMIT 1
                        )
                        AND vcm.origin_tag = 'cabinet'
                    );
            """)
            
            row = cur.fetchone()
            if row:
                print(f"\n⚠️  Eventos con person_key que NO aparecen en v_conversion_metrics: {row['events_not_in_conversion']}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()

