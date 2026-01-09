#!/usr/bin/env python3
"""
Backfill de identity_links para module_ct_scouting_daily

OBJETIVO: Crear identity_links para los 609 registros de scouting_daily con scout_id
que no tienen identity_links, permitiendo que lleguen a lead_ledger.

ESTRATEGIA:
1. Buscar registros de scouting_daily con scout_id que NO tienen identity_links
2. Intentar matching por:
   - driver_license -> canon.drivers_index.license_norm
   - driver_phone (últimos 9 dígitos) -> canon.drivers_index.phone_norm
3. Si encuentra match único, crear identity_link
4. Si encuentra match múltiple, registrar como ambiguous
5. Si no encuentra match, crear person_key nuevo y identity_link

IDEMPOTENTE: Solo crea links si no existen (verifica source_table + source_pk)
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, date
from uuid import uuid4
from typing import Optional, Dict, Any

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.config import settings
from app.models.canon import IdentityLink, IdentityRegistry, ConfidenceLevel
from app.services.normalization import normalize_license, normalize_phone, normalize_phone_pe9
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


def get_scouting_daily_without_links(db: Session) -> list:
    """Obtiene registros de scouting_daily con scout_id que no tienen identity_links"""
    query = text("""
        SELECT 
            sd.id,
            sd.scout_id,
            sd.driver_license,
            sd.driver_phone,
            sd.registration_date,
            sd.created_at
        FROM public.module_ct_scouting_daily sd
        WHERE sd.scout_id IS NOT NULL
            AND NOT EXISTS (
                SELECT 1 FROM canon.identity_links il
                WHERE il.source_table = 'module_ct_scouting_daily'
                    AND il.source_pk = sd.id::TEXT
            )
        ORDER BY sd.registration_date DESC, sd.id DESC
    """)
    
    result = db.execute(query)
    return [dict(row._mapping) for row in result.fetchall()]


def find_driver_by_license(db: Session, license_norm: str) -> Optional[str]:
    """Busca driver_id en drivers_index por license_norm"""
    if not license_norm:
        return None
    
    query = text("""
        SELECT driver_id
        FROM canon.drivers_index
        WHERE license_norm = :license_norm
        LIMIT 1
    """)
    
    result = db.execute(query, {"license_norm": license_norm})
    row = result.fetchone()
    return row.driver_id if row else None


def find_driver_by_phone(db: Session, phone_pe9: str) -> Optional[str]:
    """Busca driver_id en drivers_index por phone (últimos 9 dígitos)"""
    if not phone_pe9:
        return None
    
    query = text("""
        SELECT driver_id
        FROM canon.drivers_index
        WHERE RIGHT(phone_norm, 9) = :phone_pe9
        LIMIT 1
    """)
    
    result = db.execute(query, {"phone_pe9": phone_pe9})
    candidates = result.fetchall()
    
    if len(candidates) == 1:
        return candidates[0].driver_id
    elif len(candidates) > 1:
        # Múltiples matches - retornar None para marcar como ambiguous
        return None
    return None


def get_or_create_person_key(
    db: Session,
    driver_id: Optional[str] = None,
    license_norm: Optional[str] = None,
    phone_norm: Optional[str] = None
) -> Optional[str]:
    """
    Obtiene o crea person_key basado en driver_id o datos disponibles.
    
    Si hay driver_id, busca identity_link existente para ese driver.
    Si no, busca person_key por phone o license.
    Si no encuentra, crea uno nuevo.
    """
    person_key = None
    
    # 1. Si hay driver_id, buscar identity_link existente para ese driver
    if driver_id:
        existing_link = db.query(IdentityLink).filter(
            IdentityLink.source_table == "drivers",
            IdentityLink.source_pk == str(driver_id)
        ).first()
        
        if existing_link:
            return str(existing_link.person_key)
    
    # 2. Buscar person_key existente por phone o license
    if phone_norm:
        existing_person = db.query(IdentityRegistry).filter(
            IdentityRegistry.primary_phone == phone_norm
        ).first()
        if existing_person:
            return str(existing_person.person_key)
    
    if license_norm:
        existing_person = db.query(IdentityRegistry).filter(
            IdentityRegistry.primary_license == license_norm
        ).first()
        if existing_person:
            return str(existing_person.person_key)
    
    # 3. Crear nuevo person_key
    person_key = uuid4()
    person = IdentityRegistry(
        person_key=person_key,
        confidence_level=ConfidenceLevel.MEDIUM,  # MEDIUM porque puede ser nuevo
        primary_phone=phone_norm,
        primary_license=license_norm
    )
    db.add(person)
    db.flush()
    
    return str(person_key)


def create_identity_link(
    db: Session,
    person_key: str,
    source_pk: str,
    snapshot_date: date,
    match_rule: str,
    match_score: int,
    confidence: ConfidenceLevel,
    evidence: Dict[str, Any],
    run_id: Optional[int] = None
) -> IdentityLink:
    """Crea identity_link (idempotente)"""
    # Verificar si ya existe
    existing = db.query(IdentityLink).filter(
        IdentityLink.source_table == "module_ct_scouting_daily",
        IdentityLink.source_pk == source_pk
    ).first()
    
    if existing:
        # Actualizar existente
        existing.person_key = person_key
        existing.match_rule = match_rule
        existing.match_score = match_score
        existing.confidence_level = confidence
        existing.evidence = evidence
        existing.snapshot_date = datetime.combine(snapshot_date, datetime.min.time())
        if run_id:
            existing.run_id = run_id
        return existing
    
    # Crear nuevo
    link = IdentityLink(
        person_key=person_key,
        source_table="module_ct_scouting_daily",
        source_pk=source_pk,
        snapshot_date=datetime.combine(snapshot_date, datetime.min.time()),
        match_rule=match_rule,
        match_score=match_score,
        confidence_level=confidence,
        evidence=evidence,
        run_id=run_id
    )
    db.add(link)
    return link


def process_scouting_record(db: Session, record: Dict[str, Any], stats: Dict[str, int]) -> None:
    """Procesa un registro de scouting_daily para crear identity_link"""
    source_pk = str(record["id"])
    driver_license = record.get("driver_license")
    driver_phone = record.get("driver_phone")
    registration_date = record.get("registration_date")
    
    if isinstance(registration_date, datetime):
        registration_date = registration_date.date()
    elif isinstance(registration_date, str):
        try:
            registration_date = datetime.strptime(registration_date, "%Y-%m-%d").date()
        except:
            registration_date = date.today()
    elif not registration_date:
        registration_date = date.today()
    
    # Normalizar datos
    license_norm = normalize_license(driver_license) if driver_license else None
    phone_norm = normalize_phone(driver_phone) if driver_phone else None
    phone_pe9 = normalize_phone_pe9(driver_phone) if driver_phone else None
    
    driver_id = None
    match_rule = None
    match_score = 0
    confidence = ConfidenceLevel.LOW
    evidence = {
        "source": "scouting_daily",
        "source_pk": source_pk,
        "driver_license": driver_license,
        "driver_phone": driver_phone
    }
    
    # Estrategia de matching: license primero, luego phone
    if license_norm:
        driver_id = find_driver_by_license(db, license_norm)
        if driver_id:
            match_rule = "BACKFILL_LICENSE_MATCH"
            match_score = 80
            confidence = ConfidenceLevel.HIGH
            evidence["match_method"] = "license"
            evidence["license_norm"] = license_norm
            evidence["driver_id_found"] = driver_id
    
    if not driver_id and phone_pe9:
        driver_id = find_driver_by_phone(db, phone_pe9)
        if driver_id:
            match_rule = "BACKFILL_PHONE_MATCH"
            match_score = 70
            confidence = ConfidenceLevel.MEDIUM
            evidence["match_method"] = "phone"
            evidence["phone_pe9"] = phone_pe9
            evidence["driver_id_found"] = driver_id
        elif phone_pe9:
            # Verificar si hay múltiples matches
            query = text("""
                SELECT COUNT(*) as cnt
                FROM canon.drivers_index
                WHERE RIGHT(phone_norm, 9) = :phone_pe9
            """)
            result = db.execute(query, {"phone_pe9": phone_pe9})
            count = result.fetchone().cnt
            if count > 1:
                evidence["phone_ambiguous"] = True
                evidence["phone_candidates_count"] = count
    
    # Obtener o crear person_key
    person_key = get_or_create_person_key(
        db,
        driver_id=driver_id,
        license_norm=license_norm,
        phone_norm=phone_norm
    )
    
    if not person_key:
        stats["errors"] += 1
        logger.warning(f"No se pudo crear person_key para scouting_daily.id={source_pk}")
        return
    
    # Si no hubo match con driver_id, ajustar confidence
    if not driver_id:
        match_rule = "BACKFILL_NEW_PERSON"
        match_score = 50
        confidence = ConfidenceLevel.LOW
        evidence["match_method"] = "new_person"
    
    # Crear identity_link
    try:
        create_identity_link(
            db=db,
            person_key=person_key,
            source_pk=source_pk,
            snapshot_date=registration_date,
            match_rule=match_rule,
            match_score=match_score,
            confidence=confidence,
            evidence=evidence
        )
        
        if driver_id:
            stats["created_with_driver"] += 1
        else:
            stats["created_new_person"] += 1
        
        logger.debug(f"Created identity_link for scouting_daily.id={source_pk}, person_key={person_key}, match_rule={match_rule}")
        
    except Exception as e:
        stats["errors"] += 1
        logger.error(f"Error creating identity_link for scouting_daily.id={source_pk}: {e}", exc_info=True)
        raise


def main():
    """Ejecuta el backfill de identity_links para scouting_daily"""
    stats = {
        "total": 0,
        "created_with_driver": 0,
        "created_new_person": 0,
        "skipped": 0,
        "errors": 0
    }
    
    db = SessionLocal()
    
    try:
        logger.info("="*70)
        logger.info("BACKFILL: Identity Links para scouting_daily")
        logger.info("="*70)
        
        # Obtener registros sin identity_links
        records = get_scouting_daily_without_links(db)
        stats["total"] = len(records)
        
        logger.info(f"Encontrados {stats['total']} registros de scouting_daily sin identity_links")
        
        if stats["total"] == 0:
            logger.info("No hay registros para procesar")
            return stats
        
        # Procesar en batches
        batch_size = 50
        for idx, record in enumerate(records, 1):
            try:
                process_scouting_record(db, record, stats)
                
                if idx % batch_size == 0:
                    db.commit()
                    logger.info(f"Procesados {idx}/{stats['total']} registros...")
            
            except Exception as e:
                logger.error(f"Error procesando registro {record.get('id')}: {e}", exc_info=True)
                db.rollback()
                stats["errors"] += 1
        
        # Commit final
        db.commit()
        
        logger.info("="*70)
        logger.info("RESUMEN FINAL")
        logger.info("="*70)
        logger.info(f"Total procesados: {stats['total']}")
        logger.info(f"Creados con driver match: {stats['created_with_driver']}")
        logger.info(f"Creados con person nuevo: {stats['created_new_person']}")
        logger.info(f"Errores: {stats['errors']}")
        logger.info(f"Total creados: {stats['created_with_driver'] + stats['created_new_person']}")
        
        return stats
        
    except Exception as e:
        logger.error(f"Error en backfill: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

