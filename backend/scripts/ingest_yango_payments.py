#!/usr/bin/env python3
"""
Script para ejecutar la ingesta de pagos Yango desde module_ct_cabinet_payments al ledger.

Este script ejecuta la función ops.ingest_yango_payments_snapshot() que:
- Lee desde ops.v_yango_payments_raw_current_aliases (que a su vez lee desde public.module_ct_cabinet_payments)
- Inserta nuevos registros en ops.yango_payment_ledger de forma idempotente
- Actualiza registros existentes cuando aparece información de identidad (driver_id/person_key)

Uso:
    python scripts/ingest_yango_payments.py

O programar en cron/task scheduler para ejecutar periódicamente (ej: cada hora).
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Configuración de base de datos (hardcoded para evitar dependencias del proyecto)
DB_CONFIG = {
    'host': '168.119.226.236',
    'port': 5432,
    'database': 'yego_integral',
    'user': 'yego_user',
    'password': '37>MNA&-35+'
}


def execute_ingest():
    """Ejecuta la función ops.ingest_yango_payments_snapshot()"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"[{datetime.now()}] Iniciando ingesta de pagos Yango...")
        
        # Ejecutar la función
        cur.execute("SELECT ops.ingest_yango_payments_snapshot()")
        rows_inserted = cur.fetchone()[0] or 0
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"[{datetime.now()}] Ingesta completada: {rows_inserted} filas insertadas")
        return rows_inserted
        
    except Exception as e:
        print(f"[{datetime.now()}] ERROR: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        sys.exit(1)


if __name__ == "__main__":
    rows_inserted = execute_ingest()
    sys.exit(0)


