#!/usr/bin/env python3
"""
Script para verificar el origin_tag de los eventos en lead_events
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date

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
        print("VERIFICACIÓN DE ORIGIN_TAG EN LEAD_EVENTS")
        print("=" * 70)
        
        # Verificar eventos de scouting_daily
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    source_table,
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE payload_json->>'origin_tag' = 'cabinet') AS cabinet_count,
                    COUNT(*) FILTER (WHERE payload_json->>'origin_tag' = 'scouting') AS scouting_count,
                    COUNT(*) FILTER (WHERE payload_json->>'origin_tag' IS NULL) AS null_count,
                    MAX(event_date) AS max_date
                FROM observational.lead_events
                WHERE source_table = 'module_ct_scouting_daily'
                GROUP BY source_table;
            """)
            
            row = cur.fetchone()
            if row:
                print(f"\nEventos de scouting_daily:")
                print(f"  Total: {row['total']}")
                print(f"  Con origin_tag='cabinet': {row['cabinet_count']}")
                print(f"  Con origin_tag='scouting': {row['scouting_count']}")
                print(f"  Con origin_tag=NULL: {row['null_count']}")
                print(f"  Fecha máxima: {row['max_date']}")
            
            # Verificar eventos recientes (últimos 30 días)
            cur.execute("""
                SELECT 
                    event_date,
                    COUNT(*) AS total,
                    COUNT(*) FILTER (WHERE payload_json->>'origin_tag' = 'cabinet') AS cabinet_count,
                    COUNT(*) FILTER (WHERE payload_json->>'origin_tag' = 'scouting') AS scouting_count
                FROM observational.lead_events
                WHERE source_table = 'module_ct_scouting_daily'
                    AND event_date >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY event_date
                ORDER BY event_date DESC
                LIMIT 10;
            """)
            
            rows = cur.fetchall()
            if rows:
                print(f"\nEventos recientes (últimos 10 días):")
                print(f"{'Fecha':<12} {'Total':<8} {'Cabinet':<8} {'Scouting':<8}")
                print("-" * 40)
                for r in rows:
                    print(f"{r['event_date']} {r['total']:<8} {r['cabinet_count']:<8} {r['scouting_count']:<8}")
            
            # Verificar si hay eventos con origin_tag='scouting' que deberían ser 'cabinet'
            cur.execute("""
                SELECT COUNT(*) AS count_to_fix
                FROM observational.lead_events
                WHERE source_table = 'module_ct_scouting_daily'
                    AND payload_json->>'origin_tag' = 'scouting';
            """)
            
            row = cur.fetchone()
            if row and row['count_to_fix'] > 0:
                print(f"\n⚠️  Hay {row['count_to_fix']} eventos con origin_tag='scouting' que deberían ser 'cabinet'")
                print("   Ejecuta: backend/scripts/sql/fix_existing_lead_events_origin_tag.sql")
            else:
                print("\n✓ Todos los eventos tienen el origin_tag correcto")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()



