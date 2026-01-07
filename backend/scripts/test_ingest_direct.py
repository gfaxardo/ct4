#!/usr/bin/env python3
"""
Script para probar la ingesta directamente y ver resultados detallados
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

def test_ingest():
    """Ejecuta la función y muestra resultados detallados"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        print(f"[{datetime.now()}] Verificando registros pendientes...")
        
        # Verificar cuántos registros deberían insertarse
        cur.execute("""
            SELECT COUNT(*) as should_insert
            FROM ops.v_yango_payments_raw_current_aliases rc
            WHERE NOT EXISTS (
                SELECT 1 
                FROM ops.yango_payment_status_ledger l 
                WHERE l.payment_key = rc.payment_key
                    AND l.state_hash = rc.state_hash
            )
        """)
        pending = cur.fetchone()
        print(f"Registros pendientes de ingesta: {pending['should_insert']}")
        
        if pending['should_insert'] > 0:
            # Verificar fechas
            cur.execute("""
                SELECT 
                    MIN(rc.pay_date) as min_date,
                    MAX(rc.pay_date) as max_date
                FROM ops.v_yango_payments_raw_current_aliases rc
                WHERE NOT EXISTS (
                    SELECT 1 
                    FROM ops.yango_payment_status_ledger l 
                    WHERE l.payment_key = rc.payment_key
                        AND l.state_hash = rc.state_hash
                )
            """)
            dates = cur.fetchone()
            print(f"Rango de fechas pendientes: {dates['min_date']} a {dates['max_date']}")
            
            # Ejecutar la función
            print(f"\n[{datetime.now()}] Ejecutando ingesta...")
            cur.execute("SELECT ops.ingest_yango_payments_snapshot()")
            result = cur.fetchone()
            rows_inserted = result['ingest_yango_payments_snapshot'] if result else 0
            
            conn.commit()
            print(f"[{datetime.now()}] Ingesta completada: {rows_inserted} filas insertadas")
        else:
            print("No hay registros pendientes de ingesta")
        
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
    test_ingest()

