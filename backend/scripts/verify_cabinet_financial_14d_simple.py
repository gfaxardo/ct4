#!/usr/bin/env python3
"""
Script simplificado para verificar la vista ops.v_cabinet_financial_14d
Ejecuta solo los checks principales sin timeout
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

def execute_query(conn, query, description):
    """Ejecuta una query y muestra resultados"""
    print(f"\n{description}")
    print("=" * 70)
    try:
        cur = conn.cursor()
        cur.execute(query)
        
        # Obtener columnas
        columns = [desc[0] for desc in cur.description]
        
        # Mostrar resultados
        rows = cur.fetchall()
        if rows:
            # Imprimir encabezados
            print(" | ".join(str(col) for col in columns))
            print("-" * 70)
            # Imprimir filas (limitado a 10)
            for row in rows[:10]:
                print(" | ".join(str(val) if val is not None else "NULL" for val in row))
            if len(rows) > 10:
                print(f"... y {len(rows) - 10} filas más")
        else:
            print("(Sin resultados)")
        
        cur.close()
        return rows
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return None

def main():
    print("=" * 70)
    print("VERIFICACION: ops.v_cabinet_financial_14d")
    print("=" * 70)
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_session(autocommit=True)
        
        # CHECK 1: Resumen ejecutivo
        query1 = """
        SELECT 
            COUNT(*) AS total_drivers_cabinet,
            COUNT(CASE WHEN expected_total_yango > 0 THEN 1 END) AS drivers_con_deuda_esperada,
            COUNT(CASE WHEN amount_due_yango > 0 THEN 1 END) AS drivers_con_deuda_pendiente,
            SUM(expected_total_yango) AS total_esperado_yango,
            SUM(total_paid_yango) AS total_pagado_yango,
            SUM(amount_due_yango) AS total_deuda_yango,
            CASE 
                WHEN SUM(expected_total_yango) > 0 
                THEN ROUND((SUM(total_paid_yango) / SUM(expected_total_yango)) * 100, 2)
                ELSE 0
            END AS porcentaje_cobranza
        FROM ops.v_cabinet_financial_14d;
        """
        execute_query(conn, query1, "RESUMEN EJECUTIVO")
        
        # CHECK 2: Drivers con viajes >= hito sin claim
        query2 = """
        SELECT 
            COUNT(*) AS drivers_affected,
            SUM(CASE WHEN reached_m1_14d = true AND claim_m1_exists = false THEN 1 ELSE 0 END) AS m1_without_claim,
            SUM(CASE WHEN reached_m5_14d = true AND claim_m5_exists = false THEN 1 ELSE 0 END) AS m5_without_claim,
            SUM(CASE WHEN reached_m25_14d = true AND claim_m25_exists = false THEN 1 ELSE 0 END) AS m25_without_claim
        FROM ops.v_cabinet_financial_14d
        WHERE (reached_m1_14d = true AND claim_m1_exists = false)
            OR (reached_m5_14d = true AND claim_m5_exists = false)
            OR (reached_m25_14d = true AND claim_m25_exists = false);
        """
        execute_query(conn, query2, "CHECK 1: Drivers con viajes >= hito sin claim")
        
        # CHECK 3: Total esperado vs total pagado por milestone
        query3 = """
        SELECT 
            'M1' AS milestone,
            COUNT(CASE WHEN reached_m1_14d = true THEN 1 END) AS drivers_reached,
            COUNT(CASE WHEN claim_m1_exists = true THEN 1 END) AS drivers_with_claim,
            COUNT(CASE WHEN claim_m1_paid = true THEN 1 END) AS drivers_paid,
            SUM(expected_amount_m1) AS total_expected,
            SUM(paid_amount_m1) AS total_paid,
            SUM(expected_amount_m1 - paid_amount_m1) AS total_due
        FROM ops.v_cabinet_financial_14d
        WHERE reached_m1_14d = true
        UNION ALL
        SELECT 
            'M5' AS milestone,
            COUNT(CASE WHEN reached_m5_14d = true THEN 1 END),
            COUNT(CASE WHEN claim_m5_exists = true THEN 1 END),
            COUNT(CASE WHEN claim_m5_paid = true THEN 1 END),
            SUM(expected_amount_m5),
            SUM(paid_amount_m5),
            SUM(expected_amount_m5 - paid_amount_m5)
        FROM ops.v_cabinet_financial_14d
        WHERE reached_m5_14d = true
        UNION ALL
        SELECT 
            'M25' AS milestone,
            COUNT(CASE WHEN reached_m25_14d = true THEN 1 END),
            COUNT(CASE WHEN claim_m25_exists = true THEN 1 END),
            COUNT(CASE WHEN claim_m25_paid = true THEN 1 END),
            SUM(expected_amount_m25),
            SUM(paid_amount_m25),
            SUM(expected_amount_m25 - paid_amount_m25)
        FROM ops.v_cabinet_financial_14d
        WHERE reached_m25_14d = true;
        """
        execute_query(conn, query3, "CHECK 2: Total esperado vs total pagado por milestone")
        
        # CHECK 4: Top 10 drivers con mayor deuda
        query4 = """
        SELECT 
            driver_id,
            lead_date,
            total_trips_14d,
            expected_total_yango,
            total_paid_yango,
            amount_due_yango
        FROM ops.v_cabinet_financial_14d
        WHERE amount_due_yango > 0
        ORDER BY amount_due_yango DESC
        LIMIT 10;
        """
        execute_query(conn, query4, "CHECK 3: Top 10 drivers con mayor deuda pendiente")
        
        conn.close()
        
        print("\n" + "=" * 70)
        print("[OK] Verificacion completada!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()




