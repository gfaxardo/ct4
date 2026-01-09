"""
Crear Links Faltantes Adicionales Encontrados en Búsqueda Exhaustiva
=====================================================================

Crea los links faltantes encontrados en la búsqueda exhaustiva.
Basado en los resultados de exhaustive_search_leads_for_drivers.py
"""

import sys
import json
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


def create_additional_links(dry_run: bool = True):
    """
    Crea los links faltantes encontrados en la búsqueda exhaustiva
    """
    db = SessionLocal()
    
    try:
        print(f"\n{'='*80}")
        print(f"CREACION DE LINKS FALTANTES ADICIONALES")
        print(f"{'='*80}\n")
        
        if dry_run:
            print("MODO DRY-RUN: No se harán cambios en la base de datos\n")
        else:
            print("MODO EJECUCION: Se crearán los links en la base de datos\n")
        
        # Ejecutar búsqueda exhaustiva para obtener matches
        print("Ejecutando búsqueda exhaustiva...")
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "exhaustive_search", 
            project_root / "scripts" / "exhaustive_search_leads_for_drivers.py"
        )
        exhaustive_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(exhaustive_module)
        results = exhaustive_module.exhaustive_search()
        
        matches = results.get("matches", [])
        
        if not matches:
            print("No se encontraron matches adicionales para crear links.")
            return
        
        print(f"\nTotal de matches a procesar: {len(matches)}\n")
        
        links_to_create = []
        errors = []
        
        for idx, match in enumerate(matches, 1):
            person_key_str = match["person_key"]
            source_pk = match["source_pk"]
            source_id = match["source_id"]
            match_type = match["match_type"]
            source_table = match["source_table"]
            confidence_str = match.get("confidence", "MEDIUM")
            
            # Verificar que el person_key existe
            person_key_uuid = UUID(person_key_str)
            person = db.query(IdentityRegistry).filter(
                IdentityRegistry.person_key == person_key_uuid
            ).first()
            
            if not person:
                errors.append({
                    "match": idx,
                    "person_key": person_key_str,
                    "error": "Person key no existe en identity_registry"
                })
                continue
            
            # Verificar que el link no existe ya
            existing_link = db.query(IdentityLink).filter(
                IdentityLink.source_table == source_table,
                IdentityLink.source_pk == source_pk
            ).first()
            
            if existing_link:
                print(f"  [{idx}/{len(matches)}] Link ya existe para {source_table} ID {source_id}, saltando...")
                continue
            
            # Determinar match_rule, score y confidence basado en match_type
            if "LICENSE_EXACT" in match_type and "PHONE_EXACT" in match_type:
                match_rule = "R1_R2_PHONE_LICENSE_EXACT"
                match_score = 95
                confidence = ConfidenceLevel.HIGH
            elif "LICENSE_EXACT" in match_type:
                match_rule = "R2_LICENSE_EXACT"
                match_score = 92
                confidence = ConfidenceLevel.HIGH
            elif "PHONE_EXACT" in match_type:
                match_rule = "R1_PHONE_EXACT"
                match_score = 95
                confidence = ConfidenceLevel.HIGH if confidence_str == "HIGH" else ConfidenceLevel.MEDIUM
            elif "DRIVER_ID_EXACT" in match_type:
                match_rule = "DRIVER_ID_EXACT"
                match_score = 100
                confidence = ConfidenceLevel.HIGH
            else:
                match_rule = "EXHAUSTIVE_SEARCH_MATCH"
                match_score = 85
                confidence = ConfidenceLevel.MEDIUM
            
            # Crear evidence
            evidence = {
                "match_type": match_type,
                "driver_id": match["driver_id"],
                "source_id": source_id,
                "confidence": confidence_str,
                "found_by": "exhaustive_search"
            }
            
            if source_table == "module_ct_scouting_daily":
                evidence.update({
                    "scout_id": match.get("scout_id"),
                    "registration_date": str(match.get("registration_date")),
                    "name_similarity": match.get("name_similarity", 0),
                    "license_match": match.get("license_match", False),
                    "phone_match": match.get("phone_match", False)
                })
            elif source_table == "module_ct_cabinet_leads":
                evidence.update({
                    "lead_created_at": str(match.get("lead_created_at")),
                    "name_similarity": match.get("name_similarity", 0)
                })
            elif source_table == "module_ct_migrations":
                evidence.update({
                    "scout_id": match.get("scout_id"),
                    "hire_date": str(match.get("hire_date")) if match.get("hire_date") else None
                })
            
            # Parsear fecha
            snapshot_date = None
            if source_table == "module_ct_scouting_daily" and match.get("registration_date"):
                try:
                    snapshot_date = datetime.strptime(str(match["registration_date"]), "%Y-%m-%d").date()
                except:
                    snapshot_date = datetime.now().date()
            elif source_table == "module_ct_cabinet_leads" and match.get("lead_created_at"):
                try:
                    if isinstance(match["lead_created_at"], datetime):
                        snapshot_date = match["lead_created_at"].date()
                    else:
                        snapshot_date = datetime.strptime(str(match["lead_created_at"]), "%Y-%m-%d").date()
                except:
                    snapshot_date = datetime.now().date()
            elif source_table == "module_ct_migrations" and match.get("hire_date"):
                try:
                    if isinstance(match["hire_date"], datetime):
                        snapshot_date = match["hire_date"].date()
                    else:
                        snapshot_date = datetime.strptime(str(match["hire_date"]), "%Y-%m-%d").date()
                except:
                    snapshot_date = datetime.now().date()
            else:
                snapshot_date = datetime.now().date()
            
            links_to_create.append({
                "person_key": person_key_uuid,
                "source_table": source_table,
                "source_pk": source_pk,
                "snapshot_date": snapshot_date,
                "match_rule": match_rule,
                "match_score": match_score,
                "confidence_level": confidence,
                "evidence": evidence,
                "source_id": source_id
            })
            
            if idx % 10 == 0:
                print(f"  Procesados {idx}/{len(matches)} matches...")
        
        print(f"\n{'='*80}")
        print(f"RESUMEN")
        print(f"{'='*80}\n")
        print(f"Total de matches procesados: {len(matches)}")
        print(f"Links a crear: {len(links_to_create)}")
        print(f"Errores: {len(errors)}")
        
        if errors:
            print(f"\nErrores encontrados:")
            for error in errors[:10]:
                print(f"  - Match {error['match']}: {error['error']}")
            if len(errors) > 10:
                print(f"  ... y {len(errors) - 10} más")
        
        if links_to_create:
            print(f"\n{'='*80}")
            print(f"Muestra de Links a Crear (Top 10):")
            print(f"{'='*80}")
            for link in links_to_create[:10]:
                print(f"\n  {link['source_table']} ID: {link['source_id']}")
                print(f"  Person Key: {link['person_key']}")
                print(f"  Source PK: {link['source_pk']}")
                print(f"  Match Rule: {link['match_rule']}")
                print(f"  Score: {link['match_score']}")
                print(f"  Confidence: {link['confidence_level']}")
                print(f"  Snapshot Date: {link['snapshot_date']}")
            
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
                        db.flush()  # Hacer flush después de cada link
                        created += 1
                        
                        if created % 5 == 0:
                            print(f"  Creados {created}/{len(links_to_create)} links...")
                    
                    except Exception as e:
                        db.rollback()
                        error_msg = str(e)
                        if "UniqueViolation" in error_msg or "uq_identity_links_source" in error_msg:
                            skipped += 1
                        else:
                            errors.append({
                                "source_id": link["source_id"],
                                "error": error_msg
                            })
                            print(f"  ERROR al crear link para {link['source_table']} ID {link['source_id']}: {error_msg}")
                
                if created > 0:
                    db.commit()
                    print(f"\nOK: {created} links creados exitosamente")
                    if skipped > 0:
                        print(f"INFO: {skipped} links ya existían y fueron saltados")
                else:
                    print(f"\nWARNING: No se crearon links nuevos")
                    if skipped > 0:
                        print(f"INFO: {skipped} links ya existían")
            else:
                print(f"\nTIP: Para crear estos links, ejecuta con --execute")
        
        print(f"\n{'='*80}\n")
        
        return {
            "total_matches": len(matches),
            "links_to_create": len(links_to_create),
            "errors": len(errors),
            "dry_run": dry_run
        }
        
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
    
    parser = argparse.ArgumentParser(description="Crear links faltantes adicionales")
    parser.add_argument("--execute", action="store_true", help="Ejecutar cambios (sin esto es dry-run)")
    
    args = parser.parse_args()
    
    create_additional_links(dry_run=not args.execute)

