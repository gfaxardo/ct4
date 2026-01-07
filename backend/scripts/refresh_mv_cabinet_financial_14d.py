#!/usr/bin/env python3
"""
Script para refrescar la vista materializada ops.mv_cabinet_financial_14d
"""

import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("[ERROR] ERROR: psycopg2 no está instalado.")
    print("   Instala con: pip install psycopg2-binary")
    sys.exit(1)

# Configuración de base de datos
DB_CONFIG = {
    'host': '168.119.226.236',
    'port': '5432',
    'database': 'yego_integral',
    'user': 'yego_user',
    'password': '37>MNA&-35+',
    'connect_timeout': 10
}

def refresh_materialized_view():
    """Refresca la vista materializada"""
    print("=" * 70)
    print("REFRESH: ops.mv_cabinet_financial_14d")
    print("=" * 70)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_session(autocommit=True)
        cur = conn.cursor()
        
        print("Refrescando vista materializada...")
        start_time = __import__('time').time()
        
        cur.execute("REFRESH MATERIALIZED VIEW ops.mv_cabinet_financial_14d;")
        
        elapsed = __import__('time').time() - start_time
        
        # Verificar que se refrescó correctamente
        cur.execute("SELECT COUNT(*) FROM ops.mv_cabinet_financial_14d;")
        count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        print(f"[OK] Vista materializada refrescada exitosamente!")
        print(f"     Tiempo: {elapsed:.2f} segundos")
        print(f"     Filas: {count}")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error al refrescar vista materializada: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = refresh_materialized_view()
    sys.exit(0 if success else 1)



