#!/usr/bin/env python3
"""
Script para diagnosticar leads post-05/01/2026 que no tienen identity.
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Configuración de base de datos
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"
)

def main():
    """Diagnostica leads post-05 sin identity."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("=" * 80)
        print("DIAGNOSTICO: Leads Post-05/01/2026 Sin Identity")
        print("=" * 80)
        print()
        
        # 1. Verificar si están en lead_events
        print("1. Verificando si leads post-05 están en lead_events...")
        query1 = text("""
            SELECT 
                COUNT(*) AS total_leads_raw,
                COUNT(DISTINCT COALESCE(external_id::text, id::text)) AS distinct_pk
            FROM public.module_ct_cabinet_leads
            WHERE lead_created_at::date > '2026-01-05'
        """)
        result1 = session.execute(query1)
        row1 = result1.fetchone()
        print(f"   Leads en module_ct_cabinet_leads: {row1.total_leads_raw}")
        print()
        
        query2 = text("""
            SELECT 
                COUNT(*) AS total_events,
                COUNT(DISTINCT source_pk) AS distinct_source_pk,
                COUNT(DISTINCT person_key) AS distinct_person_key,
                COUNT(*) FILTER (WHERE person_key IS NOT NULL) AS with_person_key,
                COUNT(*) FILTER (WHERE person_key IS NULL) AS without_person_key
            FROM observational.lead_events
            WHERE source_table = 'module_ct_cabinet_leads'
                AND event_date > '2026-01-05'
        """)
        result2 = session.execute(query2)
        row2 = result2.fetchone()
        print(f"   Events en lead_events: {row2.total_events}")
        print(f"   Con person_key: {row2.with_person_key}")
        print(f"   Sin person_key: {row2.without_person_key}")
        print()
        
        # 2. Verificar si tienen identity_links
        query3 = text("""
            SELECT 
                COUNT(DISTINCT il.source_pk) AS leads_with_identity
            FROM public.module_ct_cabinet_leads cl
            LEFT JOIN canon.identity_links il
                ON il.source_table = 'module_ct_cabinet_leads'
                AND il.source_pk = COALESCE(cl.external_id::text, cl.id::text)
            WHERE cl.lead_created_at::date > '2026-01-05'
                AND il.person_key IS NOT NULL
        """)
        result3 = session.execute(query3)
        row3 = result3.fetchone()
        print(f"   Leads con identity_links: {row3.leads_with_identity}")
        print()
        
        # 3. Verificar si están en v_conversion_metrics
        query4 = text("""
            SELECT 
                COUNT(DISTINCT driver_id) AS drivers_in_metrics
            FROM observational.v_conversion_metrics
            WHERE origin_tag = 'cabinet'
                AND lead_date > '2026-01-05'
        """)
        result4 = session.execute(query4)
        row4 = result4.fetchone()
        print(f"   Drivers en v_conversion_metrics: {row4.drivers_in_metrics}")
        print()
        
        # 4. Muestra algunos ejemplos de leads sin identity
        print("4. Ejemplos de leads post-05 sin identity:")
        query5 = text("""
            SELECT 
                cl.id,
                cl.external_id,
                cl.lead_created_at::date AS lead_date,
                COALESCE(cl.external_id::text, cl.id::text) AS source_pk,
                CASE WHEN le.id IS NOT NULL THEN 'SI' ELSE 'NO' END AS en_lead_events,
                CASE WHEN le.person_key IS NOT NULL THEN 'SI' ELSE 'NO' END AS tiene_person_key,
                CASE WHEN il.person_key IS NOT NULL THEN 'SI' ELSE 'NO' END AS tiene_identity_link
            FROM public.module_ct_cabinet_leads cl
            LEFT JOIN observational.lead_events le
                ON le.source_table = 'module_ct_cabinet_leads'
                AND le.source_pk = COALESCE(cl.external_id::text, cl.id::text)
            LEFT JOIN canon.identity_links il
                ON il.source_table = 'module_ct_cabinet_leads'
                AND il.source_pk = COALESCE(cl.external_id::text, cl.id::text)
            WHERE cl.lead_created_at::date > '2026-01-05'
                AND (le.person_key IS NULL OR il.person_key IS NULL)
            ORDER BY cl.lead_created_at DESC
            LIMIT 10
        """)
        result5 = session.execute(query5)
        rows5 = result5.fetchall()
        
        if rows5:
            print(f"   {'ID':<10} {'External ID':<15} {'Lead Date':<12} {'Source PK':<15} {'En Events':<10} {'Person Key':<12} {'Identity Link':<15}")
            print("-" * 100)
            for row in rows5:
                print(f"   {str(row.id):<10} {str(row.external_id or 'NULL'):<15} {str(row.lead_date):<12} {str(row.source_pk):<15} {row.en_lead_events:<10} {row.tiene_person_key:<12} {row.tiene_identity_link:<15}")
        else:
            print("   No se encontraron leads sin identity.")
        print()
        
        # 5. Recomendación
        print("=" * 80)
        print("RECOMENDACION:")
        print("=" * 80)
        
        if row2.total_events == 0:
            print("PROBLEMA: Los leads post-05 NO están en lead_events.")
            print("SOLUCION: Ejecutar populate_events_from_cabinet para fechas post-05:")
            print("   POST /api/v1/attribution/populate-events")
            print("   Body: {")
            print('     "source_tables": ["module_ct_cabinet_leads"],')
            print('     "date_from": "2026-01-06",')
            print('     "date_to": "2026-01-10"')
            print("   }")
        elif row2.without_person_key > 0:
            print("PROBLEMA: Los leads post-05 están en lead_events pero NO tienen person_key.")
            print("SOLUCION: Ejecutar matching/ingestion para estos leads:")
            print("   POST /api/v1/identity/run")
            print("   Body: {")
            print('     "source_tables": ["module_ct_cabinet_leads"],')
            print('     "scope_date_from": "2026-01-06",')
            print('     "scope_date_to": "2026-01-10",')
            print('     "incremental": true')
            print("   }")
        else:
            print("Los leads post-05 tienen person_key. Verificar por qué no aparecen en la auditoría.")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    main()
