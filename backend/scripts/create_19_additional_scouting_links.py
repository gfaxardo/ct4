"""
Crear los 19 Links Adicionales de Scouting Encontrados
=======================================================

Crea los 19 links de scouting_daily encontrados en la búsqueda exhaustiva.
Estos son casos donde el teléfono del driver tiene código de país (51) 
pero el teléfono del scouting solo tiene los últimos 9 dígitos.
"""

import sys
from pathlib import Path
from datetime import datetime
from uuid import UUID
import hashlib

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db import SessionLocal
from app.models.canon import IdentityLink, IdentityRegistry
from app.models.canon import ConfidenceLevel
from app.services.normalization import normalize_phone, normalize_license


# Los 19 matches encontrados en la búsqueda exhaustiva
MATCHES = [
    {"driver_id": "9c52da4fcf6346f8a1cd", "scouting_id": 466, "scout_id": None, "registration_date": None},
    {"driver_id": "2c7d5f3560bd4270855e", "scouting_id": 358, "scout_id": None, "registration_date": None},
    {"driver_id": "698bf004e2024b9e9e99", "scouting_id": 426, "scout_id": None, "registration_date": None},
    {"driver_id": "6c7861c571134fa29783", "scouting_id": 314, "scout_id": None, "registration_date": None},
    {"driver_id": "989bc62b48714cdbbfeb", "scouting_id": 425, "scout_id": None, "registration_date": None},
    {"driver_id": "043877c723504ac88961", "scouting_id": 300, "scout_id": None, "registration_date": None},
    {"driver_id": "08be64656df84fe2b7a9", "scouting_id": 195, "scout_id": None, "registration_date": None},
    {"driver_id": "56d9779efdf940268718", "scouting_id": 331, "scout_id": None, "registration_date": None},
    {"driver_id": "b9a8bb7a6a9848e68c7e", "scouting_id": 305, "scout_id": None, "registration_date": None},
    {"driver_id": "bafd24b3c82b4a37b956", "scouting_id": 284, "scout_id": None, "registration_date": None},
    {"driver_id": "db23bced580f4b7a8974", "scouting_id": 194, "scout_id": None, "registration_date": None},
    {"driver_id": "21766ad66f12487eb2b9", "scouting_id": 133, "scout_id": None, "registration_date": None},
    {"driver_id": "26f735e099ff4eb6af3d", "scouting_id": 16, "scout_id": None, "registration_date": None},
    {"driver_id": "503b0143ab634bc0baa1", "scouting_id": 86, "scout_id": None, "registration_date": None},
    {"driver_id": "6f2590c0125749ecbfbd", "scouting_id": 15, "scout_id": None, "registration_date": None},
    {"driver_id": "7e04afd75d73430cae4b", "scouting_id": 19, "scout_id": None, "registration_date": None},
    {"driver_id": "7fe32d1303ed471a9be7", "scouting_id": 85, "scout_id": None, "registration_date": None},
    {"driver_id": "b13e474f0a1641e7949b", "scouting_id": 46, "scout_id": None, "registration_date": None},
    {"driver_id": "cdeb2b6d5226491b85d0", "scouting_id": 167, "scout_id": None, "registration_date": None},
]


def create_links(dry_run: bool = True):
    """
    Crea los 19 links adicionales de scouting
    """
    db = SessionLocal()
    
    try:
        print(f"\n{'='*80}")
        print(f"CREACION DE 19 LINKS ADICIONALES DE SCOUTING")
        print(f"{'='*80}\n")
        
        if dry_run:
            print("MODO DRY-RUN: No se harán cambios en la base de datos\n")
        else:
            print("MODO EJECUCION: Se crearán los links en la base de datos\n")
        
        links_to_create = []
        
        # Obtener información completa de cada match
        for match_info in MATCHES:
            driver_id_partial = match_info["driver_id"]
            scouting_id = match_info["scouting_id"]
            
            # Buscar el driver completo
            query_driver = text("""
                SELECT 
                    il.source_pk as driver_id,
                    ir.person_key,
                    ir.primary_phone,
                    ir.primary_license,
                    ir.primary_full_name
                FROM canon.identity_links il
                JOIN canon.identity_registry ir ON ir.person_key = il.person_key
                WHERE il.source_table = 'drivers'
                AND il.source_pk LIKE :driver_id_pattern
                LIMIT 1
            """)
            
            result_driver = db.execute(query_driver, {"driver_id_pattern": f"{driver_id_partial}%"})
            driver = result_driver.fetchone()
            
            if not driver:
                print(f"  WARNING: No se encontró driver con ID parcial {driver_id_partial}")
                continue
            
            driver_id = driver.driver_id
            person_key = driver.person_key
            
            # Obtener información del scouting
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
                WHERE id = :scouting_id
                LIMIT 1
            """)
            
            result_scouting = db.execute(query_scouting, {"scouting_id": scouting_id})
            scouting = result_scouting.fetchone()
            
            if not scouting:
                print(f"  WARNING: No se encontró scouting con ID {scouting_id}")
                continue
            
            # Generar source_pk canónico
            source_pk_raw = f"{scouting.scout_id}|{normalize_phone(scouting.driver_phone)}|{normalize_license(scouting.driver_license) if scouting.driver_license else ''}|{scouting.registration_date}"
            source_pk = hashlib.md5(source_pk_raw.encode()).hexdigest()
            
            # Verificar si ya tiene link
            check_link = text("""
                SELECT id, person_key
                FROM canon.identity_links
                WHERE source_table = 'module_ct_scouting_daily'
                AND source_pk = :source_pk
            """)
            link_exists = db.execute(check_link, {"source_pk": source_pk}).fetchone()
            
            if link_exists:
                print(f"  [{len(links_to_create)+1}/19] Link ya existe para scouting ID {scouting_id}, saltando...")
                continue
            
            # Determinar match_rule y confidence
            phone_match = normalize_phone(scouting.driver_phone) == normalize_phone(driver.primary_phone) if (scouting.driver_phone and driver.primary_phone) else False
            license_match = normalize_license(scouting.driver_license) == normalize_license(driver.primary_license) if (scouting.driver_license and driver.primary_license) else False
            
            if phone_match and license_match:
                match_rule = "R1_R2_PHONE_LICENSE_EXACT"
                match_score = 95
                confidence = ConfidenceLevel.HIGH
            elif phone_match:
                match_rule = "R1_PHONE_EXACT"
                match_score = 95
                confidence = ConfidenceLevel.HIGH
            elif license_match:
                match_rule = "R2_LICENSE_EXACT"
                match_score = 92
                confidence = ConfidenceLevel.HIGH
            else:
                match_rule = "PHONE_EXACT_EXHAUSTIVE"
                match_score = 90
                confidence = ConfidenceLevel.MEDIUM
            
            # Parsear fecha
            try:
                snapshot_date = datetime.strptime(str(scouting.registration_date), "%Y-%m-%d").date()
            except:
                snapshot_date = datetime.now().date()
            
            # Crear evidence
            evidence = {
                "match_type": "PHONE_EXACT_EXHAUSTIVE",
                "driver_id": driver_id,
                "scouting_id": scouting_id,
                "scout_id": scouting.scout_id,
                "phone_match": phone_match,
                "license_match": license_match,
                "found_by": "exhaustive_search",
                "driver_phone": driver.primary_phone,
                "scouting_phone": scouting.driver_phone
            }
            
            links_to_create.append({
                "person_key": person_key,
                "source_table": "module_ct_scouting_daily",
                "source_pk": source_pk,
                "snapshot_date": snapshot_date,
                "match_rule": match_rule,
                "match_score": match_score,
                "confidence_level": confidence,
                "evidence": evidence,
                "scouting_id": scouting_id,
                "driver_id": driver_id
            })
        
        print(f"\n{'='*80}")
        print(f"RESUMEN")
        print(f"{'='*80}\n")
        print(f"Total de matches a procesar: {len(MATCHES)}")
        print(f"Links a crear: {len(links_to_create)}")
        
        if links_to_create:
            print(f"\n{'='*80}")
            print(f"Muestra de Links a Crear (Top 10):")
            print(f"{'='*80}")
            for link in links_to_create[:10]:
                print(f"\n  Scouting ID: {link['scouting_id']}")
                print(f"  Driver ID: {link['driver_id'][:20]}...")
                print(f"  Person Key: {link['person_key']}")
                print(f"  Match Rule: {link['match_rule']}")
                print(f"  Score: {link['match_score']}")
                print(f"  Confidence: {link['confidence_level']}")
            
            if len(links_to_create) > 10:
                print(f"\n  ... y {len(links_to_create) - 10} más")
            
            if not dry_run:
                print(f"\n{'='*80}")
                print(f"CREANDO LINKS EN LA BASE DE DATOS...")
                print(f"{'='*80}\n")
                
                created = 0
                skipped = 0
                for link in links_to_create:
                    try:
                        # Verificar nuevamente antes de crear
                        existing_link = db.query(IdentityLink).filter(
                            IdentityLink.source_table == link["source_table"],
                            IdentityLink.source_pk == link["source_pk"]
                        ).first()
                        
                        if existing_link:
                            skipped += 1
                            continue
                        
                        new_link = IdentityLink(
                            person_key=link["person_key"],
                            source_table=link["source_table"],
                            source_pk=link["source_pk"],
                            snapshot_date=link["snapshot_date"],
                            match_rule=link["match_rule"],
                            match_score=link["match_score"],
                            confidence_level=link["confidence_level"],
                            evidence=link["evidence"]
                        )
                        db.add(new_link)
                        db.flush()
                        created += 1
                        
                        print(f"  Creado link para scouting ID {link['scouting_id']} ({created}/{len(links_to_create)})")
                    
                    except Exception as e:
                        db.rollback()
                        error_msg = str(e)
                        if "UniqueViolation" in error_msg or "uq_identity_links_source" in error_msg:
                            skipped += 1
                        else:
                            print(f"  ERROR al crear link para scouting ID {link['scouting_id']}: {error_msg}")
                
                if created > 0:
                    db.commit()
                    print(f"\nOK: {created} links creados exitosamente")
                    if skipped > 0:
                        print(f"INFO: {skipped} links ya existían y fueron saltados")
                else:
                    print(f"\nWARNING: No se crearon links nuevos")
            else:
                print(f"\nTIP: Para crear estos links, ejecuta con --execute")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"\nERROR: Error en creacion de links: {e}")
        import traceback
        traceback.print_exc()
        if not dry_run:
            db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Crear 19 links adicionales de scouting")
    parser.add_argument("--execute", action="store_true", help="Ejecutar cambios (sin esto es dry-run)")
    
    args = parser.parse_args()
    
    create_links(dry_run=not args.execute)

