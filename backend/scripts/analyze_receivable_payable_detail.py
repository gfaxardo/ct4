#!/usr/bin/env python3
"""
Análisis profundo de ops.mv_yango_receivable_payable_detail
Para entender por qué M1 no se genera para drivers con M5
"""
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

def get_view_definition(conn, schema, view_name):
    """Obtiene la definición completa de una vista/materializada."""
    cur = conn.cursor()
    # Intentar como vista primero
    cur.execute(f"""
        SELECT pg_get_viewdef('{schema}.{view_name}', true) as definition
    """)
    result = cur.fetchone()
    if result and result[0]:
        return result[0]
    
    # Si no es vista, intentar como materializada
    cur.execute(f"""
        SELECT definition 
        FROM pg_matviews 
        WHERE schemaname = '{schema}' AND matviewname = '{view_name}'
    """)
    result = cur.fetchone()
    return result[0] if result else None

def analyze_receivable_payable_detail(conn):
    """Analiza la vista/materializada que genera los claims."""
    print("="*80)
    print("ANALISIS: ops.mv_yango_receivable_payable_detail")
    print("="*80)
    
    # Obtener definición
    definition = get_view_definition(conn, 'ops', 'mv_yango_receivable_payable_detail')
    
    if definition:
        print("\n[OK] Definicion obtenida")
        print(f"Longitud: {len(definition)} caracteres")
        
        # Guardar definición
        with open("backend/sql/ops/_analysis_mv_receivable_payable_detail_def.sql", 'w', encoding='utf-8') as f:
            f.write(f"-- Definicion completa de ops.mv_yango_receivable_payable_detail\n")
            f.write(f"-- Generado por analisis de causa raiz M5 sin M1\n\n")
            f.write(definition)
        print("[OK] Definicion guardada")
        
        # Analizar estructura
        if 'milestone_value' in definition.lower():
            print("\n[INFO] La vista contiene milestone_value")
        
        if 'lead_origin' in definition.lower():
            print("[INFO] La vista contiene lead_origin")
        
        # Buscar filtros por milestone
        import re
        milestone_filters = re.findall(r'milestone[_\w]*\s*[=<>!]+\s*[15]', definition, re.IGNORECASE)
        if milestone_filters:
            print(f"\n[INFO] Filtros por milestone encontrados: {milestone_filters}")
        else:
            print("\n[INFO] No se encontraron filtros explícitos por milestone_value")
        
        return definition
    else:
        print("[ERROR] No se pudo obtener la definicion")
        return None

def check_data_in_receivable_payable(conn, driver_ids):
    """Verifica qué milestones existen en mv_yango_receivable_payable_detail para drivers específicos."""
    print("\n" + "="*80)
    print("VERIFICACION: Datos en ops.mv_yango_receivable_payable_detail")
    print("="*80)
    
    if not driver_ids:
        print("[WARNING] No hay driver_ids para verificar")
        return
    
    cur = conn.cursor()
    
    # Verificar milestones para estos drivers
    placeholders = ','.join(['%s'] * len(driver_ids))
    cur.execute(f"""
        SELECT 
            driver_id,
            milestone_value,
            lead_origin,
            COUNT(*) as record_count,
            MIN(lead_date) as first_lead_date,
            MAX(lead_date) as last_lead_date
        FROM ops.mv_yango_receivable_payable_detail
        WHERE driver_id IN ({placeholders})
        AND lead_origin = 'cabinet'
        AND milestone_value IN (1, 5, 25)
        GROUP BY driver_id, milestone_value, lead_origin
        ORDER BY driver_id, milestone_value
    """, driver_ids)
    
    rows = cur.fetchall()
    print(f"\n[OK] Datos encontrados en mv_yango_receivable_payable_detail:")
    print(f"{'driver_id':<40} {'milestone':<10} {'lead_origin':<15} {'count':<6} {'first_date':<12}")
    print("-" * 100)
    
    current_driver = None
    for row in rows:
        driver_id, milestone, origin, count, first_date, last_date = row
        if current_driver != driver_id:
            print()  # Nueva línea entre drivers
            current_driver = driver_id
        print(f"{str(driver_id):<40} {milestone:<10} {str(origin):<15} {count:<6} {str(first_date):<12}")
    
    # Verificar drivers sin M1 en la fuente
    cur.execute(f"""
        SELECT 
            driver_id,
            COUNT(*) FILTER (WHERE milestone_value = 1) as m1_count,
            COUNT(*) FILTER (WHERE milestone_value = 5) as m5_count,
            COUNT(*) FILTER (WHERE milestone_value = 25) as m25_count
        FROM ops.mv_yango_receivable_payable_detail
        WHERE driver_id IN ({placeholders})
        AND lead_origin = 'cabinet'
        AND milestone_value IN (1, 5, 25)
        GROUP BY driver_id
        HAVING COUNT(*) FILTER (WHERE milestone_value = 1) = 0
        AND COUNT(*) FILTER (WHERE milestone_value = 5) > 0
    """, driver_ids)
    
    missing_m1 = cur.fetchall()
    print(f"\n[INFO] Drivers sin M1 en mv_yango_receivable_payable_detail: {len(missing_m1)}")
    
    if missing_m1:
        print("\n[CONCLUSION] M1 NO existe en la fuente upstream para estos drivers")
        print("La causa raiz esta en como se genera mv_yango_receivable_payable_detail")

def check_lead_dates_pattern(conn):
    """Verifica si hay un patrón temporal que explique M5 sin M1."""
    print("\n" + "="*80)
    print("ANALISIS TEMPORAL: Patrones de lead_date")
    print("="*80)
    
    cur = conn.cursor()
    
    # Comparar lead_dates entre M1 y M5 para drivers que tienen ambos
    cur.execute("""
        WITH m1_leads AS (
            SELECT driver_id, MIN(lead_date) as m1_lead_date
            FROM ops.mv_yango_receivable_payable_detail
            WHERE lead_origin = 'cabinet'
            AND milestone_value = 1
            GROUP BY driver_id
        ),
        m5_leads AS (
            SELECT driver_id, MIN(lead_date) as m5_lead_date
            FROM ops.mv_yango_receivable_payable_detail
            WHERE lead_origin = 'cabinet'
            AND milestone_value = 5
            GROUP BY driver_id
        )
        SELECT 
            m5.driver_id,
            m1.m1_lead_date,
            m5.m5_lead_date,
            (m5.m5_lead_date - m1.m1_lead_date) as days_between
        FROM m5_leads m5
        LEFT JOIN m1_leads m1 ON m1.driver_id = m5.driver_id
        WHERE m1.driver_id IS NOT NULL
        ORDER BY days_between
        LIMIT 10
    """)
    
    rows = cur.fetchall()
    print("\n[OK] Drivers con AMBOS M1 y M5 (sample):")
    print(f"{'driver_id':<40} {'M1_date':<12} {'M5_date':<12} {'days_diff':<10}")
    print("-" * 80)
    for row in rows:
        driver_id, m1_date, m5_date, days = row
        print(f"{str(driver_id):<40} {str(m1_date):<12} {str(m5_date):<12} {days if days else 'N/A':<10}")
    
    # Verificar si M5 sin M1 tienen lead_dates muy recientes
    cur.execute("""
        SELECT 
            driver_id,
            MIN(lead_date) as m5_lead_date,
            CURRENT_DATE - MIN(lead_date) as days_since_m5
        FROM ops.mv_yango_receivable_payable_detail
        WHERE lead_origin = 'cabinet'
        AND milestone_value = 5
        AND driver_id IN (
            SELECT driver_id 
            FROM ops.mv_yango_receivable_payable_detail
            WHERE lead_origin = 'cabinet'
            AND milestone_value IN (1, 5)
            GROUP BY driver_id
            HAVING COUNT(*) FILTER (WHERE milestone_value = 1) = 0
            AND COUNT(*) FILTER (WHERE milestone_value = 5) > 0
        )
        GROUP BY driver_id
        ORDER BY m5_lead_date DESC
        LIMIT 10
    """)
    
    rows = cur.fetchall()
    print("\n[OK] Drivers con M5 sin M1 - fechas M5:")
    print(f"{'driver_id':<40} {'M5_date':<12} {'days_ago':<10}")
    print("-" * 70)
    for row in rows:
        driver_id, m5_date, days_ago = row
        print(f"{str(driver_id):<40} {str(m5_date):<12} {days_ago:<10}")

def main():
    """Función principal."""
    print("="*80)
    print("ANALISIS PROFUNDO: Causa raiz M5 sin M1")
    print("="*80)
    
    db_config = get_db_config()
    conn = psycopg2.connect(**db_config)
    
    try:
        # Obtener sample de drivers con M5 sin M1
        cur = conn.cursor()
        cur.execute("""
            SELECT driver_id 
            FROM ops.v_payments_driver_matrix_cabinet
            WHERE m5_without_m1_flag = true
            LIMIT 10
        """)
        driver_ids = [r[0] for r in cur.fetchall()]
        
        # Analizar la vista/materializada upstream
        definition = analyze_receivable_payable_detail(conn)
        
        # Verificar datos en la fuente
        check_data_in_receivable_payable(conn, driver_ids)
        
        # Analizar patrones temporales
        check_lead_dates_pattern(conn)
        
        print("\n" + "="*80)
        print("ANALISIS COMPLETADO")
        print("="*80)
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()







