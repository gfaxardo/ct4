#!/usr/bin/env python3
"""
Script para diagnosticar por qué los datos solo llegan hasta el 14/12/2025
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date

DB_CONFIG = {
    'host': '168.119.226.236',
    'port': '5432',
    'database': 'yego_integral',
    'user': 'yego_user',
    'password': '37>MNA&-35+'
}

def print_section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)

def execute_query(conn, query, title):
    """Ejecuta una consulta y muestra los resultados"""
    print(f"\n{title}:")
    print("-" * 70)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            rows = cur.fetchall()
            if rows:
                # Imprimir encabezados
                if rows:
                    headers = list(rows[0].keys())
                    print(" | ".join(f"{h:20}" for h in headers))
                    print("-" * 70)
                    # Imprimir filas
                    for row in rows:
                        values = [str(row[h]) if row[h] is not None else "NULL" for h in headers]
                        print(" | ".join(f"{v[:20]:20}" for v in values))
            else:
                print("(Sin resultados)")
    except Exception as e:
        print(f"[ERROR] {e}")

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    
    try:
        print_section("DIAGNÓSTICO: ¿Por qué los datos solo llegan hasta el 14/12/2025?")
        
        # 1. Fechas más recientes en tablas fuente
        query1 = """
        SELECT 
            'module_ct_scouting_daily' AS source,
            MAX(registration_date::date) AS max_date,
            COUNT(*) FILTER (WHERE registration_date::date >= '2025-12-14') AS records_since_14dec
        FROM public.module_ct_scouting_daily;
        """
        execute_query(conn, query1, "1. TABLAS FUENTE - scouting_daily")
        
        # 2. Fechas más recientes en lead_events (cabinet)
        query2 = """
        SELECT 
            MAX(event_date) AS max_date,
            COUNT(*) FILTER (WHERE event_date >= '2025-12-14') AS records_since_14dec,
            COUNT(*) FILTER (WHERE payload_json->>'origin_tag' = 'cabinet' AND event_date >= '2025-12-14') AS cabinet_records_since_14dec
        FROM observational.lead_events
        WHERE payload_json->>'origin_tag' = 'cabinet';
        """
        execute_query(conn, query2, "2. LEAD_EVENTS (cabinet)")
        
        # 3. Fechas más recientes en v_conversion_metrics (cabinet)
        query3 = """
        SELECT 
            MAX(lead_date) AS max_date,
            COUNT(*) FILTER (WHERE lead_date >= '2025-12-14') AS records_since_14dec
        FROM observational.v_conversion_metrics
        WHERE origin_tag = 'cabinet'
            AND driver_id IS NOT NULL;
        """
        execute_query(conn, query3, "3. CONVERSION_METRICS (cabinet)")
        
        # 4. Fechas más recientes en v_cabinet_financial_14d
        query4 = """
        SELECT 
            MAX(lead_date) AS max_date,
            COUNT(*) FILTER (WHERE lead_date >= '2025-12-14') AS records_since_14dec
        FROM ops.v_cabinet_financial_14d;
        """
        execute_query(conn, query4, "4. FINANCIAL_14D")
        
        # 5. Estado de ingestion_runs recientes (últimas 10)
        query5 = """
        SELECT 
            id AS run_id,
            started_at,
            completed_at,
            status,
            scope_date_from,
            scope_date_to,
            stats->>'processed' AS processed,
            stats->>'matched' AS matched,
            error_message
        FROM ops.ingestion_runs
        ORDER BY started_at DESC
        LIMIT 10;
        """
        execute_query(conn, query5, "5. INGESTION_RUNS (últimas 10)")
        
        # 6. Verificar si hay eventos de scouting_daily sin procesar (últimos 30 días)
        query6 = """
        SELECT 
            COUNT(*) AS unprocessed_count,
            MIN(registration_date::date) AS min_date,
            MAX(registration_date::date) AS max_date
        FROM public.module_ct_scouting_daily sd
        WHERE registration_date::date >= CURRENT_DATE - INTERVAL '30 days'
            AND NOT EXISTS (
                SELECT 1
                FROM observational.lead_events le
                WHERE le.source_table = 'module_ct_scouting_daily'
                    AND le.source_pk = (
                        sd.scout_id::text || '|' || 
                        COALESCE(sd.driver_phone, '') || '|' || 
                        COALESCE(sd.driver_license, '') || '|' || 
                        COALESCE(sd.registration_date::text, '')
                    )
            );
        """
        execute_query(conn, query6, "6. SCOUTING_DAILY SIN PROCESAR (últimos 30 días)")
        
        # 7. Verificar eventos recientes en lead_events por source_table
        query7 = """
        SELECT 
            source_table,
            COUNT(*) AS total_count,
            MAX(event_date) AS max_event_date,
            COUNT(*) FILTER (WHERE event_date >= '2025-12-14') AS since_14dec,
            COUNT(*) FILTER (WHERE payload_json->>'origin_tag' = 'cabinet') AS cabinet_count
        FROM observational.lead_events
        GROUP BY source_table
        ORDER BY max_event_date DESC;
        """
        execute_query(conn, query7, "7. LEAD_EVENTS por source_table")
        
        print_section("FIN DEL DIAGNÓSTICO")
        
    finally:
        conn.close()

if __name__ == "__main__":
    main()


