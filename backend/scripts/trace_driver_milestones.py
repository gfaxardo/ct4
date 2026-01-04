#!/usr/bin/env python3
"""
Rastreo completo de milestones para un driver específico
"""
import psycopg2
import os
from datetime import datetime

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

def trace_driver(driver_id):
    """Rastrea un driver en todas las capas de la cadena."""
    db_config = get_db_config()
    conn = psycopg2.connect(**db_config)
    cur = conn.cursor()
    
    print("="*100)
    print(f"RASTREO COMPLETO: driver_id = {driver_id}")
    print("="*100)
    
    # 1. Verificar en v_payments_driver_matrix_cabinet (vista final)
    print("\n" + "="*100)
    print("1. ops.v_payments_driver_matrix_cabinet (VISTA FINAL)")
    print("="*100)
    cur.execute("""
        SELECT 
            driver_id,
            person_key,
            m1_achieved_flag,
            m1_achieved_date,
            m5_achieved_flag,
            m5_achieved_date,
            m25_achieved_flag,
            m25_achieved_date,
            m5_without_m1_flag,
            milestone_inconsistency_notes
        FROM ops.v_payments_driver_matrix_cabinet
        WHERE driver_id = %s
    """, (driver_id,))
    
    row = cur.fetchone()
    if row:
        print(f"  driver_id: {row[0]}")
        print(f"  person_key: {row[1]}")
        print(f"  M1: achieved={row[2]}, date={row[3]}")
        print(f"  M5: achieved={row[4]}, date={row[5]}")
        print(f"  M25: achieved={row[6]}, date={row[7]}")
        print(f"  m5_without_m1_flag: {row[8]}")
        print(f"  inconsistency_notes: {row[9]}")
    else:
        print("  [NO ENCONTRADO]")
        conn.close()
        return
    
    # 2. Verificar en v_claims_payment_status_cabinet (claims base)
    print("\n" + "="*100)
    print("2. ops.v_claims_payment_status_cabinet (CLAIMS BASE)")
    print("="*100)
    cur.execute("""
        SELECT 
            driver_id,
            person_key,
            milestone_value,
            lead_date,
            expected_amount,
            payment_status,
            paid_flag,
            days_overdue,
            reason_code
        FROM ops.v_claims_payment_status_cabinet
        WHERE driver_id = %s
        ORDER BY milestone_value, lead_date
    """, (driver_id,))
    
    rows = cur.fetchall()
    if rows:
        print(f"  Total filas: {len(rows)}")
        print(f"\n  {'milestone':<10} {'lead_date':<12} {'expected':<10} {'status':<20} {'paid':<6} {'overdue':<8} {'reason':<30}")
        print("  " + "-" * 100)
        for r in rows:
            print(f"  {r[2]:<10} {str(r[3]):<12} {str(r[4]):<10} {str(r[5]):<20} {str(r[6]):<6} {r[7]:<8} {str(r[8]):<30}")
        
        milestones = [r[2] for r in rows]
        print(f"\n  Milestones encontrados: {sorted(set(milestones))}")
        print(f"  M1 presente: {1 in milestones}")
        print(f"  M5 presente: {5 in milestones}")
    else:
        print("  [NO ENCONTRADO]")
    
    # 3. Verificar en mv_yango_receivable_payable_detail (materializada)
    print("\n" + "="*100)
    print("3. ops.mv_yango_receivable_payable_detail (MATERIALIZADA)")
    print("="*100)
    cur.execute("""
        SELECT 
            driver_id,
            person_key,
            milestone_value,
            lead_date,
            achieved_date,
            payable_date,
            lead_origin,
            amount,
            milestone_type,
            window_days,
            trips_in_window
        FROM ops.mv_yango_receivable_payable_detail
        WHERE driver_id = %s
        ORDER BY milestone_value, lead_date
    """, (driver_id,))
    
    rows = cur.fetchall()
    if rows:
        print(f"  Total filas: {len(rows)}")
        print(f"\n  {'milestone':<10} {'lead_date':<12} {'achieved':<12} {'payable':<12} {'origin':<15} {'amount':<10} {'type':<15} {'window':<8} {'trips':<6}")
        print("  " + "-" * 120)
        for r in rows:
            print(f"  {r[2]:<10} {str(r[3]):<12} {str(r[4]):<12} {str(r[5]):<12} {str(r[6]):<15} {str(r[7]):<10} {str(r[8]):<15} {r[9] if r[9] else 'NULL':<8} {r[10] if r[10] else 'NULL':<6}")
        
        milestones = [r[2] for r in rows]
        print(f"\n  Milestones encontrados: {sorted(set(milestones))}")
        print(f"  M1 presente: {1 in milestones}")
        print(f"  M5 presente: {5 in milestones}")
    else:
        print("  [NO ENCONTRADO]")
    
    # 4. Verificar en v_yango_receivable_payable_detail (vista)
    print("\n" + "="*100)
    print("4. ops.v_yango_receivable_payable_detail (VISTA)")
    print("="*100)
    cur.execute("""
        SELECT 
            driver_id,
            person_key,
            milestone_value,
            lead_date,
            achieved_date,
            payable_date,
            lead_origin,
            amount,
            milestone_type,
            window_days,
            trips_in_window
        FROM ops.v_yango_receivable_payable_detail
        WHERE driver_id = %s
        ORDER BY milestone_value, lead_date
    """, (driver_id,))
    
    rows = cur.fetchall()
    if rows:
        print(f"  Total filas: {len(rows)}")
        print(f"\n  {'milestone':<10} {'lead_date':<12} {'achieved':<12} {'payable':<12} {'origin':<15} {'amount':<10} {'type':<15} {'window':<8} {'trips':<6}")
        print("  " + "-" * 110)
        for r in rows:
            print(f"  {r[2]:<10} {str(r[3]):<12} {str(r[4]):<12} {str(r[5]):<12} {str(r[6]):<15} {str(r[7]):<10} {str(r[8]):<15} {str(r[9] if r[9] else 'NULL'):<8} {str(r[10] if r[10] else 'NULL'):<6}")
        
        milestones = [r[2] for r in rows]
        print(f"\n  Milestones encontrados: {sorted(set(milestones))}")
        print(f"  M1 presente: {1 in milestones}")
        print(f"  M5 presente: {5 in milestones}")
    else:
        print("  [NO ENCONTRADO]")
    
    # 5. Verificar en v_partner_payments_report_ui (fuente de generación)
    print("\n" + "="*100)
    print("5. ops.v_partner_payments_report_ui (FUENTE DE GENERACION)")
    print("="*100)
    cur.execute("""
        SELECT 
            driver_id,
            person_key,
            milestone_value,
            lead_date,
            achieved_date,
            payable_date,
            lead_origin,
            amount,
            milestone_type,
            is_payable,
            window_days,
            trips_in_window
        FROM ops.v_partner_payments_report_ui
        WHERE driver_id = %s
        ORDER BY milestone_value, lead_date
    """, (driver_id,))
    
    rows = cur.fetchall()
    if rows:
        print(f"  Total filas: {len(rows)}")
        print(f"\n  {'milestone':<10} {'lead_date':<12} {'achieved':<12} {'payable':<12} {'origin':<15} {'amount':<10} {'type':<15} {'is_payable':<10} {'window':<8} {'trips':<6}")
        print("  " + "-" * 120)
        for r in rows:
            print(f"  {r[2]:<10} {str(r[3]):<12} {str(r[4]):<12} {str(r[5]):<12} {str(r[6]):<15} {str(r[7]):<10} {str(r[8]):<15} {str(r[9]):<10} {str(r[10] if r[10] else 'NULL'):<8} {str(r[11] if r[11] else 'NULL'):<6}")
        
        milestones = [r[2] for r in rows]
        print(f"\n  Milestones encontrados: {sorted(set(milestones))}")
        print(f"  M1 presente: {1 in milestones}")
        print(f"  M5 presente: {5 in milestones}")
        
        # Verificar condiciones de elegibilidad
        m1_rows = [r for r in rows if r[2] == 1]
        m5_rows = [r for r in rows if r[2] == 5]
        
        if m1_rows:
            print(f"\n  [INFO] M1 existe en fuente de generacion ({len(m1_rows)} filas)")
            for r in m1_rows:
                print(f"    - is_payable: {r[9]}, amount: {r[7]}, window_days: {r[10]}, trips: {r[11]}")
        else:
            print(f"\n  [CONCLUSION] M1 NO existe en fuente de generacion")
            if m5_rows:
                print(f"  [COMPARACION] M5 existe con:")
                for r in m5_rows[:1]:  # Solo primera fila
                    print(f"    - is_payable: {r[9]}, amount: {r[7]}, window_days: {r[10]}, trips: {r[11]}")
    else:
        print("  [NO ENCONTRADO]")
    
    # 6. Resumen y conclusión
    print("\n" + "="*100)
    print("RESUMEN Y CONCLUSION")
    print("="*100)
    
    # Verificar en todas las capas
    cur.execute("""
        SELECT 
            'v_claims' as layer,
            COUNT(*) FILTER (WHERE milestone_value = 1) as m1_count,
            COUNT(*) FILTER (WHERE milestone_value = 5) as m5_count
        FROM ops.v_claims_payment_status_cabinet
        WHERE driver_id = %s
        UNION ALL
        SELECT 
            'mv_receivable' as layer,
            COUNT(*) FILTER (WHERE milestone_value = 1) as m1_count,
            COUNT(*) FILTER (WHERE milestone_value = 5) as m5_count
        FROM ops.mv_yango_receivable_payable_detail
        WHERE driver_id = %s
        UNION ALL
        SELECT 
            'v_receivable' as layer,
            COUNT(*) FILTER (WHERE milestone_value = 1) as m1_count,
            COUNT(*) FILTER (WHERE milestone_value = 5) as m5_count
        FROM ops.v_yango_receivable_payable_detail
        WHERE driver_id = %s
        UNION ALL
        SELECT 
            'v_partner_payments' as layer,
            COUNT(*) FILTER (WHERE milestone_value = 1) as m1_count,
            COUNT(*) FILTER (WHERE milestone_value = 5) as m5_count
        FROM ops.v_partner_payments_report_ui
        WHERE driver_id = %s
    """, (driver_id, driver_id, driver_id, driver_id))
    
    summary = cur.fetchall()
    print("\n  Presencia de milestones por capa:")
    print(f"  {'Capa':<25} {'M1':<6} {'M5':<6}")
    print("  " + "-" * 40)
    for layer, m1, m5 in summary:
        print(f"  {layer:<25} {m1:<6} {m5:<6}")
    
    # Conclusión
    m1_exists_anywhere = any(m1 > 0 for _, m1, _ in summary)
    m5_exists_anywhere = any(m5 > 0 for _, _, m5 in summary)
    
    # Verificar detalles de M1 en fuente de generación
    cur.execute("""
        SELECT 
            milestone_value,
            is_payable,
            amount,
            achieved_date,
            payable_date,
            window_days,
            trips_in_window
        FROM ops.v_partner_payments_report_ui
        WHERE driver_id = %s
        AND milestone_value = 1
    """, (driver_id,))
    
    m1_details = cur.fetchall()
    
    print("\n  RESPUESTAS:")
    print(f"  1. ¿Existe evidencia de M1 en cualquier tabla? {'SI' if m1_exists_anywhere else 'NO'}")
    
    if m1_exists_anywhere:
        print(f"\n  2. ¿Qué condición impide que M1 exista en las vistas finales?")
        if m1_details:
            m1_row = m1_details[0]
            print(f"     - M1 SÍ existe en ops.v_partner_payments_report_ui (fuente de generación)")
            print(f"     - Detalles de M1:")
            print(f"       * is_payable: {m1_row[1]}")
            print(f"       * amount: {m1_row[2]}")
            print(f"       * achieved_date: {m1_row[3]}")
            print(f"       * payable_date: {m1_row[4]}")
            print(f"       * window_days: {m1_row[5]}")
            print(f"       * trips_in_window: {m1_row[6]}")
            
            # Verificar si M1 pasa el filtro
            m1_in_final = any(m1 > 0 for layer, m1, _ in summary if layer in ['v_claims', 'mv_receivable', 'v_receivable'])
            
            if m1_row[1] == False:  # is_payable = False
                print(f"\n     - PERO es filtrado por la condición: is_payable = False")
                print(f"     - La vista ops.v_yango_receivable_payable_detail filtra con:")
                print(f"       WHERE is_payable = true AND amount > 0")
                print(f"     - Como M1 tiene is_payable = False, NO pasa el filtro")
                print(f"     - M5 tiene is_payable = True, por eso SÍ aparece")
            elif m1_in_final:
                print(f"\n     - M1 SÍ pasa el filtro (is_payable = True) y aparece en vistas finales")
                print(f"     - Este driver tiene M1, M5 y M25 correctamente")
            else:
                print(f"\n     - [ADVERTENCIA] M1 tiene is_payable = True pero no aparece en vistas finales")
                print(f"     - Revisar otros filtros o condiciones")
    elif not m1_exists_anywhere and m5_exists_anywhere:
        print(f"\n  2. ¿Qué condición impide que M1 exista?")
        print(f"     - M1 nunca se generó en la fuente de generación (ops.v_partner_payments_report_ui)")
        print(f"     - Posibles causas:")
        print(f"       a) Regla de negocio: M1 requiere condiciones que este driver no cumple")
        print(f"       b) Ventana temporal: M1 requiere un evento/lead anterior que no existe")
        print(f"       c) Elegibilidad: Driver alcanzó M5 directamente sin pasar por M1")
    
    conn.close()

if __name__ == "__main__":
    driver_id = 'b0084435635747669db9c78bdb4fc13d'
    trace_driver(driver_id)

