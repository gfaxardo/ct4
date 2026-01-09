"""
Script de backfill para determinar origen de todas las personas existentes.

Este script:
1. Determina origen de todas las personas en identity_registry
2. Crea registros en canon.identity_origin
3. Detecta violaciones
4. Genera reporte de casos que requieren revisión manual
"""
import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db import SessionLocal
from app.models.canon import (
    IdentityRegistry, IdentityOrigin, IdentityOriginHistory,
    OriginTag, OriginResolutionStatus, DecidedBy
)
from app.services.origin_determination import OriginDeterminationService
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backfill_identity_origin(dry_run: bool = True, batch_size: int = 100):
    """
    Backfill de origen para todas las personas.
    
    Args:
        dry_run: Si True, solo muestra qué haría sin hacer cambios
        batch_size: Tamaño del lote para procesar
    """
    db = SessionLocal()
    service = OriginDeterminationService(db)
    
    try:
        # Obtener todas las personas
        total_persons_query = text("SELECT COUNT(*) as total FROM canon.identity_registry")
        total_persons = db.execute(total_persons_query).scalar() or 0
        
        logger.info(f"Total de personas a procesar: {total_persons}")
        
        # Obtener personas en lotes
        offset = 0
        stats = {
            "processed": 0,
            "created": 0,
            "updated": 0,
            "requires_manual_review": 0,
            "errors": 0
        }
        
        while offset < total_persons:
            persons_query = text(f"""
                SELECT person_key
                FROM canon.identity_registry
                ORDER BY created_at
                LIMIT :limit OFFSET :offset
            """)
            
            persons = db.execute(persons_query, {"limit": batch_size, "offset": offset}).fetchall()
            
            if not persons:
                break
            
            for person_row in persons:
                person_key = person_row.person_key
                stats["processed"] += 1
                
                try:
                    # Determinar origen
                    origin_result = service.determine_origin(person_key)
                    
                    if not origin_result:
                        logger.warning(f"Person {person_key}: No se pudo determinar origen automáticamente")
                        stats["requires_manual_review"] += 1
                        continue
                    
                    if origin_result.requires_manual_review:
                        logger.warning(
                            f"Person {person_key}: Requiere revisión manual - {origin_result.conflict_reason}"
                        )
                        stats["requires_manual_review"] += 1
                        continue
                    
                    # Verificar si ya existe registro
                    existing_origin = db.query(IdentityOrigin).filter(
                        IdentityOrigin.person_key == person_key
                    ).first()
                    
                    if existing_origin:
                        if not dry_run:
                            # Actualizar registro existente si es necesario
                            if existing_origin.origin_tag != origin_result.origin_tag:
                                # Registrar cambio en historial
                                history = IdentityOriginHistory(
                                    person_key=person_key,
                                    origin_tag_old=existing_origin.origin_tag.value if existing_origin.origin_tag else None,
                                    origin_tag_new=origin_result.origin_tag.value,
                                    origin_source_id_old=existing_origin.origin_source_id,
                                    origin_source_id_new=origin_result.origin_source_id,
                                    origin_confidence_old=float(existing_origin.origin_confidence),
                                    origin_confidence_new=origin_result.origin_confidence,
                                    resolution_status_old=existing_origin.resolution_status.value,
                                    resolution_status_new=existing_origin.resolution_status.value,
                                    ruleset_version_old=existing_origin.ruleset_version,
                                    ruleset_version_new=existing_origin.ruleset_version,
                                    changed_by="system",
                                    change_reason="Backfill automático"
                                )
                                db.add(history)
                                
                                existing_origin.origin_tag = origin_result.origin_tag
                                existing_origin.origin_source_id = origin_result.origin_source_id
                                existing_origin.origin_confidence = origin_result.origin_confidence
                                existing_origin.evidence = origin_result.evidence
                                existing_origin.updated_at = datetime.utcnow()
                            
                            stats["updated"] += 1
                        else:
                            logger.info(f"Person {person_key}: Actualizaría origen a {origin_result.origin_tag.value}")
                            stats["updated"] += 1
                    else:
                        if not dry_run:
                            # Crear nuevo registro
                            first_seen_at = service.get_first_seen_at(person_key)
                            
                            # Asegurar que origin_tag sea el enum correcto (no string)
                            origin_tag_enum = origin_result.origin_tag
                            if isinstance(origin_tag_enum, str):
                                origin_tag_enum = OriginTag(origin_tag_enum)
                            
                            origin = IdentityOrigin(
                                person_key=person_key,
                                origin_tag=origin_tag_enum,
                                origin_source_id=origin_result.origin_source_id,
                                origin_confidence=origin_result.origin_confidence,
                                origin_created_at=origin_result.origin_created_at or (first_seen_at or datetime.utcnow()),
                                evidence=origin_result.evidence,
                                decided_by=DecidedBy.SYSTEM,
                                resolution_status=OriginResolutionStatus.RESOLVED_AUTO
                            )
                            db.add(origin)
                            stats["created"] += 1
                        else:
                            logger.info(f"Person {person_key}: Crearía origen {origin_result.origin_tag.value}")
                            stats["created"] += 1
                    
                    if not dry_run and stats["processed"] % 100 == 0:
                        db.commit()
                        logger.info(f"Procesadas {stats['processed']} personas...")
                
                except Exception as e:
                    logger.error(f"Error procesando person {person_key}: {str(e)}")
                    stats["errors"] += 1
                    if not dry_run:
                        db.rollback()
            
            offset += batch_size
        
        if not dry_run:
            db.commit()
        
        # Reporte final
        logger.info("\n" + "="*60)
        logger.info("REPORTE DE BACKFILL")
        logger.info("="*60)
        logger.info(f"Total procesadas: {stats['processed']}")
        logger.info(f"Registros creados: {stats['created']}")
        logger.info(f"Registros actualizados: {stats['updated']}")
        logger.info(f"Requieren revisión manual: {stats['requires_manual_review']}")
        logger.info(f"Errores: {stats['errors']}")
        logger.info("="*60)
        
        if dry_run:
            logger.info("\nMODO DRY RUN - No se hicieron cambios")
            logger.info("Ejecutar con --execute para aplicar cambios")
        
        return stats
    
    except Exception as e:
        logger.error(f"Error en backfill: {str(e)}")
        if not dry_run:
            db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill de origen canónico")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Ejecutar cambios (sin este flag es dry-run)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Tamaño del lote (default: 100)"
    )
    
    args = parser.parse_args()
    
    dry_run = not args.execute
    
    if dry_run:
        logger.info("MODO DRY RUN - No se harán cambios")
    
    backfill_identity_origin(dry_run=dry_run, batch_size=args.batch_size)

