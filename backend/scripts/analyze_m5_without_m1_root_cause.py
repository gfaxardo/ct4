#!/usr/bin/env python3
"""
Análisis de causa raíz: M5 sin M1 en ops.v_payments_driver_matrix_cabinet
Arquitecto Senior de Datos - Investigación
"""
import psycopg2
import os
from pathlib import Path

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
    """Obtiene la definición completa de una vista usando pg_get_viewdef."""
    cur = conn.cursor()
    cur.execute(f"""
        SELECT pg_get_viewdef('{schema}.{view_name}', true) as definition
    """)
    result = cur.fetchone()
    return result[0] if result else None

def analyze_claims_view_structure(conn):
    """Analiza la estructura y fuentes de v_claims_payment_status_cabinet."""
    print("="*80)
    print("PASO 1: Analizando ops.v_claims_payment_status_cabinet")
    print("="*80)
    
    # Obtener definición de la vista
    definition = get_view_definition(conn, 'ops', 'v_claims_payment_status_cabinet')
    
    if definition:
        print("\n[OK] Definicion de la vista obtenida")
        print(f"\nLongitud: {len(definition)} caracteres")
        
        # Guardar definición completa
        output_file = Path("backend/sql/ops/_analysis_v_claims_payment_status_cabinet_def.sql")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"-- Definicion completa de ops.v_claims_payment_status_cabinet\n")
            f.write(f"-- Generado por analisis de causa raiz M5 sin M1\n\n")
            f.write(definition)
        print(f"[OK] Definicion guardada en: {output_file}")
        
        # Analizar fuentes mencionadas
        sources = []
        if 'FROM' in definition.upper():
            # Buscar tablas/vistas mencionadas
            import re
            from_pattern = r'FROM\s+([a-z_\.]+)'
            joins_pattern = r'JOIN\s+([a-z_\.]+)'
            
            for pattern in [from_pattern, joins_pattern]:
                matches = re.findall(pattern, definition, re.IGNORECASE)
                sources.extend(matches)
        
        print(f"\nFuentes identificadas en la definicion: {len(set(sources))}")
        for src in sorted(set(sources)):
            print(f"  - {src}")
        
        return definition
    else:
        print("[ERROR] No se pudo obtener la definicion")
        return None

def identify_m5_without_m1_drivers(conn):
    """Identifica los drivers con M5 sin M1 para análisis."""
    print("\n" + "="*80)
    print("PASO 2: Identificando drivers con M5 sin M1")
    print("="*80)
    
    cur = conn.cursor()
    
    # Obtener sample de drivers con M5 sin M1
    cur.execute("""
        SELECT 
            driver_id,
            person_key,
            m5_achieved_flag,
            m1_achieved_flag,
            m5_achieved_date,
            m1_achieved_date,
            lead_date,
            origin_tag
        FROM ops.v_payments_driver_matrix_cabinet
        WHERE m5_without_m1_flag = true
        LIMIT 10
    """)
    
    rows = cur.fetchall()
    print(f"\n[OK] Sample de 10 drivers con M5 sin M1:")
    print(f"{'driver_id':<40} {'m5_date':<12} {'lead_date':<12} {'origin_tag':<15}")
    print("-" * 80)
    for row in rows:
        driver_id, person_key, m5_flag, m1_flag, m5_date, m1_date, lead_date, origin_tag = row
        print(f"{str(driver_id):<40} {str(m5_date):<12} {str(lead_date):<12} {str(origin_tag):<15}")
    
    return [r[0] for r in rows]  # Retornar driver_ids

def trace_claims_for_drivers(conn, driver_ids):
    """Rastrea claims en v_claims_payment_status_cabinet para drivers específicos."""
    print("\n" + "="*80)
    print("PASO 3: Rastreando claims en ops.v_claims_payment_status_cabinet")
    print("="*80)
    
    if not driver_ids:
        print("[WARNING] No hay driver_ids para rastrear")
        return
    
    cur = conn.cursor()
    
    # Para cada driver, verificar qué milestones existen en claims
    placeholders = ','.join(['%s'] * len(driver_ids))
    cur.execute(f"""
        SELECT 
            driver_id,
            milestone_value,
            COUNT(*) as claim_count,
            MIN(lead_date) as first_lead_date,
            MAX(lead_date) as last_lead_date
        FROM ops.v_claims_payment_status_cabinet
        WHERE driver_id IN ({placeholders})
        GROUP BY driver_id, milestone_value
        ORDER BY driver_id, milestone_value
    """, driver_ids)
    
    rows = cur.fetchall()
    print(f"\n[OK] Claims encontrados para sample de drivers:")
    print(f"{'driver_id':<40} {'milestone':<10} {'count':<6} {'first_date':<12} {'last_date':<12}")
    print("-" * 100)
    
    current_driver = None
    for row in rows:
        driver_id, milestone, count, first_date, last_date = row
        if current_driver != driver_id:
            print()  # Nueva línea entre drivers
            current_driver = driver_id
        print(f"{str(driver_id):<40} {milestone:<10} {count:<6} {str(first_date):<12} {str(last_date):<12}")
    
    # Verificar si hay drivers sin ningún claim M1
    cur.execute(f"""
        SELECT 
            driver_id,
            COUNT(*) FILTER (WHERE milestone_value = 1) as m1_count,
            COUNT(*) FILTER (WHERE milestone_value = 5) as m5_count,
            COUNT(*) FILTER (WHERE milestone_value = 25) as m25_count
        FROM ops.v_claims_payment_status_cabinet
        WHERE driver_id IN ({placeholders})
        GROUP BY driver_id
        HAVING COUNT(*) FILTER (WHERE milestone_value = 1) = 0
        AND COUNT(*) FILTER (WHERE milestone_value = 5) > 0
    """, driver_ids)
    
    missing_m1 = cur.fetchall()
    print(f"\n[INFO] Drivers en sample sin M1 pero con M5: {len(missing_m1)}")

def analyze_upstream_sources(conn):
    """Analiza las fuentes upstream para entender dónde se generan los claims."""
    print("\n" + "="*80)
    print("PASO 4: Analizando fuentes upstream")
    print("="*80)
    
    cur = conn.cursor()
    
    # Obtener definición de v_claims_payment_status_cabinet
    definition = get_view_definition(conn, 'ops', 'v_claims_payment_status_cabinet')
    
    if not definition:
        print("[ERROR] No se pudo obtener definicion")
        return
    
    # Buscar referencias a tablas/vistas que generan claims
    # Buscar patrones comunes: payment_rules, leads, etc.
    print("\n[INFO] Buscando referencias a fuentes de claims...")
    
    # Verificar si hay tablas de reglas de pago
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'ops' 
        AND table_name LIKE '%payment%rule%'
        ORDER BY table_name
    """)
    rule_tables = cur.fetchall()
    if rule_tables:
        print(f"\n[OK] Tablas de reglas de pago encontradas: {[r[0] for r in rule_tables]}")
    
    # Verificar si hay tablas de leads
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema IN ('public', 'ops')
        AND (table_name LIKE '%lead%' OR table_name LIKE '%cabinet%')
        ORDER BY table_schema, table_name
    """)
    lead_tables = cur.fetchall()
    if lead_tables:
        print(f"\n[OK] Tablas de leads encontradas: {[f'{r[0]}' for r in lead_tables]}")

def generate_diagnostic_queries():
    """Genera queries mínimas para confirmar la causa raíz."""
    queries = """
-- ============================================================================
-- QUERIES DIAGNOSTICAS: Causa raiz M5 sin M1
-- ============================================================================

-- Q1: Verificar distribución de milestones en claims base
SELECT 
    milestone_value,
    COUNT(*) as total_claims,
    COUNT(DISTINCT driver_id) as unique_drivers
FROM ops.v_claims_payment_status_cabinet
WHERE milestone_value IN (1, 5, 25)
GROUP BY milestone_value
ORDER BY milestone_value;

-- Q2: Drivers con M5 pero sin M1 en claims base
SELECT 
    COUNT(DISTINCT driver_id) as drivers_m5_sin_m1
FROM (
    SELECT 
        driver_id,
        COUNT(*) FILTER (WHERE milestone_value = 1) as m1_count,
        COUNT(*) FILTER (WHERE milestone_value = 5) as m5_count
    FROM ops.v_claims_payment_status_cabinet
    GROUP BY driver_id
    HAVING COUNT(*) FILTER (WHERE milestone_value = 1) = 0
    AND COUNT(*) FILTER (WHERE milestone_value = 5) > 0
) subq;

-- Q3: Verificar si hay filtros por milestone_value en la vista
-- (Revisar manualmente la definición de v_claims_payment_status_cabinet)

-- Q4: Verificar reglas de negocio que generan claims
-- (Revisar ops.payment_rules o similar)

-- Q5: Verificar condiciones temporales/ventanas
SELECT 
    driver_id,
    milestone_value,
    lead_date,
    expected_amount,
    payment_status
FROM ops.v_claims_payment_status_cabinet
WHERE driver_id IN (
    SELECT driver_id 
    FROM ops.v_payments_driver_matrix_cabinet 
    WHERE m5_without_m1_flag = true 
    LIMIT 5
)
ORDER BY driver_id, milestone_value, lead_date;
"""
    
    output_file = Path("backend/sql/ops/_diagnostic_m5_without_m1_queries.sql")
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(queries)
    
    print(f"\n[OK] Queries diagnosticas generadas en: {output_file}")
    return queries

def main():
    """Función principal."""
    print("="*80)
    print("ANALISIS DE CAUSA RAIZ: M5 sin M1")
    print("Arquitecto Senior de Datos")
    print("="*80)
    
    db_config = get_db_config()
    conn = psycopg2.connect(**db_config)
    
    try:
        # Paso 1: Analizar definición de v_claims_payment_status_cabinet
        definition = analyze_claims_view_structure(conn)
        
        # Paso 2: Identificar drivers con M5 sin M1
        driver_ids = identify_m5_without_m1_drivers(conn)
        
        # Paso 3: Rastrear claims para esos drivers
        if driver_ids:
            trace_claims_for_drivers(conn, driver_ids)
        
        # Paso 4: Analizar fuentes upstream
        analyze_upstream_sources(conn)
        
        # Generar queries diagnósticas
        generate_diagnostic_queries()
        
        print("\n" + "="*80)
        print("ANALISIS COMPLETADO")
        print("="*80)
        print("\nSiguiente paso: Revisar la definicion guardada y ejecutar queries diagnosticas")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()








