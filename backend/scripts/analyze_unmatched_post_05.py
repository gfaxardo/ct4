#!/usr/bin/env python3
"""
Script para analizar leads post-05 que no tienen identity (unmatched).
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
    """Analiza leads post-05 sin identity."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("=" * 80)
        print("ANALISIS: Leads Post-05 Sin Identity (Unmatched)")
        print("=" * 80)
        print()
        
        # 1. Verificar si están en identity_unmatched
        print("1. Verificando si están en identity_unmatched...")
        query1 = text("""
            SELECT 
                COUNT(*) AS total_unmatched,
                COUNT(DISTINCT source_pk) AS distinct_source_pk,
                COUNT(DISTINCT reason_code) AS distinct_reasons
            FROM canon.identity_unmatched
            WHERE source_table = 'module_ct_cabinet_leads'
                AND snapshot_date > '2026-01-05'
        """)
        result1 = session.execute(query1)
        row1 = result1.fetchone()
        print(f"   Total en identity_unmatched: {row1.total_unmatched}")
        print(f"   Source PKs distintos: {row1.distinct_source_pk}")
        print()
        
        # 2. Ver breakdown por reason_code
        query2 = text("""
            SELECT 
                reason_code,
                COUNT(*) AS count
            FROM canon.identity_unmatched
            WHERE source_table = 'module_ct_cabinet_leads'
                AND snapshot_date > '2026-01-05'
            GROUP BY reason_code
            ORDER BY count DESC
        """)
        result2 = session.execute(query2)
        rows2 = result2.fetchall()
        
        if rows2:
            print("2. Breakdown por reason_code:")
            print(f"   {'Reason Code':<30} {'Count':<10}")
            print("-" * 45)
            for row in rows2:
                print(f"   {str(row.reason_code):<30} {row.count:<10}")
        else:
            print("2. No se encontraron registros en identity_unmatched.")
        print()
        
        # 3. Analizar datos disponibles en los leads sin identity
        print("3. Analizando datos disponibles en leads sin identity...")
        query3 = text("""
            SELECT 
                COUNT(*) AS total,
                COUNT(park_phone) AS has_phone,
                COUNT(asset_plate_number) AS has_plate,
                COUNT(first_name) AS has_first_name,
                COUNT(last_name) AS has_last_name,
                COUNT(CASE WHEN park_phone IS NOT NULL AND park_phone != '' THEN 1 END) AS phone_not_empty,
                COUNT(CASE WHEN asset_plate_number IS NOT NULL AND asset_plate_number != '' THEN 1 END) AS plate_not_empty
            FROM public.module_ct_cabinet_leads cl
            LEFT JOIN observational.lead_events le
                ON le.source_table = 'module_ct_cabinet_leads'
                AND le.source_pk = COALESCE(cl.external_id::text, cl.id::text)
            LEFT JOIN canon.identity_links il
                ON il.source_table = 'module_ct_cabinet_leads'
                AND il.source_pk = COALESCE(cl.external_id::text, cl.id::text)
            WHERE cl.lead_created_at::date > '2026-01-05'
                AND (le.person_key IS NULL OR il.person_key IS NULL)
        """)
        result3 = session.execute(query3)
        row3 = result3.fetchone()
        
        print(f"   Total leads sin identity: {row3.total}")
        print(f"   Con phone (no null): {row3.has_phone}")
        print(f"   Con phone (no vacío): {row3.phone_not_empty}")
        print(f"   Con plate (no null): {row3.has_plate}")
        print(f"   Con plate (no vacío): {row3.plate_not_empty}")
        print(f"   Con first_name: {row3.has_first_name}")
        print(f"   Con last_name: {row3.has_last_name}")
        print()
        
        # 4. Ejemplos de leads sin datos suficientes
        print("4. Ejemplos de leads sin identity (primeros 10):")
        query4 = text("""
            SELECT 
                cl.id,
                cl.external_id,
                cl.lead_created_at::date AS lead_date,
                cl.park_phone,
                cl.asset_plate_number,
                cl.first_name,
                cl.last_name,
                iu.reason_code
            FROM public.module_ct_cabinet_leads cl
            LEFT JOIN observational.lead_events le
                ON le.source_table = 'module_ct_cabinet_leads'
                AND le.source_pk = COALESCE(cl.external_id::text, cl.id::text)
            LEFT JOIN canon.identity_links il
                ON il.source_table = 'module_ct_cabinet_leads'
                AND il.source_pk = COALESCE(cl.external_id::text, cl.id::text)
            LEFT JOIN canon.identity_unmatched iu
                ON iu.source_table = 'module_ct_cabinet_leads'
                AND iu.source_pk = COALESCE(cl.external_id::text, cl.id::text)
                AND iu.snapshot_date > '2026-01-05'
            WHERE cl.lead_created_at::date > '2026-01-05'
                AND (le.person_key IS NULL OR il.person_key IS NULL)
            ORDER BY cl.lead_created_at DESC
            LIMIT 10
        """)
        result4 = session.execute(query4)
        rows4 = result4.fetchall()
        
        if rows4:
            print(f"   {'ID':<8} {'External ID':<15} {'Lead Date':<12} {'Phone':<15} {'Plate':<15} {'Name':<30} {'Reason':<20}")
            print("-" * 120)
            for row in rows4:
                name = f"{row.first_name or ''} {row.last_name or ''}".strip() or 'N/A'
                print(f"   {str(row.id):<8} {str(row.external_id or 'N/A')[:15]:<15} {str(row.lead_date):<12} {str(row.park_phone or 'N/A')[:15]:<15} {str(row.asset_plate_number or 'N/A')[:15]:<15} {name[:30]:<30} {str(row.reason_code or 'N/A')[:20]:<20}")
        print()
        
        # 5. Recomendación
        print("=" * 80)
        print("CONCLUSION:")
        print("=" * 80)
        print()
        
        if row3.phone_not_empty == 0 and row3.plate_not_empty == 0:
            print("PROBLEMA: Los leads sin identity NO tienen datos suficientes para matching.")
            print("  - No tienen phone ni plate (campos requeridos para matching)")
            print("  - Estos leads probablemente no se pueden matchear automáticamente")
            print("  - Requieren resolución manual o datos adicionales")
        elif row1.total_unmatched > 0:
            print(f"PROBLEMA: {row1.total_unmatched} leads están en identity_unmatched.")
            print("  - Revisar reason_code para entender por qué no se matchearon")
            print("  - Algunos pueden requerir resolución manual")
        else:
            print("Los leads sin identity pueden tener datos insuficientes o no coincidir con drivers existentes.")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    main()
