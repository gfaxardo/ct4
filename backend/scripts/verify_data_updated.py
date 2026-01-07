#!/usr/bin/env python3
"""
Script para verificar si los datos se actualizaron después del proceso
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
        print("VERIFICACIÓN DE DATOS ACTUALIZADOS")
        print("=" * 70)
        
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Verificar max lead_date en v_conversion_metrics
            cur.execute("""
                SELECT 
                    MAX(lead_date) AS max_lead_date,
                    COUNT(*) FILTER (WHERE lead_date >= '2025-12-15') AS since_15dec
                FROM observational.v_conversion_metrics
                WHERE origin_tag = 'cabinet'
                    AND driver_id IS NOT NULL;
            """)
            
            row = cur.fetchone()
            if row:
                print(f"\nv_conversion_metrics (cabinet):")
                print(f"  Max lead_date: {row['max_lead_date']}")
                print(f"  Desde 15/12: {row['since_15dec']}")
            
            # Verificar max lead_date en v_cabinet_financial_14d
            cur.execute("""
                SELECT 
                    MAX(lead_date) AS max_lead_date,
                    COUNT(*) FILTER (WHERE lead_date >= '2025-12-15') AS since_15dec
                FROM ops.v_cabinet_financial_14d;
            """)
            
            row = cur.fetchone()
            if row:
                print(f"\nv_cabinet_financial_14d:")
                print(f"  Max lead_date: {row['max_lead_date']}")
                print(f"  Desde 15/12: {row['since_15dec']}")
            
            # Verificar max lead_date en mv_cabinet_financial_14d (si existe)
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM pg_matviews 
                    WHERE schemaname = 'ops' 
                    AND matviewname = 'mv_cabinet_financial_14d'
                )
            """)
            mv_exists = cur.fetchone()[0]
            
            if mv_exists:
                cur.execute("""
                    SELECT 
                        MAX(lead_date) AS max_lead_date,
                        COUNT(*) FILTER (WHERE lead_date >= '2025-12-15') AS since_15dec
                    FROM ops.mv_cabinet_financial_14d;
                """)
                
                row = cur.fetchone()
                if row:
                    print(f"\nmv_cabinet_financial_14d (materializada):")
                    print(f"  Max lead_date: {row['max_lead_date']}")
                    print(f"  Desde 15/12: {row['since_15dec']}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()


