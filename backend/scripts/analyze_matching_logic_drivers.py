"""
Análisis de la Lógica de Matching para Drivers sin Leads
=========================================================

Analiza qué estaba comparando el matching engine cuando creó los 902 drivers sin leads.
Específicamente para los casos de R1_PHONE_EXACT y R2_LICENSE_EXACT.
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db import SessionLocal
from app.services.normalization import normalize_phone, normalize_license


def analyze_matching_logic():
    """
    Analiza la lógica de matching que creó los drivers sin leads
    """
    db = SessionLocal()
    
    try:
        print(f"\n{'='*80}")
        print(f"ANALISIS DE LOGICA DE MATCHING: Drivers sin Leads")
        print(f"{'='*80}\n")
        
        # Obtener drivers sin leads con información de matching
        query = text("""
            SELECT DISTINCT
                il.source_pk as driver_id,
                ir.person_key,
                ir.primary_phone,
                ir.primary_license,
                ir.primary_full_name,
                il.match_rule,
                il.linked_at,
                il.evidence,
                d.phone as driver_phone_raw,
                d.license_number as driver_license_raw,
                d.license_normalized_number as driver_license_norm_raw
            FROM canon.identity_links il
            JOIN canon.identity_registry ir ON ir.person_key = il.person_key
            LEFT JOIN public.drivers d ON d.driver_id::text = il.source_pk
            WHERE il.source_table = 'drivers'
            AND il.match_rule IN ('R1_PHONE_EXACT', 'R2_LICENSE_EXACT')
            AND il.person_key NOT IN (
                SELECT DISTINCT person_key
                FROM canon.identity_links
                WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
            )
            ORDER BY il.linked_at DESC
            LIMIT 50
        """)
        
        result = db.execute(query)
        drivers = result.fetchall()
        
        print(f"Analizando {len(drivers)} casos de R1_PHONE_EXACT y R2_LICENSE_EXACT\n")
        
        # Para cada driver, entender qué estaba comparando
        for idx, driver in enumerate(drivers, 1):
            print(f"{'='*80}")
            print(f"Caso {idx}: Driver {driver.driver_id[:20]}...")
            print(f"{'='*80}")
            print(f"Match Rule: {driver.match_rule}")
            print(f"Linked at: {driver.linked_at}")
            print(f"Person Key: {driver.person_key}")
            print(f"\nDatos del Driver:")
            print(f"  Phone Raw: {driver.driver_phone_raw}")
            print(f"  Phone Normalized (en registry): {driver.primary_phone}")
            print(f"  License Raw: {driver.driver_license_raw}")
            print(f"  License Normalized Raw: {driver.driver_license_norm_raw}")
            print(f"  License Normalized (en registry): {driver.primary_license}")
            print(f"  Name: {driver.primary_full_name}")
            
            # Normalizar para comparar
            phone_norm = normalize_phone(driver.driver_phone_raw) if driver.driver_phone_raw else None
            license_norm = normalize_license(driver.driver_license_norm_raw or driver.driver_license_raw) if (driver.driver_license_norm_raw or driver.driver_license_raw) else None
            
            print(f"\nDatos Normalizados:")
            print(f"  Phone Norm: {phone_norm}")
            print(f"  License Norm: {license_norm}")
            
            # Buscar qué estaba comparando en drivers_index
            if driver.match_rule == 'R1_PHONE_EXACT' and phone_norm:
                print(f"\n{'='*80}")
                print(f"BUSCANDO EN drivers_index POR PHONE_NORM = {phone_norm}")
                print(f"{'='*80}")
                
                query_drivers_index = text("""
                    SELECT 
                        driver_id,
                        park_id,
                        phone_norm,
                        license_norm,
                        full_name_norm,
                        snapshot_date
                    FROM canon.drivers_index
                    WHERE phone_norm = :phone_norm
                    ORDER BY snapshot_date DESC
                    LIMIT 10
                """)
                
                result_index = db.execute(query_drivers_index, {"phone_norm": phone_norm})
                matches = result_index.fetchall()
                
                print(f"Encontrados {len(matches)} drivers en drivers_index con el mismo teléfono:")
                for match_idx, match in enumerate(matches, 1):
                    is_same_driver = str(match.driver_id) == driver.driver_id
                    marker = " <-- ESTE ES EL DRIVER ACTUAL" if is_same_driver else ""
                    print(f"\n  {match_idx}. Driver ID: {match.driver_id}")
                    print(f"     Park ID: {match.park_id}")
                    print(f"     Phone Norm: {match.phone_norm}")
                    print(f"     License Norm: {match.license_norm}")
                    print(f"     Name Norm: {match.full_name_norm}")
                    print(f"     Snapshot Date: {match.snapshot_date}")
                    print(f"     {marker}")
                    
                    # Verificar si este driver tiene link
                    link_query = text("""
                        SELECT id, person_key, match_rule, linked_at
                        FROM canon.identity_links
                        WHERE source_table = 'drivers'
                        AND source_pk = :driver_id
                    """)
                    link_result = db.execute(link_query, {"driver_id": str(match.driver_id)})
                    link = link_result.fetchone()
                    if link:
                        print(f"     Tiene link: person_key={link.person_key}, rule={link.match_rule}, linked_at={link.linked_at}")
                    else:
                        print(f"     NO tiene link")
            
            elif driver.match_rule == 'R2_LICENSE_EXACT' and license_norm:
                print(f"\n{'='*80}")
                print(f"BUSCANDO EN drivers_index POR LICENSE_NORM = {license_norm}")
                print(f"{'='*80}")
                
                query_drivers_index = text("""
                    SELECT 
                        driver_id,
                        park_id,
                        phone_norm,
                        license_norm,
                        full_name_norm,
                        snapshot_date
                    FROM canon.drivers_index
                    WHERE license_norm = :license_norm
                    ORDER BY snapshot_date DESC
                    LIMIT 10
                """)
                
                result_index = db.execute(query_drivers_index, {"license_norm": license_norm})
                matches = result_index.fetchall()
                
                print(f"Encontrados {len(matches)} drivers en drivers_index con la misma licencia:")
                for match_idx, match in enumerate(matches, 1):
                    is_same_driver = str(match.driver_id) == driver.driver_id
                    marker = " <-- ESTE ES EL DRIVER ACTUAL" if is_same_driver else ""
                    print(f"\n  {match_idx}. Driver ID: {match.driver_id}")
                    print(f"     Park ID: {match.park_id}")
                    print(f"     Phone Norm: {match.phone_norm}")
                    print(f"     License Norm: {match.license_norm}")
                    print(f"     Name Norm: {match.full_name_norm}")
                    print(f"     Snapshot Date: {match.snapshot_date}")
                    print(f"     {marker}")
                    
                    # Verificar si este driver tiene link
                    link_query = text("""
                        SELECT id, person_key, match_rule, linked_at
                        FROM canon.identity_links
                        WHERE source_table = 'drivers'
                        AND source_pk = :driver_id
                    """)
                    link_result = db.execute(link_query, {"driver_id": str(match.driver_id)})
                    link = link_result.fetchone()
                    if link:
                        print(f"     Tiene link: person_key={link.person_key}, rule={link.match_rule}, linked_at={link.linked_at}")
                    else:
                        print(f"     NO tiene link")
            
            # Verificar si hay personas existentes con el mismo teléfono/licencia
            print(f"\n{'='*80}")
            print(f"BUSCANDO PERSONAS EXISTENTES EN identity_registry")
            print(f"{'='*80}")
            
            if phone_norm:
                person_by_phone_query = text("""
                    SELECT person_key, primary_phone, primary_license, primary_full_name, created_at
                    FROM canon.identity_registry
                    WHERE primary_phone = :phone_norm
                    AND person_key != :person_key
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                person_result = db.execute(person_by_phone_query, {
                    "phone_norm": phone_norm,
                    "person_key": driver.person_key
                })
                persons_by_phone = person_result.fetchall()
                
                if persons_by_phone:
                    print(f"\nEncontradas {len(persons_by_phone)} personas con el mismo teléfono:")
                    for p in persons_by_phone:
                        print(f"  - Person Key: {p.person_key}")
                        print(f"    Created at: {p.created_at}")
                        print(f"    Phone: {p.primary_phone}")
                        print(f"    License: {p.primary_license}")
                        print(f"    Name: {p.primary_full_name}")
                else:
                    print(f"\nNO hay otras personas con el mismo teléfono")
            
            if license_norm:
                person_by_license_query = text("""
                    SELECT person_key, primary_phone, primary_license, primary_full_name, created_at
                    FROM canon.identity_registry
                    WHERE primary_license = :license_norm
                    AND person_key != :person_key
                    ORDER BY created_at DESC
                    LIMIT 5
                """)
                person_result = db.execute(person_by_license_query, {
                    "license_norm": license_norm,
                    "person_key": driver.person_key
                })
                persons_by_license = person_result.fetchall()
                
                if persons_by_license:
                    print(f"\nEncontradas {len(persons_by_license)} personas con la misma licencia:")
                    for p in persons_by_license:
                        print(f"  - Person Key: {p.person_key}")
                        print(f"    Created at: {p.created_at}")
                        print(f"    Phone: {p.primary_phone}")
                        print(f"    License: {p.primary_license}")
                        print(f"    Name: {p.primary_full_name}")
                else:
                    print(f"\nNO hay otras personas con la misma licencia")
            
            # CONCLUSIÓN
            print(f"\n{'='*80}")
            print(f"CONCLUSION PARA ESTE CASO:")
            print(f"{'='*80}")
            print(f"El matching engine estaba comparando:")
            print(f"  - Driver contra drivers_index (tabla de drivers normalizados)")
            print(f"  - NO estaba comparando contra leads (cabinet/scouting/migrations)")
            print(f"  - Si encontraba un driver con el mismo teléfono/licencia, creaba una persona")
            print(f"  - Pero NO verificaba si había un lead asociado")
            print(f"  - Por eso se crearon drivers sin leads")
            
            if idx >= 10:  # Limitar a 10 casos para no saturar
                print(f"\n... (limitado a 10 casos para análisis)")
                break
        
        print(f"\n{'='*80}")
        print(f"RESUMEN GENERAL")
        print(f"{'='*80}\n")
        print(f"PROBLEMA IDENTIFICADO:")
        print(f"  Cuando process_drivers() se ejecutaba:")
        print(f"  1. Tomaba un driver de public.drivers")
        print(f"  2. Normalizaba teléfono/licencia")
        print(f"  3. Buscaba en canon.drivers_index por teléfono/licencia normalizado")
        print(f"  4. Si encontraba un driver con el mismo teléfono/licencia:")
        print(f"     - Llamaba a _get_or_create_person_from_driver()")
        print(f"     - Esta función buscaba si ya existía una persona con ese teléfono/licencia")
        print(f"     - Si no existía, creaba una NUEVA persona")
        print(f"     - Creaba un link de driver para esa persona")
        print(f"  5. NO verificaba si había un LEAD asociado")
        print(f"\n  RESULTADO: Drivers agrupados por teléfono/licencia, pero SIN leads")
        print(f"\n  SOLUCION: process_drivers() ahora NO crea links directamente")
        print(f"            Los links solo se crean cuando hay un lead que matchea con un driver")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"\nERROR: Error en analisis: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    analyze_matching_logic()

