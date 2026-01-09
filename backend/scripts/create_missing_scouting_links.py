"""
Script de Creación: Links Faltantes de Scouting
===============================================

Crea los links faltantes de identity_links para los drivers que tienen
coincidencias en scouting_daily pero no tienen el link correspondiente.

Basado en los resultados de investigate_drivers_without_leads.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime
from uuid import UUID

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db import SessionLocal
from app.models.canon import IdentityLink, IdentityRegistry
from app.models.canon import ConfidenceLevel


def create_missing_scouting_links(dry_run: bool = True, limit: int = None):
    """
    Crea los links faltantes de scouting basado en investigation_results.json
    """
    db = SessionLocal()
    
    try:
        print(f"\n{'='*80}")
        print(f"CREACION DE LINKS FALTANTES DE SCOUTING")
        print(f"{'='*80}\n")
        
        if dry_run:
            print("MODO DRY-RUN: No se harán cambios en la base de datos\n")
        else:
            print("MODO EJECUCION: Se crearán los links en la base de datos\n")
        
        # Cargar resultados de investigación
        results_file = project_root / "scripts" / "investigation_results.json"
        if not results_file.exists():
            print(f"ERROR: No se encuentra el archivo {results_file}")
            print("Ejecuta primero investigate_drivers_without_leads.py")
            return
        
        with open(results_file, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        matches_scouting = results.get("matches_scouting", [])
        
        if limit:
            matches_scouting = matches_scouting[:limit]
            print(f"Limitando a {limit} matches\n")
        
        print(f"Total de matches a procesar: {len(matches_scouting)}\n")
        
        links_to_create = []
        errors = []
        
        for idx, match in enumerate(matches_scouting, 1):
            person_key_str = match["person_key"]
            source_pk = match["source_pk"]
            source_id = match["source_id"]
            match_type = match["match_type"]
            registration_date = match["registration_date"]
            
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
                IdentityLink.source_table == "module_ct_scouting_daily",
                IdentityLink.source_pk == source_pk
            ).first()
            
            if existing_link:
                print(f"  [{idx}/{len(matches_scouting)}] Link ya existe para scouting ID {source_id}, saltando...")
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
                confidence = ConfidenceLevel.HIGH
            else:
                match_rule = "SCOUTING_MATCH"
                match_score = 85
                confidence = ConfidenceLevel.MEDIUM
            
            # Crear evidence
            evidence = {
                "match_type": match_type,
                "driver_id": match["driver_id"],
                "scouting_id": source_id,
                "scout_id": match.get("scout_id"),
                "license_match": match.get("license_match", False),
                "name_similarity": match.get("name_similarity", 0),
                "driver_phone": match.get("driver_phone"),
                "scouting_phone": match.get("scouting_phone"),
                "driver_license": match.get("driver_license"),
                "scouting_license": match.get("scouting_license"),
                "investigation_date": results.get("investigation_date")
            }
            
            # Parsear registration_date
            try:
                snapshot_date = datetime.strptime(registration_date, "%Y-%m-%d").date()
            except:
                snapshot_date = datetime.now().date()
            
            links_to_create.append({
                "person_key": person_key_uuid,
                "source_table": "module_ct_scouting_daily",
                "source_pk": source_pk,
                "snapshot_date": snapshot_date,
                "match_rule": match_rule,
                "match_score": match_score,
                "confidence_level": confidence,
                "evidence": evidence,
                "source_id": source_id
            })
            
            if idx % 10 == 0:
                print(f"  Procesados {idx}/{len(matches_scouting)} matches...")
        
        print(f"\n{'='*80}")
        print(f"RESUMEN")
        print(f"{'='*80}\n")
        print(f"Total de matches procesados: {len(matches_scouting)}")
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
                print(f"\n  Scouting ID: {link['source_id']}")
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
                        # Verificar nuevamente antes de crear (por si acaso cambió)
                        existing_link = db.query(IdentityLink).filter(
                            IdentityLink.source_table == link["source_table"],
                            IdentityLink.source_pk == link["source_pk"]
                        ).first()
                        
                        if existing_link:
                            skipped += 1
                            if skipped % 10 == 0:
                                print(f"  Saltados {skipped} links existentes...")
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
                        db.flush()  # Hacer flush después de cada link para detectar errores temprano
                        created += 1
                        
                        if created % 10 == 0:
                            print(f"  Creados {created}/{len(links_to_create)} links...")
                    
                    except Exception as e:
                        db.rollback()
                        error_msg = str(e)
                        if "UniqueViolation" in error_msg or "uq_identity_links_source" in error_msg:
                            skipped += 1
                            if skipped % 10 == 0:
                                print(f"  Saltados {skipped} links existentes...")
                        else:
                            errors.append({
                                "source_id": link["source_id"],
                                "error": error_msg
                            })
                            print(f"  ERROR al crear link para scouting ID {link['source_id']}: {error_msg}")
                
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
            "total_matches": len(matches_scouting),
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
    
    parser = argparse.ArgumentParser(description="Crear links faltantes de scouting")
    parser.add_argument("--execute", action="store_true", help="Ejecutar cambios (sin esto es dry-run)")
    parser.add_argument("--limit", type=int, help="Limitar número de matches a procesar")
    
    args = parser.parse_args()
    
    create_missing_scouting_links(dry_run=not args.execute, limit=args.limit)

