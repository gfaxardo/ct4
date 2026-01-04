#!/usr/bin/env python3
"""Script simple para verificar que la vista se creó correctamente."""
import psycopg2
import os

def get_db_config():
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"
    )
    url = database_url.replace("postgresql://", "")
    auth, rest = url.split("@")
    user, pwd = auth.split(":", 1)
    host_port, db = rest.rsplit("/", 1)
    host, port = host_port.split(":")
    return {"host": host, "port": port, "database": db, "user": user, "password": pwd}

def main():
    db_config = get_db_config()
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    
    print("="*80)
    print("Verificacion de vista: ops.v_payments_driver_matrix_cabinet")
    print("="*80)
    
    # Verificar que existe
    cur.execute("""
        SELECT COUNT(*) 
        FROM information_schema.views 
        WHERE table_schema = 'ops' 
        AND table_name = 'v_payments_driver_matrix_cabinet'
    """)
    exists = cur.fetchone()[0]
    print(f"\n[{'OK' if exists else 'ERROR'}] Vista existe: {exists > 0}")
    
    if exists:
        # Contar columnas
        cur.execute("""
            SELECT COUNT(*) 
            FROM information_schema.columns 
            WHERE table_schema = 'ops' 
            AND table_name = 'v_payments_driver_matrix_cabinet'
        """)
        col_count = cur.fetchone()[0]
        print(f"[OK] Total de columnas: {col_count}")
        
        # Verificar flags de inconsistencia
        cur.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'ops' 
            AND table_name = 'v_payments_driver_matrix_cabinet'
            AND column_name IN ('m5_without_m1_flag', 'm25_without_m5_flag', 'milestone_inconsistency_notes')
        """)
        flags = [r[0] for r in cur.fetchall()]
        print(f"[{'OK' if len(flags) == 3 else 'ERROR'}] Flags de inconsistencia: {flags}")
        
        # Contar filas
        try:
            cur.execute("SELECT COUNT(*) FROM ops.v_payments_driver_matrix_cabinet")
            total = cur.fetchone()[0]
            print(f"[OK] Total de filas: {total}")
            
            # Contar inconsistencias
            cur.execute("""
                SELECT 
                    COUNT(*) FILTER (WHERE m5_without_m1_flag = true) as m5_sin_m1,
                    COUNT(*) FILTER (WHERE m25_without_m5_flag = true) as m25_sin_m5
                FROM ops.v_payments_driver_matrix_cabinet
            """)
            row = cur.fetchone()
            print(f"[OK] Inconsistencias detectadas: M5 sin M1={row[0]}, M25 sin M5={row[1]}")
        except Exception as e:
            print(f"[WARNING] Error contando filas: {str(e)[:100]}")
    
    print("\n" + "="*80)
    conn.close()

if __name__ == "__main__":
    main()

