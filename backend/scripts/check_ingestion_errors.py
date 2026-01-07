#!/usr/bin/env python3
"""
Script para verificar los errores de las ingestion_runs fallidas
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
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Obtener las ingestion_runs fallidas
            cur.execute("""
                SELECT 
                    id,
                    started_at,
                    completed_at,
                    status,
                    error_message,
                    scope_date_from,
                    scope_date_to
                FROM ops.ingestion_runs
                WHERE status = 'FAILED'
                ORDER BY started_at DESC
                LIMIT 5;
            """)
            
            rows = cur.fetchall()
            
            print("=" * 70)
            print("INGESTION_RUNS FALLIDAS")
            print("=" * 70)
            
            for row in rows:
                print(f"\nRun ID: {row['id']}")
                print(f"Started: {row['started_at']}")
                print(f"Completed: {row['completed_at']}")
                print(f"Status: {row['status']}")
                print(f"Scope: {row['scope_date_from']} to {row['scope_date_to']}")
                print(f"Error: {row['error_message'][:500] if row['error_message'] else 'N/A'}")
                print("-" * 70)
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()


