"""
Búsqueda Exhaustiva de Leads para Drivers sin Leads
====================================================

Busca leads de manera más agresiva para los 902 drivers sin leads:
- Variaciones en normalización de teléfonos
- Búsquedas por licencia
- Búsquedas por nombre similar
- Búsquedas en todas las fuentes posibles
- Verifica leads que no tienen links pero deberían tenerlos
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import hashlib

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db import SessionLocal
from app.services.normalization import normalize_phone, normalize_license, normalize_name, normalize_phone_pe9
from difflib import SequenceMatcher


def similarity(a, b):
    """Calcula similitud entre dos strings"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def exhaustive_search():
    """
    Búsqueda exhaustiva de leads para drivers sin leads
    """
    db = SessionLocal()
    
    try:
        print(f"\n{'='*80}")
        print(f"BUSQUEDA EXHAUSTIVA DE LEADS PARA DRIVERS SIN LEADS")
        print(f"{'='*80}\n")
        
        # Obtener todos los drivers sin leads
        query_drivers = text("""
            SELECT DISTINCT
                il.source_pk as driver_id,
                ir.person_key,
                ir.primary_phone,
                ir.primary_license,
                ir.primary_full_name,
                il.match_rule,
                il.linked_at,
                d.phone as driver_phone_raw,
                d.license_number as driver_license_raw,
                d.license_normalized_number as driver_license_norm_raw,
                d.full_name as driver_name_raw
            FROM canon.identity_links il
            JOIN canon.identity_registry ir ON ir.person_key = il.person_key
            LEFT JOIN public.drivers d ON d.driver_id::text = il.source_pk
            WHERE il.source_table = 'drivers'
            AND il.person_key NOT IN (
                SELECT DISTINCT person_key
                FROM canon.identity_links
                WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
            )
            ORDER BY il.linked_at DESC
        """)
        
        result = db.execute(query_drivers)
        drivers = result.fetchall()
        
        print(f"Total de drivers sin leads a investigar: {len(drivers)}\n")
        
        matches_found = []
        matches_by_source = defaultdict(list)
        
        # Procesar en lotes para mejor rendimiento
        batch_size = 100
        processed = 0
        
        for i in range(0, len(drivers), batch_size):
            batch = drivers[i:i+batch_size]
            
            if processed % 200 == 0:
                print(f"Procesados {processed}/{len(drivers)} drivers...")
            
            for driver in batch:
                driver_id = driver.driver_id
                phone_norm = driver.primary_phone
                license_norm = driver.primary_license
                name_norm = driver.primary_full_name
                
                # Normalizar datos del driver con múltiples variaciones
                phone_variations = set()
                if driver.driver_phone_raw:
                    phone_variations.add(normalize_phone(driver.driver_phone_raw))
                    phone_variations.add(normalize_phone_pe9(driver.driver_phone_raw))
                    # Agregar variaciones sin código de país
                    phone_clean = normalize_phone(driver.driver_phone_raw)
                    if phone_clean and len(phone_clean) >= 9:
                        phone_variations.add(phone_clean[-9:])  # Últimos 9 dígitos
                if phone_norm:
                    phone_variations.add(phone_norm)
                    if len(phone_norm) >= 9:
                        phone_variations.add(phone_norm[-9:])
                
                license_variations = set()
                if driver.driver_license_raw:
                    license_variations.add(normalize_license(driver.driver_license_raw))
                if driver.driver_license_norm_raw:
                    license_variations.add(normalize_license(driver.driver_license_norm_raw))
                if license_norm:
                    license_variations.add(license_norm)
                
                # 1. BUSCAR EN CABINET_LEADS
                if phone_variations:
                    for phone_var in phone_variations:
                        if not phone_var:
                            continue
                        
                        # Buscar por teléfono exacto
                        query_cabinet = text("""
                            SELECT 
                                id,
                                external_id,
                                park_phone,
                                first_name,
                                middle_name,
                                last_name,
                                asset_plate_number,
                                lead_created_at,
                                created_at
                            FROM public.module_ct_cabinet_leads
                            WHERE park_phone IS NOT NULL
                            AND (
                                REPLACE(REPLACE(REPLACE(REPLACE(park_phone, ' ', ''), '-', ''), '(', ''), ')', '') LIKE :phone_pattern1
                                OR REPLACE(REPLACE(REPLACE(REPLACE(park_phone, ' ', ''), '-', ''), '(', ''), ')', '') LIKE :phone_pattern2
                                OR REPLACE(REPLACE(REPLACE(REPLACE(park_phone, ' ', ''), '-', ''), '(', ''), ')', '') LIKE :phone_pattern3
                            )
                            LIMIT 20
                        """)
                        
                        phone_pattern1 = f"%{phone_var}"
                        phone_pattern2 = f"%{phone_var[-9:]}" if len(phone_var) >= 9 else phone_pattern1
                        phone_pattern3 = phone_var
                        
                        result_cabinet = db.execute(query_cabinet, {
                            "phone_pattern1": phone_pattern1,
                            "phone_pattern2": phone_pattern2,
                            "phone_pattern3": phone_pattern3
                        })
                        cabinet_rows = result_cabinet.fetchall()
                        
                        for row in cabinet_rows:
                            cabinet_phone_norm = normalize_phone(row.park_phone)
                            if cabinet_phone_norm not in phone_variations:
                                continue
                            
                            # Verificar si ya tiene link
                            source_pk = str(row.external_id) if row.external_id else str(row.id)
                            check_link = text("""
                                SELECT id, person_key
                                FROM canon.identity_links
                                WHERE source_table = 'module_ct_cabinet_leads'
                                AND source_pk = :source_pk
                            """)
                            link_exists = db.execute(check_link, {"source_pk": source_pk}).fetchone()
                            
                            if not link_exists:
                                full_name_cabinet = f"{row.first_name or ''} {row.middle_name or ''} {row.last_name or ''}".strip()
                                name_sim = similarity(name_norm or "", normalize_name(full_name_cabinet)) if name_norm else 0
                                
                                match = {
                                    "driver_id": driver_id,
                                    "person_key": str(driver.person_key),
                                    "match_type": "PHONE_EXACT",
                                    "source_table": "module_ct_cabinet_leads",
                                    "source_pk": source_pk,
                                    "source_id": row.id,
                                    "driver_phone": phone_norm,
                                    "lead_phone": row.park_phone,
                                    "driver_name": name_norm,
                                    "lead_name": full_name_cabinet,
                                    "name_similarity": name_sim,
                                    "lead_created_at": row.lead_created_at,
                                    "confidence": "HIGH" if name_sim > 0.5 else "MEDIUM"
                                }
                                matches_found.append(match)
                                matches_by_source["cabinet_leads"].append(match)
                                break  # Solo un match por driver
                        
                        if any(m["driver_id"] == driver_id for m in matches_found):
                            break  # Ya encontramos match para este driver
                
                # 2. BUSCAR EN SCOUTING_DAILY
                if not any(m["driver_id"] == driver_id for m in matches_found):
                    if phone_variations or license_variations:
                        # Buscar por teléfono
                        if phone_variations:
                            for phone_var in phone_variations:
                                if not phone_var:
                                    continue
                                
                                query_scouting = text("""
                                    SELECT 
                                        id,
                                        scout_id,
                                        driver_phone,
                                        driver_license,
                                        driver_name,
                                        registration_date,
                                        created_at
                                    FROM public.module_ct_scouting_daily
                                    WHERE driver_phone IS NOT NULL
                                    AND (
                                        REPLACE(REPLACE(REPLACE(REPLACE(driver_phone, ' ', ''), '-', ''), '(', ''), ')', '') LIKE :phone_pattern1
                                        OR REPLACE(REPLACE(REPLACE(REPLACE(driver_phone, ' ', ''), '-', ''), '(', ''), ')', '') LIKE :phone_pattern2
                                    )
                                    LIMIT 20
                                """)
                                
                                phone_pattern1 = f"%{phone_var}"
                                phone_pattern2 = f"%{phone_var[-9:]}" if len(phone_var) >= 9 else phone_pattern1
                                
                                result_scouting = db.execute(query_scouting, {
                                    "phone_pattern1": phone_pattern1,
                                    "phone_pattern2": phone_pattern2
                                })
                                scouting_rows = result_scouting.fetchall()
                                
                                for row in scouting_rows:
                                    scouting_phone_norm = normalize_phone(row.driver_phone)
                                    if scouting_phone_norm not in phone_variations:
                                        continue
                                    
                                    # Generar source_pk canónico
                                    source_pk_raw = f"{row.scout_id}|{normalize_phone(row.driver_phone)}|{normalize_license(row.driver_license) if row.driver_license else ''}|{row.registration_date}"
                                    source_pk = hashlib.md5(source_pk_raw.encode()).hexdigest()
                                    
                                    # Verificar si ya tiene link
                                    check_link = text("""
                                        SELECT id, person_key
                                        FROM canon.identity_links
                                        WHERE source_table = 'module_ct_scouting_daily'
                                        AND source_pk = :source_pk
                                    """)
                                    link_exists = db.execute(check_link, {"source_pk": source_pk}).fetchone()
                                    
                                    if not link_exists:
                                        name_sim = similarity(name_norm or "", normalize_name(row.driver_name or "")) if name_norm else 0
                                        license_match = False
                                        if license_variations and row.driver_license:
                                            scouting_license_norm = normalize_license(row.driver_license)
                                            license_match = scouting_license_norm in license_variations
                                        
                                        match = {
                                            "driver_id": driver_id,
                                            "person_key": str(driver.person_key),
                                            "match_type": "PHONE_EXACT" + ("_LICENSE_EXACT" if license_match else ""),
                                            "source_table": "module_ct_scouting_daily",
                                            "source_pk": source_pk,
                                            "source_id": row.id,
                                            "driver_phone": phone_norm,
                                            "lead_phone": row.driver_phone,
                                            "driver_license": license_norm,
                                            "lead_license": row.driver_license,
                                            "driver_name": name_norm,
                                            "lead_name": row.driver_name,
                                            "name_similarity": name_sim,
                                            "license_match": license_match,
                                            "registration_date": row.registration_date,
                                            "scout_id": row.scout_id,
                                            "confidence": "HIGH" if (license_match or name_sim > 0.7) else "MEDIUM"
                                        }
                                        matches_found.append(match)
                                        matches_by_source["scouting_daily"].append(match)
                                        break  # Solo un match por driver
                                
                                if any(m["driver_id"] == driver_id for m in matches_found):
                                    break
                        
                        # Buscar por licencia si no se encontró por teléfono
                        if not any(m["driver_id"] == driver_id for m in matches_found) and license_variations:
                            for license_var in license_variations:
                                if not license_var:
                                    continue
                                
                                query_scouting_license = text("""
                                    SELECT 
                                        id,
                                        scout_id,
                                        driver_phone,
                                        driver_license,
                                        driver_name,
                                        registration_date,
                                        created_at
                                    FROM public.module_ct_scouting_daily
                                    WHERE driver_license IS NOT NULL
                                    AND UPPER(REPLACE(REPLACE(driver_license, ' ', ''), '-', '')) = :license_norm
                                    LIMIT 20
                                """)
                                
                                result_scouting = db.execute(query_scouting_license, {"license_norm": license_var})
                                scouting_rows = result_scouting.fetchall()
                                
                                for row in scouting_rows:
                                    scouting_license_norm = normalize_license(row.driver_license)
                                    if scouting_license_norm != license_var:
                                        continue
                                    
                                    # Generar source_pk canónico
                                    source_pk_raw = f"{row.scout_id}|{normalize_phone(row.driver_phone)}|{normalize_license(row.driver_license) if row.driver_license else ''}|{row.registration_date}"
                                    source_pk = hashlib.md5(source_pk_raw.encode()).hexdigest()
                                    
                                    # Verificar si ya tiene link
                                    check_link = text("""
                                        SELECT id, person_key
                                        FROM canon.identity_links
                                        WHERE source_table = 'module_ct_scouting_daily'
                                        AND source_pk = :source_pk
                                    """)
                                    link_exists = db.execute(check_link, {"source_pk": source_pk}).fetchone()
                                    
                                    if not link_exists:
                                        name_sim = similarity(name_norm or "", normalize_name(row.driver_name or "")) if name_norm else 0
                                        phone_match = False
                                        if phone_variations and row.driver_phone:
                                            scouting_phone_norm = normalize_phone(row.driver_phone)
                                            phone_match = scouting_phone_norm in phone_variations
                                        
                                        match = {
                                            "driver_id": driver_id,
                                            "person_key": str(driver.person_key),
                                            "match_type": "LICENSE_EXACT" + ("_PHONE_EXACT" if phone_match else ""),
                                            "source_table": "module_ct_scouting_daily",
                                            "source_pk": source_pk,
                                            "source_id": row.id,
                                            "driver_phone": phone_norm,
                                            "lead_phone": row.driver_phone,
                                            "driver_license": license_norm,
                                            "lead_license": row.driver_license,
                                            "driver_name": name_norm,
                                            "lead_name": row.driver_name,
                                            "name_similarity": name_sim,
                                            "license_match": True,
                                            "phone_match": phone_match,
                                            "registration_date": row.registration_date,
                                            "scout_id": row.scout_id,
                                            "confidence": "HIGH" if (phone_match or name_sim > 0.7) else "MEDIUM"
                                        }
                                        matches_found.append(match)
                                        matches_by_source["scouting_daily"].append(match)
                                        break  # Solo un match por driver
                                
                                if any(m["driver_id"] == driver_id for m in matches_found):
                                    break
                
                # 3. BUSCAR EN MIGRATIONS (por driver_id directo)
                if not any(m["driver_id"] == driver_id for m in matches_found):
                    query_migrations = text("""
                        SELECT 
                            id,
                            driver_id,
                            scout_id,
                            created_at,
                            hire_date
                        FROM public.module_ct_migrations
                        WHERE driver_id::text = :driver_id
                        LIMIT 5
                    """)
                    
                    result_migrations = db.execute(query_migrations, {"driver_id": driver_id})
                    migration_rows = result_migrations.fetchall()
                    
                    for row in migration_rows:
                        # Verificar si ya tiene link
                        source_pk = str(row.id)
                        check_link = text("""
                            SELECT id, person_key
                            FROM canon.identity_links
                            WHERE source_table = 'module_ct_migrations'
                            AND source_pk = :source_pk
                        """)
                        link_exists = db.execute(check_link, {"source_pk": source_pk}).fetchone()
                        
                        if not link_exists:
                            match = {
                                "driver_id": driver_id,
                                "person_key": str(driver.person_key),
                                "match_type": "DRIVER_ID_EXACT",
                                "source_table": "module_ct_migrations",
                                "source_pk": source_pk,
                                "source_id": row.id,
                                "migration_driver_id": row.driver_id,
                                "scout_id": row.scout_id,
                                "created_at": row.created_at,
                                "hire_date": row.hire_date,
                                "confidence": "HIGH"
                            }
                            matches_found.append(match)
                            matches_by_source["migrations"].append(match)
                            break  # Solo un match por driver
            
            processed += len(batch)
        
        # Reporte
        print(f"\n{'='*80}")
        print(f"RESULTADOS DE BUSQUEDA EXHAUSTIVA")
        print(f"{'='*80}\n")
        
        print(f"Total de drivers investigados: {len(drivers)}")
        print(f"Total de matches encontrados: {len(matches_found)}")
        print(f"Drivers con matches: {len(set([m['driver_id'] for m in matches_found]))}")
        print(f"Drivers sin matches: {len(drivers) - len(set([m['driver_id'] for m in matches_found]))}")
        
        print(f"\nDesglose por fuente:")
        for source, matches in matches_by_source.items():
            print(f"  - {source}: {len(matches)} matches")
        
        # Muestra de matches
        if matches_found:
            print(f"\n{'='*80}")
            print(f"MUESTRA DE MATCHES ENCONTRADOS (Top 20):")
            print(f"{'='*80}")
            
            for idx, match in enumerate(matches_found[:20], 1):
                print(f"\n{idx}. Driver: {match['driver_id'][:20]}...")
                print(f"   Match Type: {match['match_type']}")
                print(f"   Source: {match['source_table']} (ID: {match['source_id']})")
                print(f"   Confidence: {match['confidence']}")
                
                if match['source_table'] == 'module_ct_cabinet_leads':
                    print(f"   Phone: {match['driver_phone']} == {match['lead_phone']}")
                    if match.get('name_similarity', 0) > 0:
                        print(f"   Name: {match['driver_name']} vs {match['lead_name']} (sim: {match['name_similarity']:.2f})")
                
                elif match['source_table'] == 'module_ct_scouting_daily':
                    if match.get('phone_match') or 'PHONE' in match['match_type']:
                        print(f"   Phone: {match['driver_phone']} == {match['lead_phone']}")
                    if match.get('license_match') or 'LICENSE' in match['match_type']:
                        print(f"   License: {match['driver_license']} == {match['lead_license']}")
                    if match.get('name_similarity', 0) > 0:
                        print(f"   Name: {match['driver_name']} vs {match['lead_name']} (sim: {match['name_similarity']:.2f})")
                
                elif match['source_table'] == 'module_ct_migrations':
                    print(f"   Driver ID Match: {match['driver_id']} == {match['migration_driver_id']}")
                    print(f"   Scout ID: {match['scout_id']}")
        
        print(f"\n{'='*80}")
        print(f"RECOMENDACIONES")
        print(f"{'='*80}\n")
        
        if matches_found:
            print(f"Se encontraron {len(matches_found)} leads que NO tienen links pero deberían tenerlos.")
            print(f"Estos leads pueden ser vinculados a los drivers correspondientes.")
            print(f"\nPróximo paso: Ejecutar create_missing_scouting_links.py o crear script similar")
            print(f"para crear los links faltantes de cabinet_leads y migrations.")
        else:
            print(f"No se encontraron leads adicionales para estos drivers.")
            print(f"Esto confirma que estos drivers realmente no tienen leads asociados.")
        
        print(f"\n{'='*80}\n")
        
        return {
            "total_drivers": len(drivers),
            "matches_found": len(matches_found),
            "drivers_with_matches": len(set([m['driver_id'] for m in matches_found])),
            "matches_by_source": {k: len(v) for k, v in matches_by_source.items()},
            "matches": matches_found
        }
        
    except Exception as e:
        print(f"\nERROR: Error en busqueda exhaustiva: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    exhaustive_search()

