#!/usr/bin/env python3
"""
Script para verificar la cobertura de v_conversion_metrics
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
        print("VERIFICACIÓN DE COBERTURA DE V_CONVERSION_METRICS")
        print("=" * 70)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Contar person_key únicos en lead_events (cabinet)
            cur.execute("""
                SELECT 
                    COUNT(DISTINCT le.person_key) AS unique_person_keys,
                    COUNT(*) AS total_events
                FROM observational.lead_events le
                WHERE le.source_table = 'module_ct_scouting_daily'
                    AND le.payload_json->>'origin_tag' = 'cabinet'
                    AND le.person_key IS NOT NULL
                    AND le.event_date >= '2025-12-10';
            """)
            
            row = cur.fetchone()
            if row:
                print(f"\nEventos en lead_events (desde 10/12):")
                print(f"  Person_keys únicos: {row['unique_person_keys']}")
                print(f"  Total eventos: {row['total_events']}")
            
            # Contar person_key únicos en v_conversion_metrics (cabinet)
            cur.execute("""
                SELECT 
                    COUNT(DISTINCT vcm.driver_id) AS unique_drivers,
                    COUNT(*) AS total_rows
                FROM observational.v_conversion_metrics vcm
                WHERE vcm.origin_tag = 'cabinet'
                    AND vcm.driver_id IS NOT NULL
                    AND vcm.lead_date >= '2025-12-10';
            """)
            
            row = cur.fetchone()
            if row:
                print(f"\nFilas en v_conversion_metrics (desde 10/12):")
                print(f"  Drivers únicos: {row['unique_drivers']}")
                print(f"  Total filas: {row['total_rows']}")
            
            # Verificar distribución de lead_date en v_conversion_metrics
            cur.execute("""
                SELECT 
                    lead_date,
                    COUNT(*) AS driver_count
                FROM observational.v_conversion_metrics
                WHERE origin_tag = 'cabinet'
                    AND driver_id IS NOT NULL
                    AND lead_date >= '2025-12-10'
                GROUP BY lead_date
                ORDER BY lead_date DESC;
            """)
            
            rows = cur.fetchall()
            if rows:
                print(f"\nDistribución de lead_date en v_conversion_metrics (desde 10/12):")
                print(f"{'Fecha':<12} {'Drivers':<8}")
                print("-" * 25)
                for r in rows:
                    print(f"{r['lead_date']} {r['driver_count']:<8}")
            
            # Verificar si hay eventos recientes que no aparecen en v_conversion_metrics
            cur.execute("""
                WITH recent_events AS (
                    SELECT DISTINCT
                        le.person_key,
                        MIN(le.event_date) AS first_event_date
                    FROM observational.lead_events le
                    WHERE le.source_table = 'module_ct_scouting_daily'
                        AND le.payload_json->>'origin_tag' = 'cabinet'
                        AND le.person_key IS NOT NULL
                        AND le.event_date >= '2025-12-10'
                    GROUP BY le.person_key
                ),
                drivers_from_events AS (
                    SELECT 
                        re.person_key,
                        re.first_event_date,
                        il.source_pk::text AS driver_id
                    FROM recent_events re
                    INNER JOIN canon.identity_links il
                        ON il.person_key = re.person_key
                        AND il.source_table = 'drivers'
                )
                SELECT 
                    COUNT(*) AS events_not_in_conversion
                FROM drivers_from_events dfe
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM observational.v_conversion_metrics vcm
                    WHERE vcm.driver_id::text = dfe.driver_id
                        AND vcm.origin_tag = 'cabinet'
                );
            """)
            
            row = cur.fetchone()
            if row:
                print(f"\nPerson_keys que NO aparecen en v_conversion_metrics: {row['events_not_in_conversion']}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()


