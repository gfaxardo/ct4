#!/usr/bin/env python3
"""
Script para investigar el problema de integridad:
Scouts con quality_bucket = MISSING pero scout_id IS NOT NULL
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import settings

def main():
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("INVESTIGACIÓN: Problema de Integridad")
        print("="*80)
        
        # Encontrar casos específicos con el problema
        query1 = text("""
            SELECT 
                driver_id,
                person_key,
                scout_id,
                scout_name,
                scout_quality_bucket,
                is_scout_resolved,
                scout_source_table,
                scout_priority
            FROM ops.v_yango_collection_with_scout
            WHERE scout_quality_bucket = 'MISSING' 
                AND scout_id IS NOT NULL
            LIMIT 10
        """)
        
        results = session.execute(query1).fetchall()
        
        if not results:
            print("\n[OK] No se encontraron casos con el problema")
            return 0
        
        print(f"\n[PROBLEMA] Se encontraron {len(results)} casos con quality_bucket=MISSING pero scout_id IS NOT NULL:")
        
        for i, row in enumerate(results, 1):
            print(f"\nCaso {i}:")
            print(f"  driver_id: {row.driver_id}")
            print(f"  person_key: {row.person_key}")
            print(f"  scout_id: {row.scout_id}")
            print(f"  scout_name: {row.scout_name}")
            print(f"  scout_quality_bucket: {row.scout_quality_bucket}")
            print(f"  is_scout_resolved: {row.is_scout_resolved}")
            print(f"  scout_source_table: {row.scout_source_table}")
            print(f"  scout_priority: {row.scout_priority}")
        
        # Investigar la lógica de la vista
        print("\n" + "="*80)
        print("INVESTIGACIÓN: Lógica de la Vista")
        print("="*80)
        
        # Verificar qué está pasando en v_scout_attribution para estos casos
        if results:
            driver_id_example = results[0].driver_id
            person_key_example = results[0].person_key
            
            print(f"\nInvestigando driver_id: {driver_id_example}")
            print(f"person_key: {person_key_example}")
            
            # Verificar en v_scout_attribution
            query2 = text("""
                SELECT 
                    person_key,
                    driver_id,
                    scout_id,
                    source_table,
                    priority
                FROM ops.v_scout_attribution
                WHERE person_key = :person_key
                   OR driver_id = :driver_id
            """)
            
            result2 = session.execute(query2, {
                "person_key": person_key_example,
                "driver_id": driver_id_example
            }).fetchall()
            
            print(f"\nEn v_scout_attribution:")
            for row in result2:
                print(f"  person_key: {row.person_key}, driver_id: {row.driver_id}, scout_id: {row.scout_id}, source_table: {row.source_table}, priority: {row.priority}")
            
            # Verificar en v_yango_cabinet_claims_for_collection
            query3 = text("""
                SELECT 
                    driver_id,
                    person_key
                FROM ops.v_yango_cabinet_claims_for_collection
                WHERE driver_id = :driver_id
                LIMIT 1
            """)
            
            result3 = session.execute(query3, {"driver_id": driver_id_example}).fetchone()
            if result3:
                print(f"\nEn v_yango_cabinet_claims_for_collection:")
                print(f"  driver_id: {result3.driver_id}, person_key: {result3.person_key}")
            
            # Verificar el JOIN en la vista
            print(f"\n" + "="*80)
            print("DIAGNÓSTICO: Verificando el JOIN")
            print("="*80)
            
            # Simular el JOIN manualmente
            query4 = text("""
                SELECT 
                    y.driver_id,
                    y.person_key AS y_person_key,
                    sa.person_key AS sa_person_key,
                    sa.driver_id AS sa_driver_id,
                    sa.scout_id,
                    sa.source_table,
                    CASE 
                        WHEN sa.source_table = 'observational.lead_ledger' THEN 'SATISFACTORY_LEDGER'
                        WHEN sa.source_table = 'observational.lead_events' THEN 'EVENTS_ONLY'
                        WHEN sa.source_table = 'public.module_ct_migrations' THEN 'MIGRATIONS_ONLY'
                        WHEN sa.source_table = 'public.module_ct_scouting_daily' THEN 'SCOUTING_DAILY_ONLY'
                        WHEN sa.source_table = 'public.module_ct_cabinet_payments' THEN 'CABINET_PAYMENTS_ONLY'
                        ELSE 'MISSING'
                    END AS calculated_quality_bucket
                FROM ops.v_yango_cabinet_claims_for_collection y
                LEFT JOIN ops.v_scout_attribution sa
                    ON (sa.person_key = y.person_key AND y.person_key IS NOT NULL)
                    OR (sa.driver_id = y.driver_id AND y.person_key IS NULL AND sa.person_key IS NULL)
                WHERE y.driver_id = :driver_id
                LIMIT 5
            """)
            
            result4 = session.execute(query4, {"driver_id": driver_id_example}).fetchall()
            print(f"\nSimulación del JOIN:")
            for row in result4:
                print(f"  driver_id: {row.driver_id}")
                print(f"  y.person_key: {row.y_person_key}")
                print(f"  sa.person_key: {row.sa_person_key}")
                print(f"  sa.driver_id: {row.sa_driver_id}")
                print(f"  sa.scout_id: {row.scout_id}")
                print(f"  sa.source_table: {row.source_table}")
                print(f"  calculated_quality_bucket: {row.calculated_quality_bucket}")
                print()
        
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Error durante la investigación: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()

if __name__ == "__main__":
    sys.exit(main())
