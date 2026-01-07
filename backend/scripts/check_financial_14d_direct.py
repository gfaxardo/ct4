#!/usr/bin/env python3
"""
Script para verificar directamente v_cabinet_financial_14d
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
        print("VERIFICACIÓN DIRECTA DE V_CABINET_FINANCIAL_14D")
        print("=" * 70)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Contar registros por fecha
            cur.execute("""
                SELECT 
                    lead_date,
                    COUNT(*) AS driver_count
                FROM ops.v_cabinet_financial_14d
                WHERE lead_date >= '2025-12-10'
                GROUP BY lead_date
                ORDER BY lead_date DESC
                LIMIT 20;
            """)
            
            rows = cur.fetchall()
            if rows:
                print(f"\nDistribución por lead_date (desde 10/12):")
                print(f"{'Fecha':<12} {'Drivers':<8}")
                print("-" * 25)
                for r in rows:
                    print(f"{r['lead_date']} {r['driver_count']:<8}")
            
            # Verificar el máximo lead_date
            cur.execute("""
                SELECT 
                    MAX(lead_date) AS max_lead_date,
                    COUNT(*) FILTER (WHERE lead_date >= '2025-12-15') AS since_15dec,
                    COUNT(*) FILTER (WHERE lead_date >= '2025-12-14') AS since_14dec,
                    COUNT(*) AS total
                FROM ops.v_cabinet_financial_14d;
            """)
            
            row = cur.fetchone()
            if row:
                print(f"\nResumen:")
                print(f"  Max lead_date: {row['max_lead_date']}")
                print(f"  Desde 15/12: {row['since_15dec']}")
                print(f"  Desde 14/12: {row['since_14dec']}")
                print(f"  Total: {row['total']}")
            
            # Verificar algunos registros recientes
            cur.execute("""
                SELECT 
                    driver_id,
                    driver_name,
                    lead_date,
                    total_trips_14d,
                    expected_total_yango,
                    amount_due_yango
                FROM ops.v_cabinet_financial_14d
                WHERE lead_date >= '2025-12-15'
                ORDER BY lead_date DESC, driver_id
                LIMIT 10;
            """)
            
            rows = cur.fetchall()
            if rows:
                print(f"\nRegistros recientes (desde 15/12):")
                print(f"{'Driver ID':<15} {'Nombre':<30} {'Lead Date':<12} {'Viajes':<8} {'Esperado':<10} {'Deuda':<10}")
                print("-" * 100)
                for r in rows:
                    driver_name = (r['driver_name'] or 'N/A')[:28]
                    print(f"{r['driver_id']:<15} {driver_name:<30} {r['lead_date']} {r['total_trips_14d']:<8} {r['expected_total_yango']:<10} {r['amount_due_yango']:<10}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()


