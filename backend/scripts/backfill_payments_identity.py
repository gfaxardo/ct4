#!/usr/bin/env python3
"""
Script para ejecutar backfill de identidad en pagos Yango sin driver_id.

Este script ejecuta ops.backfill_ledger_identity() que asigna driver_id y person_key
a pagos en ops.yango_payment_status_ledger que no tienen identidad asignada.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Configuración de base de datos
DB_CONFIG = {
    'host': '168.119.226.236',
    'port': 5432,
    'database': 'yego_integral',
    'user': 'yego_user',
    'password': '37>MNA&-35+'
}


def backfill_identity(dry_run=True):
    """Ejecuta el backfill de identidad"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"[{datetime.now()}] Verificando pagos sin identidad...")
        
        # Verificar cuántos pagos insertados hoy NO tienen driver_id
        cur.execute("""
            SELECT 
                COUNT(*) as total_inserted_today,
                COUNT(*) FILTER (WHERE driver_id IS NOT NULL) as with_driver_id,
                COUNT(*) FILTER (WHERE driver_id IS NULL) as without_driver_id
            FROM ops.yango_payment_status_ledger
            WHERE snapshot_at >= CURRENT_DATE
        """)
        stats = cur.fetchone()
        print(f"Pagos insertados hoy: {stats['total_inserted_today']}")
        print(f"  - Con driver_id: {stats['with_driver_id']}")
        print(f"  - Sin driver_id: {stats['without_driver_id']}")
        
        if stats['without_driver_id'] == 0:
            print("No hay pagos sin identidad. No se necesita backfill.")
            return
        
        # Verificar si existe la función
        cur.execute("""
            SELECT routine_name
            FROM information_schema.routines
            WHERE routine_schema = 'ops'
                AND routine_name = 'backfill_ledger_identity'
        """)
        func_exists = cur.fetchone()
        
        if not func_exists:
            print("ERROR: La función ops.backfill_ledger_identity no existe.")
            print("Ejecuta primero: backend/sql/ops/backfill_ledger_identity.sql")
            return
        
        # Ejecutar dry_run primero
        print(f"\n[{datetime.now()}] Ejecutando backfill (dry_run={dry_run})...")
        cur.execute("SELECT * FROM ops.backfill_ledger_identity(0.85, %s)", (dry_run,))
        results = cur.fetchall()
        
        if results:
            print(f"\nResultados del backfill:")
            for row in results:
                print(f"  - {row}")
        
        if not dry_run:
            conn.commit()
            print(f"\n[{datetime.now()}] Backfill completado exitosamente")
        else:
            print(f"\n[{datetime.now()}] DRY RUN completado. Para ejecutar realmente, usa dry_run=False")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"[{datetime.now()}] ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Backfill de identidad en pagos Yango')
    parser.add_argument('--execute', action='store_true', help='Ejecutar realmente (sin dry_run)')
    args = parser.parse_args()
    
    backfill_identity(dry_run=not args.execute)


