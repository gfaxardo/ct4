"""
Script de Investigación: Drivers sin Leads
===========================================

Investiga si los 980 drivers sin leads tienen coincidencias en las tablas de leads
(cabinet_leads, scouting_daily, migrations) que no fueron procesadas o vinculadas.

Busca coincidencias por:
1. Teléfono normalizado
2. Licencia normalizada
3. Nombre similar
4. Placa (si está disponible)

Genera un reporte detallado de hallazgos.
"""

import sys
import os
import hashlib
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from difflib import SequenceMatcher

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db import SessionLocal
from app.services.normalization import normalize_phone, normalize_name, normalize_license


def similarity(a, b):
    """Calcula similitud entre dos strings"""
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def investigate_drivers_without_leads():
    """
    Investiga si los drivers sin leads tienen coincidencias en tablas de leads.
    """
    db = SessionLocal()
    
    try:
        print(f"\n{'='*80}")
        print(f"INVESTIGACION: Drivers sin Leads - Busqueda en Fuentes Alternativas")
        print(f"{'='*80}\n")
        
        # Paso 1: Obtener todos los drivers sin leads con sus datos
        query_drivers = text("""
            SELECT DISTINCT
                il.source_pk as driver_id,
                ir.person_key,
                ir.primary_phone,
                ir.primary_license,
                ir.primary_full_name,
                il.match_rule,
                il.linked_at
            FROM canon.identity_links il
            JOIN canon.identity_registry ir ON ir.person_key = il.person_key
            WHERE il.source_table = 'drivers'
            AND il.person_key NOT IN (
                SELECT DISTINCT person_key
                FROM canon.identity_links
                WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
            )
        """)
        
        result_drivers = db.execute(query_drivers)
        drivers = result_drivers.fetchall()
        
        print(f"Total de drivers sin leads a investigar: {len(drivers)}\n")
        
        # Paso 2: Buscar coincidencias en cabinet_leads
        print(f"{'='*80}")
        print(f"Buscando coincidencias en module_ct_cabinet_leads...")
        print(f"{'='*80}")
        
        matches_cabinet = []
        
        # Agrupar drivers por teléfono normalizado para búsquedas más eficientes
        drivers_by_phone = {}
        for driver in drivers:
            phone_norm = normalize_phone(driver.primary_phone) if driver.primary_phone else None
            if phone_norm:
                if phone_norm not in drivers_by_phone:
                    drivers_by_phone[phone_norm] = []
                drivers_by_phone[phone_norm].append(driver)
        
        print(f"Buscando coincidencias por {len(drivers_by_phone)} telefonos unicos...")
        
        # Buscar en cabinet_leads usando búsqueda por patrones de teléfono
        # Procesar en lotes de teléfonos
        processed = 0
        for phone_norm, driver_group in drivers_by_phone.items():
            if processed % 100 == 0:
                print(f"  Procesados {processed}/{len(drivers_by_phone)} telefonos...")
            
            # Buscar cabinet_leads que puedan coincidir (usar LIKE para búsqueda rápida)
            # Buscar por los últimos 9 dígitos del teléfono normalizado
            phone_suffix = phone_norm[-9:] if len(phone_norm) >= 9 else phone_norm
            
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
                    park_phone LIKE :phone_pattern1
                    OR park_phone LIKE :phone_pattern2
                    OR park_phone LIKE :phone_pattern3
                )
                LIMIT 100
            """)
            
            # Crear patrones de búsqueda
            phone_pattern1 = f"%{phone_suffix}"
            phone_pattern2 = f"%{phone_norm}"
            phone_pattern3 = phone_norm
            
            result = db.execute(query_cabinet, {
                "phone_pattern1": phone_pattern1,
                "phone_pattern2": phone_pattern2,
                "phone_pattern3": phone_pattern3
            })
            rows = result.fetchall()
            
            for row in rows:
                # Normalizar teléfono del cabinet y verificar match exacto
                cabinet_phone_norm = normalize_phone(row.park_phone) if row.park_phone else None
                if cabinet_phone_norm != phone_norm:
                    continue
                
                # Verificar si ya tiene link
                source_pk = str(row.external_id) if row.external_id else str(row.id)
                check_link = text("""
                    SELECT id
                    FROM canon.identity_links
                    WHERE source_table = 'module_ct_cabinet_leads'
                    AND source_pk = :source_pk
                """)
                link_exists = db.execute(check_link, {"source_pk": source_pk}).fetchone()
                
                if not link_exists:
                    # Procesar cada driver del grupo
                    for driver in driver_group:
                        name_norm = normalize_name(driver.primary_full_name) if driver.primary_full_name else None
                        full_name_cabinet = f"{row.first_name or ''} {row.middle_name or ''} {row.last_name or ''}".strip()
                        name_sim = similarity(name_norm or "", normalize_name(full_name_cabinet)) if name_norm else 0
                        
                        matches_cabinet.append({
                            "driver_id": driver.driver_id,
                            "person_key": str(driver.person_key),
                            "match_type": "PHONE_EXACT",
                            "source_table": "module_ct_cabinet_leads",
                            "source_pk": source_pk,
                            "source_id": row.id,
                            "driver_phone": driver.primary_phone,
                            "cabinet_phone": row.park_phone,
                            "driver_name": driver.primary_full_name,
                            "cabinet_name": full_name_cabinet,
                            "name_similarity": name_sim,
                            "lead_created_at": row.lead_created_at,
                            "plate": row.asset_plate_number
                        })
            
            processed += 1
        
        print(f"Coincidencias encontradas en cabinet_leads: {len(matches_cabinet)}")
        
        # Paso 3: Buscar coincidencias en scouting_daily
        print(f"\n{'='*80}")
        print(f"Buscando coincidencias en module_ct_scouting_daily...")
        print(f"{'='*80}")
        
        matches_scouting = []
        
        # Agrupar drivers por teléfono y licencia normalizados
        drivers_by_phone_scouting = {}
        drivers_by_license_scouting = {}
        
        for driver in drivers:
            phone_norm = normalize_phone(driver.primary_phone) if driver.primary_phone else None
            license_norm = normalize_license(driver.primary_license) if driver.primary_license else None
            
            if phone_norm:
                if phone_norm not in drivers_by_phone_scouting:
                    drivers_by_phone_scouting[phone_norm] = []
                drivers_by_phone_scouting[phone_norm].append(driver)
            
            if license_norm:
                if license_norm not in drivers_by_license_scouting:
                    drivers_by_license_scouting[license_norm] = []
                drivers_by_license_scouting[license_norm].append(driver)
        
        print(f"Buscando coincidencias por {len(drivers_by_phone_scouting)} telefonos y {len(drivers_by_license_scouting)} licencias unicas...")
        
        # Buscar por teléfono
        processed = 0
        for phone_norm, driver_group in drivers_by_phone_scouting.items():
            if processed % 100 == 0:
                print(f"  Procesados {processed}/{len(drivers_by_phone_scouting)} telefonos...")
            
            phone_suffix = phone_norm[-9:] if len(phone_norm) >= 9 else phone_norm
            
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
                    driver_phone LIKE :phone_pattern1
                    OR driver_phone LIKE :phone_pattern2
                    OR driver_phone LIKE :phone_pattern3
                )
                LIMIT 100
            """)
            
            phone_pattern1 = f"%{phone_suffix}"
            phone_pattern2 = f"%{phone_norm}"
            phone_pattern3 = phone_norm
            
            result = db.execute(query_scouting, {
                "phone_pattern1": phone_pattern1,
                "phone_pattern2": phone_pattern2,
                "phone_pattern3": phone_pattern3
            })
            rows = result.fetchall()
            
            for row in rows:
                scouting_phone_norm = normalize_phone(row.driver_phone) if row.driver_phone else None
                if scouting_phone_norm != phone_norm:
                    continue
                
                source_pk_raw = f"{row.scout_id}|{normalize_phone(row.driver_phone)}|{normalize_license(row.driver_license) if row.driver_license else ''}|{row.registration_date}"
                source_pk = hashlib.md5(source_pk_raw.encode()).hexdigest()
                
                check_link = text("""
                    SELECT id
                    FROM canon.identity_links
                    WHERE source_table = 'module_ct_scouting_daily'
                    AND source_pk = :source_pk
                """)
                link_exists = db.execute(check_link, {"source_pk": source_pk}).fetchone()
                
                if not link_exists:
                    for driver in driver_group:
                        name_norm = normalize_name(driver.primary_full_name) if driver.primary_full_name else None
                        license_norm = normalize_license(driver.primary_license) if driver.primary_license else None
                        
                        name_sim = similarity(name_norm or "", normalize_name(row.driver_name or "")) if name_norm else 0
                        license_match = (normalize_license(row.driver_license or "") == license_norm) if (license_norm and row.driver_license) else False
                        
                        matches_scouting.append({
                            "driver_id": driver.driver_id,
                            "person_key": str(driver.person_key),
                            "match_type": "PHONE_EXACT" + ("_LICENSE_EXACT" if license_match else ""),
                            "source_table": "module_ct_scouting_daily",
                            "source_pk": source_pk,
                            "source_id": row.id,
                            "driver_phone": driver.primary_phone,
                            "scouting_phone": row.driver_phone,
                            "driver_license": driver.primary_license,
                            "scouting_license": row.driver_license,
                            "driver_name": driver.primary_full_name,
                            "scouting_name": row.driver_name,
                            "name_similarity": name_sim,
                            "license_match": license_match,
                            "registration_date": row.registration_date,
                            "scout_id": row.scout_id
                        })
            
            processed += 1
        
        # Buscar por licencia (solo para drivers que no tienen match por teléfono)
        drivers_with_phone_match = set([m["driver_id"] for m in matches_scouting])
        processed = 0
        for license_norm, driver_group in drivers_by_license_scouting.items():
            # Filtrar drivers que ya tienen match por teléfono
            driver_group_filtered = [d for d in driver_group if d.driver_id not in drivers_with_phone_match]
            if not driver_group_filtered:
                continue
            
            if processed % 100 == 0:
                print(f"  Procesados {processed}/{len(drivers_by_license_scouting)} licencias...")
            
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
                LIMIT 100
            """)
            
            result = db.execute(query_scouting_license, {"license_norm": license_norm})
            rows = result.fetchall()
            
            for row in rows:
                scouting_license_norm = normalize_license(row.driver_license) if row.driver_license else None
                if scouting_license_norm != license_norm:
                    continue
                
                source_pk_raw = f"{row.scout_id}|{normalize_phone(row.driver_phone)}|{normalize_license(row.driver_license) if row.driver_license else ''}|{row.registration_date}"
                source_pk = hashlib.md5(source_pk_raw.encode()).hexdigest()
                
                check_link = text("""
                    SELECT id
                    FROM canon.identity_links
                    WHERE source_table = 'module_ct_scouting_daily'
                    AND source_pk = :source_pk
                """)
                link_exists = db.execute(check_link, {"source_pk": source_pk}).fetchone()
                
                if not link_exists:
                    for driver in driver_group_filtered:
                        name_norm = normalize_name(driver.primary_full_name) if driver.primary_full_name else None
                        phone_norm = normalize_phone(driver.primary_phone) if driver.primary_phone else None
                        
                        name_sim = similarity(name_norm or "", normalize_name(row.driver_name or "")) if name_norm else 0
                        phone_match = (normalize_phone(row.driver_phone or "") == phone_norm) if (phone_norm and row.driver_phone) else False
                        
                        matches_scouting.append({
                            "driver_id": driver.driver_id,
                            "person_key": str(driver.person_key),
                            "match_type": "LICENSE_EXACT" + ("_PHONE_EXACT" if phone_match else ""),
                            "source_table": "module_ct_scouting_daily",
                            "source_pk": source_pk,
                            "source_id": row.id,
                            "driver_phone": driver.primary_phone,
                            "scouting_phone": row.driver_phone,
                            "driver_license": driver.primary_license,
                            "scouting_license": row.driver_license,
                            "driver_name": driver.primary_full_name,
                            "scouting_name": row.driver_name,
                            "name_similarity": name_sim,
                            "license_match": True,
                            "registration_date": row.registration_date,
                            "scout_id": row.scout_id
                        })
            
            processed += 1
        
        print(f"Coincidencias encontradas en scouting_daily: {len(matches_scouting)}")
        
        # Paso 4: Buscar coincidencias en migrations
        print(f"\n{'='*80}")
        print(f"Buscando coincidencias en module_ct_migrations...")
        print(f"{'='*80}")
        
        matches_migrations = []
        
        # Agrupar drivers por driver_id para búsqueda más eficiente
        driver_ids = [str(driver.driver_id) for driver in drivers]
        
        print(f"Buscando coincidencias en migrations para {len(driver_ids)} drivers...")
        
        # Buscar en migrations por driver_id directo (procesar en lotes)
        batch_size = 100
        for i in range(0, len(driver_ids), batch_size):
            batch = driver_ids[i:i+batch_size]
            
            if i % 500 == 0:
                print(f"  Procesados {i}/{len(driver_ids)} drivers...")
            
            # Crear query con múltiples driver_ids usando tupla
            placeholders = ','.join([f':driver_id_{j}' for j in range(len(batch))])
            query_migrations = text(f"""
                SELECT 
                    id,
                    driver_id,
                    scout_id,
                    created_at,
                    hire_date
                FROM public.module_ct_migrations
                WHERE driver_id::text IN ({placeholders})
                ORDER BY created_at DESC
            """)
            
            params = {f"driver_id_{j}": driver_id for j, driver_id in enumerate(batch)}
            result = db.execute(query_migrations, params)
            rows = result.fetchall()
            
            # Crear mapa de driver_id a driver para lookup rápido
            drivers_map = {str(driver.driver_id): driver for driver in drivers}
            
            for row in rows:
                driver_id_str = str(row.driver_id)
                if driver_id_str not in drivers_map:
                    continue
                
                driver = drivers_map[driver_id_str]
                
                # Verificar si ya tiene link
                source_pk = str(row.id)
                check_link = text("""
                    SELECT id
                    FROM canon.identity_links
                    WHERE source_table = 'module_ct_migrations'
                    AND source_pk = :source_pk
                """)
                link_exists = db.execute(check_link, {"source_pk": source_pk}).fetchone()
                
                if not link_exists:
                    matches_migrations.append({
                        "driver_id": driver_id_str,
                        "person_key": str(driver.person_key),
                        "match_type": "DRIVER_ID_EXACT",
                        "source_table": "module_ct_migrations",
                        "source_pk": source_pk,
                        "source_id": row.id,
                        "migration_driver_id": row.driver_id,
                        "scout_id": row.scout_id,
                        "created_at": row.created_at,
                        "hire_date": row.hire_date
                    })
        
        print(f"Coincidencias encontradas en migrations: {len(matches_migrations)}")
        
        # Paso 5: Generar reporte
        print(f"\n{'='*80}")
        print(f"REPORTE DE INVESTIGACION")
        print(f"{'='*80}\n")
        
        total_matches = len(matches_cabinet) + len(matches_scouting) + len(matches_migrations)
        drivers_with_matches = len(set([m["driver_id"] for m in matches_cabinet + matches_scouting + matches_migrations]))
        drivers_without_matches = len(drivers) - drivers_with_matches
        
        print(f"Total de drivers investigados: {len(drivers)}")
        print(f"Total de coincidencias encontradas: {total_matches}")
        print(f"Drivers con coincidencias: {drivers_with_matches}")
        print(f"Drivers sin coincidencias: {drivers_without_matches}")
        print(f"\nDesglose por fuente:")
        print(f"  - Cabinet Leads: {len(matches_cabinet)} coincidencias")
        print(f"  - Scouting Daily: {len(matches_scouting)} coincidencias")
        print(f"  - Migrations: {len(matches_migrations)} coincidencias")
        
        # Muestra de coincidencias
        if matches_cabinet:
            print(f"\n{'='*80}")
            print(f"Muestra de Coincidencias en Cabinet Leads (Top 10):")
            print(f"{'='*80}")
            for idx, match in enumerate(matches_cabinet[:10], 1):
                print(f"\n{idx}. Driver: {match['driver_id'][:20]}...")
                print(f"   Match: {match['match_type']}")
                print(f"   Cabinet ID: {match['source_id']} (external_id: {match['source_pk']})")
                print(f"   Telefono: {match['driver_phone']} == {match['cabinet_phone']}")
                if match['name_similarity'] > 0:
                    print(f"   Nombre: {match['driver_name']} vs {match['cabinet_name']} (sim: {match['name_similarity']:.2f})")
                print(f"   Lead creado: {match['lead_created_at']}")
        
        if matches_scouting:
            print(f"\n{'='*80}")
            print(f"Muestra de Coincidencias en Scouting Daily (Top 10):")
            print(f"{'='*80}")
            for idx, match in enumerate(matches_scouting[:10], 1):
                print(f"\n{idx}. Driver: {match['driver_id'][:20]}...")
                print(f"   Match: {match['match_type']}")
                print(f"   Scouting ID: {match['source_id']}")
                print(f"   Telefono: {match['driver_phone']} == {match['scouting_phone']}")
                if match.get('license_match'):
                    print(f"   Licencia: {match['driver_license']} == {match['scouting_license']}")
                if match['name_similarity'] > 0:
                    print(f"   Nombre: {match['driver_name']} vs {match['scouting_name']} (sim: {match['name_similarity']:.2f})")
                print(f"   Registration: {match['registration_date']}")
        
        if matches_migrations:
            print(f"\n{'='*80}")
            print(f"Muestra de Coincidencias en Migrations (Top 10):")
            print(f"{'='*80}")
            for idx, match in enumerate(matches_migrations[:10], 1):
                print(f"\n{idx}. Driver: {match['driver_id'][:20]}...")
                print(f"   Match: {match['match_type']}")
                print(f"   Migration ID: {match['source_id']}")
                print(f"   Driver ID: {match['migration_driver_id']}")
                print(f"   Scout ID: {match['scout_id']}")
                print(f"   Creado: {match['created_at']}")
        
        # Guardar resultados en archivo JSON
        results = {
            "investigation_date": datetime.now().isoformat(),
            "total_drivers_investigated": len(drivers),
            "total_matches_found": total_matches,
            "drivers_with_matches": drivers_with_matches,
            "drivers_without_matches": drivers_without_matches,
            "matches_cabinet": matches_cabinet,
            "matches_scouting": matches_scouting,
            "matches_migrations": matches_migrations
        }
        
        output_file = project_root / "scripts" / "investigation_results.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str, ensure_ascii=False)
        
        print(f"\n{'='*80}")
        print(f"Resultados guardados en: {output_file}")
        print(f"{'='*80}\n")
        
        return results
        
    except Exception as e:
        print(f"\nERROR: Error en investigacion: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    investigate_drivers_without_leads()

