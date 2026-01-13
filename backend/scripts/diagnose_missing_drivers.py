"""
Script para diagnosticar por qué leads con identity y milestones no aparecen en la vista principal.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db import get_db
from sqlalchemy import text

def main():
    db = next(get_db())
    
    print("=" * 80)
    print("DIAGNÓSTICO: Leads con identity+driver+trips que NO aparecen en vista principal")
    print("=" * 80)
    
    # 1. Contar drivers en vista principal
    result1 = db.execute(text("SELECT COUNT(*) FROM ops.v_cabinet_financial_14d"))
    count_main = result1.scalar()
    print(f"\n1. Drivers en vista principal (v_cabinet_financial_14d): {count_main}")
    
    # 2. Contar leads con identity+driver+trips en Limbo
    result2 = db.execute(text("""
        SELECT COUNT(*) 
        FROM ops.v_cabinet_leads_limbo 
        WHERE person_key IS NOT NULL 
          AND driver_id IS NOT NULL 
          AND trips_14d > 0
    """))
    count_limbo_complete = result2.scalar()
    print(f"2. Leads con identity+driver+trips en Limbo: {count_limbo_complete}")
    
    # 3. Contar leads que NO están en vista principal
    result3 = db.execute(text("""
        SELECT COUNT(*) 
        FROM ops.v_cabinet_leads_limbo l 
        WHERE l.person_key IS NOT NULL 
          AND l.driver_id IS NOT NULL 
          AND l.trips_14d > 0 
          AND NOT EXISTS (
              SELECT 1 
              FROM ops.v_cabinet_financial_14d f 
              WHERE f.driver_id = l.driver_id
          )
    """))
    count_missing = result3.scalar()
    print(f"3. Leads con identity+driver+trips que NO están en vista principal: {count_missing}")
    
    # 4. Verificar si están en v_conversion_metrics
    result4 = db.execute(text("""
        SELECT COUNT(*) 
        FROM ops.v_cabinet_leads_limbo l 
        WHERE l.person_key IS NOT NULL 
          AND l.driver_id IS NOT NULL 
          AND l.trips_14d > 0 
          AND NOT EXISTS (
              SELECT 1 
              FROM ops.v_cabinet_financial_14d f 
              WHERE f.driver_id = l.driver_id
          )
          AND EXISTS (
              SELECT 1 
              FROM observational.v_conversion_metrics vcm
              WHERE vcm.driver_id = l.driver_id
                AND vcm.origin_tag = 'cabinet'
          )
    """))
    count_in_vcm = result4.scalar()
    print(f"4. De los faltantes, cuántos SÍ están en v_conversion_metrics (cabinet): {count_in_vcm}")
    
    # 5. Verificar si están en v_payment_calculation
    result5 = db.execute(text("""
        SELECT COUNT(*) 
        FROM ops.v_cabinet_leads_limbo l 
        WHERE l.person_key IS NOT NULL 
          AND l.driver_id IS NOT NULL 
          AND l.trips_14d > 0 
          AND NOT EXISTS (
              SELECT 1 
              FROM ops.v_cabinet_financial_14d f 
              WHERE f.driver_id = l.driver_id
          )
          AND EXISTS (
              SELECT 1 
              FROM ops.v_payment_calculation vpc
              WHERE vpc.driver_id = l.driver_id
                AND vpc.origin_tag = 'cabinet'
          )
    """))
    count_in_vpc = result5.scalar()
    print(f"5. De los faltantes, cuántos SÍ están en v_payment_calculation (cabinet): {count_in_vpc}")
    
    # 6. Verificar si tienen lead_date en v_conversion_metrics
    result6 = db.execute(text("""
        SELECT COUNT(*) 
        FROM ops.v_cabinet_leads_limbo l 
        WHERE l.person_key IS NOT NULL 
          AND l.driver_id IS NOT NULL 
          AND l.trips_14d > 0 
          AND NOT EXISTS (
              SELECT 1 
              FROM ops.v_cabinet_financial_14d f 
              WHERE f.driver_id = l.driver_id
          )
          AND EXISTS (
              SELECT 1 
              FROM observational.v_conversion_metrics vcm
              WHERE vcm.driver_id = l.driver_id
                AND vcm.origin_tag = 'cabinet'
                AND vcm.lead_date IS NULL
          )
    """))
    count_no_lead_date = result6.scalar()
    print(f"6. De los faltantes, cuántos tienen lead_date NULL en v_conversion_metrics: {count_no_lead_date}")
    
    # 7. Ejemplos de leads faltantes
    print("\n" + "=" * 80)
    print("EJEMPLOS de leads con identity+driver+trips que NO están en vista principal:")
    print("=" * 80)
    result7 = db.execute(text("""
        SELECT 
            l.lead_source_pk,
            l.lead_date,
            l.driver_id,
            l.person_key,
            l.trips_14d,
            l.reached_m1_14d,
            l.reached_m5_14d,
            l.reached_m25_14d,
            CASE 
                WHEN EXISTS (SELECT 1 FROM observational.v_conversion_metrics vcm WHERE vcm.driver_id = l.driver_id AND vcm.origin_tag = 'cabinet') 
                THEN 'SÍ en v_conversion_metrics'
                ELSE 'NO en v_conversion_metrics'
            END AS in_vcm,
            CASE 
                WHEN EXISTS (SELECT 1 FROM ops.v_payment_calculation vpc WHERE vpc.driver_id = l.driver_id AND vpc.origin_tag = 'cabinet') 
                THEN 'SÍ en v_payment_calculation'
                ELSE 'NO en v_payment_calculation'
            END AS in_vpc
        FROM ops.v_cabinet_leads_limbo l 
        WHERE l.person_key IS NOT NULL 
          AND l.driver_id IS NOT NULL 
          AND l.trips_14d > 0 
          AND NOT EXISTS (
              SELECT 1 
              FROM ops.v_cabinet_financial_14d f 
              WHERE f.driver_id = l.driver_id
          )
        LIMIT 10
    """))
    rows = result7.fetchall()
    if rows:
        print(f"\nMostrando {len(rows)} ejemplos:")
        for row in rows:
            print(f"\n  Lead: {row.lead_source_pk}")
            print(f"    Lead Date: {row.lead_date}")
            print(f"    Driver ID: {row.driver_id}")
            print(f"    Person Key: {row.person_key}")
            print(f"    Trips 14d: {row.trips_14d}")
            print(f"    M1: {row.reached_m1_14d}, M5: {row.reached_m5_14d}, M25: {row.reached_m25_14d}")
            print(f"    {row.in_vcm}")
            print(f"    {row.in_vpc}")
    else:
        print("\nNo se encontraron ejemplos (todos los leads con identity+driver+trips están en la vista principal)")
    
    print("\n" + "=" * 80)
    print("DIAGNÓSTICO COMPLETO")
    print("=" * 80)

if __name__ == "__main__":
    main()
