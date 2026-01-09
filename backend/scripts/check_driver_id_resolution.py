#!/usr/bin/env python3
"""
Script para verificar si los eventos tienen driver_id resuelto
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
        print("VERIFICACIÓN DE DRIVER_ID EN LEAD_EVENTS")
        print("=" * 70)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Verificar eventos con person_key pero sin driver_id resuelto
            cur.execute("""
                SELECT 
                    COUNT(*) AS total_with_person_key,
                    COUNT(*) FILTER (WHERE EXISTS (
                        SELECT 1
                        FROM canon.identity_links il
                        WHERE il.person_key = le.person_key
                            AND il.source_table = 'drivers'
                    )) AS with_driver_id,
                    COUNT(*) FILTER (WHERE NOT EXISTS (
                        SELECT 1
                        FROM canon.identity_links il
                        WHERE il.person_key = le.person_key
                            AND il.source_table = 'drivers'
                    )) AS without_driver_id
                FROM observational.lead_events le
                WHERE le.source_table = 'module_ct_scouting_daily'
                    AND le.payload_json->>'origin_tag' = 'cabinet'
                    AND le.person_key IS NOT NULL;
            """)
            
            row = cur.fetchone()
            if row:
                print(f"\nEventos con person_key:")
                print(f"  Total: {row['total_with_person_key']}")
                print(f"  Con driver_id resuelto: {row['with_driver_id']}")
                print(f"  Sin driver_id resuelto: {row['without_driver_id']}")
            
            # Verificar distribución por fecha
            cur.execute("""
                SELECT 
                    le.event_date,
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE EXISTS (
                        SELECT 1
                        FROM canon.identity_links il
                        WHERE il.person_key = le.person_key
                            AND il.source_table = 'drivers'
                    )) AS with_driver_id
                FROM observational.lead_events le
                WHERE le.source_table = 'module_ct_scouting_daily'
                    AND le.payload_json->>'origin_tag' = 'cabinet'
                    AND le.person_key IS NOT NULL
                    AND le.event_date >= '2025-12-10'
                GROUP BY le.event_date
                ORDER BY le.event_date DESC;
            """)
            
            rows = cur.fetchall()
            if rows:
                print(f"\nDistribución por fecha (desde 10/12):")
                print(f"{'Fecha':<12} {'Total':<8} {'Con driver_id':<12}")
                print("-" * 35)
                for r in rows:
                    print(f"{r['event_date']} {r['total']:<8} {r['with_driver_id']:<12}")
            
            # Verificar cuántos aparecen en v_conversion_metrics
            cur.execute("""
                SELECT 
                    COUNT(DISTINCT le.person_key) AS events_in_conversion_metrics
                FROM observational.lead_events le
                WHERE le.source_table = 'module_ct_scouting_daily'
                    AND le.payload_json->>'origin_tag' = 'cabinet'
                    AND le.person_key IS NOT NULL
                    AND EXISTS (
                        SELECT 1
                        FROM observational.v_conversion_metrics vcm
                        WHERE vcm.driver_id = (
                            SELECT il.source_pk::integer
                            FROM canon.identity_links il
                            WHERE il.person_key = le.person_key
                                AND il.source_table = 'drivers'
                            LIMIT 1
                        )
                        AND vcm.origin_tag = 'cabinet'
                    );
            """)
            
            row = cur.fetchone()
            if row:
                print(f"\nEventos que aparecen en v_conversion_metrics: {row['events_in_conversion_metrics']}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()



