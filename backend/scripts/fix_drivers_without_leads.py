"""
Script de Limpieza: Corregir Drivers sin Leads con Sistema de Cuarentena
========================================================================

Este script corrige los drivers que están en el sistema sin leads asociados
utilizando un sistema de cuarentena para mantener auditabilidad.

Estrategia:
1. Identifica drivers sin leads (excluyendo ya en cuarentena)
2. Para drivers con lead_events: crea links faltantes y marca como resolved_relinked
3. Para drivers sin lead_events: inserta en quarantine como quarantined
4. Genera reporte JSON + CSV con totales, ejemplos e IDs

IMPORTANTE: Este script es DRY RUN por defecto.
Usar --execute para aplicar los cambios.
"""

import sys
import os
import argparse
import json
import csv
from pathlib import Path
from datetime import datetime
from uuid import UUID

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db import SessionLocal
from app.models.canon import (
    IdentityLink, 
    IdentityRegistry, 
    ConfidenceLevel,
    DriverOrphanQuarantine,
    OrphanDetectedReason,
    OrphanStatus
)
from app.services.normalization import normalize_phone, normalize_license
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_drivers_without_leads(db, exclude_quarantined=True):
    """
    Encuentra drivers que no tienen leads asociados.
    Por defecto excluye drivers ya en cuarentena (excepto purged).
    """
    exclude_query = ""
    if exclude_quarantined:
        exclude_query = """
        AND il.source_pk NOT IN (
            SELECT driver_id 
            FROM canon.driver_orphan_quarantine 
            WHERE status IN ('quarantined', 'resolved_relinked', 'resolved_created_lead')
        )
        """
    
    query = text(f"""
        SELECT DISTINCT
            il.person_key,
            il.source_pk as driver_id,
            il.match_rule as creation_rule,
            il.linked_at,
            il.evidence,
            ir.primary_phone,
            ir.primary_license,
            ir.primary_full_name
        FROM canon.identity_links il
        JOIN canon.identity_registry ir ON ir.person_key = il.person_key
        WHERE il.source_table = 'drivers'
        AND il.person_key NOT IN (
            SELECT DISTINCT person_key
            FROM canon.identity_links
            WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
        )
        {exclude_query}
    """)
    
    result = db.execute(query)
    return result.fetchall()


def extract_driver_id_from_payload(payload_json):
    """
    Extrae driver_id de payload_json usando múltiples estrategias.
    Retorna el driver_id encontrado o None.
    """
    if not payload_json:
        return None
    
    # Estrategia 1: driver_id directo
    driver_id = payload_json.get('driver_id') or payload_json.get('driverId') or payload_json.get('id')
    if driver_id:
        return str(driver_id).strip()
    
    # Estrategia 2: Objeto driver anidado
    driver_obj = payload_json.get('driver')
    if driver_obj and isinstance(driver_obj, dict):
        driver_id = driver_obj.get('driver_id') or driver_obj.get('driverId') or driver_obj.get('id')
        if driver_id:
            return str(driver_id).strip()
    
    return None


def find_driver_id_by_license_or_phone(db, driver_license=None, driver_phone=None):
    """
    Busca driver_id usando license o phone desde drivers_index o identity_links.
    Retorna el driver_id encontrado o None.
    """
    # Normalizar inputs
    if driver_license:
        driver_license = str(driver_license).strip().upper()
    if driver_phone:
        driver_phone = str(driver_phone).strip().replace('-', '').replace(' ', '')
    
    if not driver_license and not driver_phone:
        return None
    
    # Estrategia 1: Buscar en drivers_index (más directo)
    query_drivers_index = text("""
        SELECT DISTINCT driver_id
        FROM canon.drivers_index
        WHERE (:license IS NULL OR license_norm = :license)
           OR (:phone IS NULL OR phone_norm = :phone)
        LIMIT 1
    """)
    result = db.execute(query_drivers_index, {
        "license": driver_license,
        "phone": driver_phone
    })
    row = result.fetchone()
    if row:
        return str(row.driver_id)
    
    # Estrategia 2: Buscar en identity_links -> identity_registry
    query_identity = text("""
        SELECT DISTINCT il.source_pk as driver_id
        FROM canon.identity_links il
        JOIN canon.identity_registry ir ON ir.person_key = il.person_key
        WHERE il.source_table = 'drivers'
          AND (
              (:license IS NULL OR ir.primary_license = :license)
           OR (:phone IS NULL OR ir.primary_phone = :phone)
          )
        LIMIT 1
    """)
    result = db.execute(query_identity, {
        "license": driver_license,
        "phone": driver_phone
    })
    row = result.fetchone()
    if row:
        return str(row.driver_id)
    
    return None


def find_lead_events_for_driver_with_evidence(db, driver_id):
    """
    Encuentra lead_events asociados a un driver con jerarquía de evidencia.
    
    Retorna lista de dicts con:
    - event_id, source_table, source_pk, event_date, payload_json, created_at
    - match_strategy: 'driver_id_direct', 'license_exact', 'phone_exact', 'both_exact'
    - evidence_level: 1 (fuerte), 2 (media), 3 (débil)
    """
    driver_id = str(driver_id).strip()
    events_found = []  # Lista de dicts con evidencia
    
    # EVIDENCIA NIVEL 1 (fuerte): driver_id directo
    query_direct = text("""
        SELECT 
            le.id,
            le.source_table,
            le.source_pk,
            le.event_date,
            le.payload_json,
            le.created_at,
            'driver_id_direct' as match_strategy,
            1 as evidence_level
        FROM observational.lead_events le
        WHERE le.payload_json->>'driver_id' = :driver_id
           OR le.payload_json->>'driverId' = :driver_id
           OR le.payload_json->>'id' = :driver_id
           OR (le.payload_json->'driver'->>'driver_id') = :driver_id
           OR (le.payload_json->'driver'->>'driverId') = :driver_id
           OR (le.payload_json->'driver'->>'id') = :driver_id
        ORDER BY le.event_date DESC, le.created_at DESC
        LIMIT 20
    """)
    result = db.execute(query_direct, {"driver_id": driver_id})
    for row in result:
        events_found.append({
            "event_id": row.id,
            "source_table": row.source_table,
            "source_pk": row.source_pk,
            "event_date": row.event_date,
            "payload_json": row.payload_json,
            "created_at": row.created_at,
            "match_strategy": row.match_strategy,
            "evidence_level": row.evidence_level
        })
    
    # Estrategia 2: Buscar por license/phone en payload y mapear a driver_id
    # Obtener license/phone del driver desde múltiples fuentes
    driver_license_norm = None
    driver_phone_norm = None
    
    # Intentar desde drivers_index primero
    query_driver_info_idx = text("""
        SELECT license_norm, phone_norm
        FROM canon.drivers_index
        WHERE driver_id = :driver_id
        LIMIT 1
    """)
    result = db.execute(query_driver_info_idx, {"driver_id": driver_id})
    driver_info = result.fetchone()
    
    if driver_info:
        driver_license_norm = driver_info.license_norm
        driver_phone_norm = driver_info.phone_norm
    
    # Si no se encontró, buscar en public.drivers y normalizar
    if not driver_license_norm and not driver_phone_norm:
        query_driver_info_raw = text("""
            SELECT license_number, license_normalized_number, phone
            FROM public.drivers
            WHERE driver_id::text = :driver_id
            LIMIT 1
        """)
        result = db.execute(query_driver_info_raw, {"driver_id": driver_id})
        driver_raw = result.fetchone()
        
        if driver_raw:
            # Normalizar license (usar normalized si existe, sino normalizar el raw)
            license_raw = driver_raw.license_normalized_number or driver_raw.license_number
            if license_raw:
                driver_license_norm = normalize_license(str(license_raw))
            
            # Normalizar phone
            if driver_raw.phone:
                driver_phone_norm = normalize_phone(str(driver_raw.phone))
    
    # Si aún no se encontró, buscar en identity_registry vía identity_links
    if not driver_license_norm and not driver_phone_norm:
        query_driver_info_registry = text("""
            SELECT ir.primary_license, ir.primary_phone
            FROM canon.identity_registry ir
            JOIN canon.identity_links il ON il.person_key = ir.person_key
            WHERE il.source_table = 'drivers'
              AND il.source_pk = :driver_id
            LIMIT 1
        """)
        result = db.execute(query_driver_info_registry, {"driver_id": driver_id})
        driver_registry = result.fetchone()
        
        if driver_registry:
            if driver_registry.primary_license:
                driver_license_norm = normalize_license(str(driver_registry.primary_license))
            if driver_registry.primary_phone:
                driver_phone_norm = normalize_phone(str(driver_registry.primary_phone))
    
    # EVIDENCIA NIVEL 2 (media): license/phone normalizado con SQL regexp_replace
    # Obtener license/phone del driver usando query SQL normalizado
    query_driver_normalized = text("""
        WITH driver_info AS (
            SELECT 
                :driver_id as driver_id,
                COALESCE(
                    di.license_norm,
                    UPPER(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                        COALESCE(d.license_normalized_number::text, d.license_number::text),
                        '[^A-Z0-9]', '', 'g'
                    ), ' ', '', 'g'), '-', '', 'g'))
                ) as license_norm,
                COALESCE(
                    di.phone_norm,
                    REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                        d.phone::text,
                        '[^0-9]', '', 'g'
                    ), ' ', '', 'g'), '-', '', 'g'), '\\(', '', 'g')
                ) as phone_norm
            FROM (SELECT :driver_id as driver_id) q
            LEFT JOIN canon.drivers_index di ON di.driver_id = q.driver_id
            LEFT JOIN public.drivers d ON d.driver_id::text = q.driver_id
            LIMIT 1
        )
        SELECT license_norm, phone_norm
        FROM driver_info
        WHERE license_norm IS NOT NULL OR phone_norm IS NOT NULL
    """)
    
    result = db.execute(query_driver_normalized, {"driver_id": driver_id})
    driver_norm_row = result.fetchone()
    
    if driver_norm_row and (driver_norm_row.license_norm or driver_norm_row.phone_norm):
        # Buscar eventos con match exacto normalizado (SQL puro)
        query_license_phone_match = text("""
            WITH driver_normalized AS (
                SELECT 
                    :driver_id as driver_id,
                    :license_norm as license_norm,
                    :phone_norm as phone_norm
            ),
            events_normalized AS (
                SELECT 
                    le.id,
                    le.source_table,
                    le.source_pk,
                    le.event_date,
                    le.payload_json,
                    le.created_at,
                    CASE 
                        WHEN le.payload_json->>'driver_license' IS NOT NULL THEN
                            UPPER(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                                le.payload_json->>'driver_license',
                                '[^A-Z0-9]', '', 'g'
                            ), ' ', '', 'g'), '-', '', 'g'))
                        ELSE NULL
                    END as event_license_norm,
                    CASE 
                        WHEN le.payload_json->>'driver_phone' IS NOT NULL THEN
                            REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                                le.payload_json->>'driver_phone',
                                '[^0-9]', '', 'g'
                            ), ' ', '', 'g'), '-', '', 'g'), '\\(', '', 'g')
                        ELSE NULL
                    END as event_phone_norm
                FROM observational.lead_events le
                WHERE le.source_table = 'module_ct_scouting_daily'
                  AND le.payload_json IS NOT NULL
                  AND (le.payload_json ? 'driver_license' OR le.payload_json ? 'driver_phone')
            ),
            matches AS (
                SELECT 
                    en.id,
                    en.source_table,
                    en.source_pk,
                    en.event_date,
                    en.payload_json,
                    en.created_at,
                    CASE 
                        WHEN dn.license_norm IS NOT NULL 
                             AND dn.phone_norm IS NOT NULL 
                             AND en.event_license_norm IS NOT NULL 
                             AND en.event_phone_norm IS NOT NULL 
                             AND dn.license_norm = en.event_license_norm 
                             AND dn.phone_norm = en.event_phone_norm THEN 'both_exact'
                        WHEN dn.license_norm IS NOT NULL 
                             AND en.event_license_norm IS NOT NULL 
                             AND dn.license_norm = en.event_license_norm THEN 'license_exact'
                        WHEN dn.phone_norm IS NOT NULL 
                             AND en.event_phone_norm IS NOT NULL 
                             AND dn.phone_norm = en.event_phone_norm THEN 'phone_exact'
                        ELSE NULL
                    END as match_strategy,
                    2 as evidence_level
                FROM driver_normalized dn
                CROSS JOIN events_normalized en
                WHERE (
                    (dn.license_norm IS NOT NULL 
                     AND en.event_license_norm IS NOT NULL 
                     AND dn.license_norm = en.event_license_norm)
                    OR
                    (dn.phone_norm IS NOT NULL 
                     AND en.event_phone_norm IS NOT NULL 
                     AND dn.phone_norm = en.event_phone_norm)
                )
            )
            SELECT *
            FROM matches
            WHERE match_strategy IS NOT NULL
            ORDER BY event_date DESC, created_at DESC
            LIMIT 20
        """)
        
        result = db.execute(query_license_phone_match, {
            "driver_id": driver_id,
            "license_norm": driver_norm_row.license_norm,
            "phone_norm": driver_norm_row.phone_norm
        })
        
        for row in result:
            # Evitar duplicados si ya fue encontrado por driver_id
            if not any(e["event_id"] == row.id for e in events_found):
                events_found.append({
                    "event_id": row.id,
                    "source_table": row.source_table,
                    "source_pk": row.source_pk,
                    "event_date": row.event_date,
                    "payload_json": row.payload_json,
                    "created_at": row.created_at,
                    "match_strategy": row.match_strategy,
                    "evidence_level": row.evidence_level
                })
    
    # EVIDENCIA NIVEL 3 (débil): Buscar por person_key (solo para contexto, no resuelve)
    query_person_key = text("""
        SELECT person_key
        FROM canon.identity_links
        WHERE source_table = 'drivers'
          AND source_pk = :driver_id
        LIMIT 1
    """)
    result = db.execute(query_person_key, {"driver_id": driver_id})
    person_key_row = result.fetchone()
    
    if person_key_row:
        person_key = person_key_row.person_key
        existing_ids = [e["event_id"] for e in events_found]
        
        if existing_ids:
            query_by_person = text("""
                SELECT 
                    le.id,
                    le.source_table,
                    le.source_pk,
                    le.event_date,
                    le.payload_json,
                    le.created_at,
                    'person_key_match' as match_strategy,
                    3 as evidence_level
                FROM observational.lead_events le
                WHERE le.person_key = :person_key
                  AND le.id != ALL(:existing_ids)
                ORDER BY le.event_date DESC, le.created_at DESC
                LIMIT 10
            """)
            result = db.execute(query_by_person, {
                "person_key": person_key,
                "existing_ids": existing_ids
            })
        else:
            query_by_person = text("""
                SELECT 
                    le.id,
                    le.source_table,
                    le.source_pk,
                    le.event_date,
                    le.payload_json,
                    le.created_at,
                    'person_key_match' as match_strategy,
                    3 as evidence_level
                FROM observational.lead_events le
                WHERE le.person_key = :person_key
                ORDER BY le.event_date DESC, le.created_at DESC
                LIMIT 10
            """)
            result = db.execute(query_by_person, {"person_key": person_key})
        
        for row in result:
            if not any(e["event_id"] == row.id for e in events_found):
                events_found.append({
                    "event_id": row.id,
                    "source_table": row.source_table,
                    "source_pk": row.source_pk,
                    "event_date": row.event_date,
                    "payload_json": row.payload_json,
                    "created_at": row.created_at,
                    "match_strategy": row.match_strategy,
                    "evidence_level": row.evidence_level
                })
    
    return events_found


def find_lead_events_for_driver(db, driver_id):
    """
    Wrapper para mantener compatibilidad con código existente.
    Retorna lista de objetos Row con los mismos campos que antes.
    """
    events_with_evidence = find_lead_events_for_driver_with_evidence(db, driver_id)
    
    if not events_with_evidence:
        return []
    
    # Convertir a formato Row-like para compatibilidad
    class EventRow:
        def __init__(self, data):
            self.id = data["event_id"]
            self.source_table = data["source_table"]
            self.source_pk = data["source_pk"]
            self.event_date = data["event_date"]
            self.payload_json = data["payload_json"]
            self.created_at = data["created_at"]
            self.match_strategy = data.get("match_strategy")
            self.evidence_level = data.get("evidence_level")
    
    return [EventRow(e) for e in events_with_evidence]


def find_existing_lead_link(db, person_key, source_table, source_pk):
    """Verifica si ya existe un link de lead para esta persona"""
    query = text("""
        SELECT id
        FROM canon.identity_links
        WHERE person_key = :person_key
        AND source_table = :source_table
        AND source_pk = :source_pk
    """)
    
    result = db.execute(query, {
        "person_key": person_key,
        "source_table": source_table,
        "source_pk": source_pk
    })
    
    return result.fetchone() is not None


def create_lead_link_from_event(db, person_key, event, dry_run=True):
    """
    Crea un link de lead basado en un lead_event.
    
    Para migrations, el source_pk debería ser el id de module_ct_migrations.
    Para cabinet/scouting, debería ser el external_id o id correspondiente.
    """
    source_table = event.source_table
    payload = event.payload_json or {}
    
    # Si el evento ya tiene source_pk, usarlo directamente
    if event.source_pk:
        source_pk = event.source_pk
    else:
        # Determinar source_pk según el tipo de lead
        if source_table == 'module_ct_migrations':
            source_pk = payload.get('id') or payload.get('source_pk')
            if not source_pk:
                # Intentar obtener desde la tabla original
                query = text("""
                    SELECT id::text
                    FROM public.module_ct_migrations
                    WHERE driver_id::text = :driver_id
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                result = db.execute(query, {"driver_id": payload.get('driver_id')})
                row = result.fetchone()
                source_pk = str(row.id) if row else None
        elif source_table == 'module_ct_cabinet_leads':
            source_pk = payload.get('external_id') or payload.get('id')
        elif source_table == 'module_ct_scouting_daily':
            # Para scouting, el source_pk es un hash generado
            source_pk = payload.get('source_pk') or payload.get('id')
        else:
            source_pk = payload.get('id') or payload.get('source_pk')
    
    if not source_pk:
        return None, f"No se pudo determinar source_pk para {source_table}"
    
    # Verificar si ya existe el link (por source_table y source_pk únicamente)
    try:
        if find_existing_lead_link(db, person_key, source_table, str(source_pk)):
            return None, f"Link ya existe para {source_table}:{source_pk}"
    except Exception as e:
        # Si hay error en la verificación, intentar crear de todas formas
        # La constraint única de la BD lo protegerá
        logger.warning(f"Error verificando link existente para {source_table}:{source_pk}: {e}")
    
    if dry_run:
        return {
            "person_key": str(person_key),
            "source_table": source_table,
            "source_pk": str(source_pk),
            "event_id": event.id,
            "event_date": str(event.event_date) if event.event_date else None
        }, None
    
    # Crear el link
    try:
        link = IdentityLink(
            person_key=person_key,
            source_table=source_table,
            source_pk=str(source_pk),
            snapshot_date=event.event_date if event.event_date else datetime.utcnow(),
            match_rule="LEAD_EVENT_RECONSTRUCTION",
            match_score=100,
            confidence_level=ConfidenceLevel.HIGH,
            evidence={
                "created_by": "fix_drivers_without_leads",
                "event_id": event.id,
                "event_date": str(event.event_date) if event.event_date else None,
                "reconstructed_from": "lead_events",
                "original_event_source_pk": str(event.source_pk) if event.source_pk else None
            },
            run_id=None
        )
        db.add(link)
        db.flush()
        
        return {
            "person_key": str(person_key),
            "source_table": source_table,
            "source_pk": str(source_pk),
            "link_id": link.id
        }, None
        
    except Exception as e:
        logger.error(f"Error creando link para {source_table}:{source_pk}: {e}")
        return None, f"Error creando link: {str(e)}"


def upsert_quarantine_record(
    db, 
    driver_id, 
    person_key, 
    detected_reason, 
    creation_rule, 
    evidence_json,
    status=OrphanStatus.QUARANTINED,
    resolution_notes=None,
    dry_run=True
):
    """Inserta o actualiza un registro en quarantine"""
    
    if dry_run:
        return {
            "driver_id": driver_id,
            "person_key": str(person_key) if person_key else None,
            "detected_reason": detected_reason.value if isinstance(detected_reason, OrphanDetectedReason) else detected_reason,
            "creation_rule": creation_rule,
            "status": status.value if isinstance(status, OrphanStatus) else status,
            "evidence_json": evidence_json
        }, None
    
    try:
        # Buscar registro existente
        existing = db.query(DriverOrphanQuarantine).filter(
            DriverOrphanQuarantine.driver_id == driver_id
        ).first()
        
        if existing:
            # Actualizar registro existente
            existing.status = status
            existing.resolved_at = datetime.utcnow() if status != OrphanStatus.QUARANTINED else None
            existing.resolution_notes = resolution_notes
            existing.evidence_json = evidence_json or existing.evidence_json
        else:
            # Crear nuevo registro
            existing = DriverOrphanQuarantine(
                driver_id=driver_id,
                person_key=person_key,
                detected_reason=detected_reason,
                creation_rule=creation_rule,
                evidence_json=evidence_json,
                status=status,
                resolved_at=datetime.utcnow() if status != OrphanStatus.QUARANTINED else None,
                resolution_notes=resolution_notes
            )
            db.add(existing)
        
        db.flush()
        return {"driver_id": driver_id, "status": status.value if hasattr(status, 'value') else str(status)}, None
        
    except Exception as e:
        logger.error(f"Error en quarantine para {driver_id}: {e}")
        db.rollback()
        return None, f"Error en quarantine: {str(e)}"


def reprocess_quarantined_drivers(dry_run=True, limit=None, output_dir=None):
    """
    Reprocesa drivers en cuarentena para buscar eventos usando la lógica corregida.
    Si se encuentran eventos, crea links faltantes y actualiza status a resolved_relinked.
    """
    db = SessionLocal()
    
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = Path.cwd() / "output"
        output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_json_path = output_path / f"reprocess_quarantined_{timestamp}.json"
    report_csv_path = output_path / f"reprocess_quarantined_{timestamp}.csv"
    
    try:
        print(f"\n{'='*80}")
        print(f"REPROCESO: Drivers en Cuarentena (Búsqueda Mejorada de Eventos)")
        print(f"{'='*80}")
        print(f"Modo: {'DRY RUN (solo lectura)' if dry_run else 'EJECUTAR (aplicar cambios)'}")
        if limit:
            print(f"Límite: {limit} drivers")
        print(f"Directorio de salida: {output_path}")
        print(f"{'='*80}\n")
        
        # Obtener drivers en cuarentena
        query_base = """
            SELECT 
                dq.driver_id,
                dq.person_key,
                dq.detected_reason,
                dq.creation_rule,
                dq.evidence_json,
                dq.detected_at,
                il.match_rule as original_creation_rule
            FROM canon.driver_orphan_quarantine dq
            LEFT JOIN canon.identity_links il ON (
                il.source_table = 'drivers' 
                AND il.source_pk = dq.driver_id
            )
            WHERE dq.status = 'quarantined'
            ORDER BY dq.detected_at DESC
        """
        
        if limit:
            query_base += f"\n            LIMIT {limit}"
        
        query_quarantine = text(query_base)
        result = db.execute(query_quarantine)
        quarantined_drivers = result.fetchall()
        
        print(f"Total de drivers en cuarentena encontrados: {len(quarantined_drivers)}\n")
        
        stats = {
            "processed": 0,
            "with_events": 0,
            "without_events": 0,
            "links_created": 0,
            "links_skipped": 0,
            "resolved_relinked": 0,
            "errors": 0
        }
        
        report_data = {
            "timestamp": timestamp,
            "dry_run": dry_run,
            "mode": "reprocess_quarantined",
            "stats": stats,
            "drivers": []
        }
        
        # Si no hay drivers en cuarentena, retornar
        if not quarantined_drivers:
            print("[INFO] No hay drivers en cuarentena para reprocesar")
            return report_data
        
        for driver_row in quarantined_drivers:
            stats["processed"] += 1
            driver_id = driver_row.driver_id
            person_key = driver_row.person_key
            creation_rule = driver_row.creation_rule or driver_row.original_creation_rule
            evidence = driver_row.evidence_json or {}
            
            driver_report = {
                "driver_id": driver_id,
                "person_key": str(person_key) if person_key else None,
                "creation_rule": creation_rule,
                "previous_status": "quarantined",
                "lead_events_count": 0,
                "matched_event_count": 0,
                "match_strategy": None,
                "action": None,
                "status": None,
                "detected_driver_id_path": None,
                "matched_source_table": None,
                "matched_event_sample_ids": [],
                "normalized_event_license": None,
                "normalized_event_phone": None,
                "error": None
            }
            
            # Buscar eventos usando la lógica corregida con jerarquía de evidencia
            try:
                events_with_evidence = find_lead_events_for_driver_with_evidence(db, driver_id)
            except Exception as e:
                logger.error(f"Error buscando lead_events para {driver_id}: {e}")
                db.rollback()
                events_with_evidence = []
                stats["errors"] += 1
                driver_report["error"] = str(e)
                report_data["drivers"].append(driver_report)
                continue
            
            driver_report["lead_events_count"] = len(events_with_evidence)
            
            # Filtrar eventos por nivel de evidencia (solo NIVEL 1 y 2 resuelven)
            events_strong_evidence = [e for e in events_with_evidence if e.get("evidence_level", 3) <= 2]
            events_weak_evidence = [e for e in events_with_evidence if e.get("evidence_level", 3) == 3]
            
            # Determinar match_strategy principal (priorizar NIVEL 1)
            if events_strong_evidence:
                primary_strategy = events_strong_evidence[0].get("match_strategy", "unknown")
                driver_report["match_strategy"] = primary_strategy
            elif events_weak_evidence:
                primary_strategy = events_weak_evidence[0].get("match_strategy", "ambiguous")
                driver_report["match_strategy"] = primary_strategy
            else:
                primary_strategy = "none"
                driver_report["match_strategy"] = "none"
            
            # Guardar IDs de eventos para reporte
            driver_report["matched_event_count"] = len(events_strong_evidence) if events_strong_evidence else 0
            driver_report["matched_event_sample_ids"] = [e["event_id"] for e in events_strong_evidence[:3]]
            
            # Usar eventos con evidencia fuerte para procesamiento
            events = events_strong_evidence if events_strong_evidence else []
            
            if not events:
                # Sin eventos con evidencia fuerte
                if events_weak_evidence:
                    # Tiene evidencia débil - marcar como ambiguous pero no resolver
                    stats["without_events"] += 1
                    driver_report["action"] = "skipped_ambiguous"
                    driver_report["status"] = "quarantined"
                    driver_report["match_strategy"] = "ambiguous"
                    
                    # Actualizar detected_reason si aplica
                    if driver_row.detected_reason == OrphanDetectedReason.NO_LEAD_NO_EVENTS:
                        # Actualizar pero mantener en cuarentena
                        resolution_notes = "Found weak evidence (person_key match) but no strong evidence (driver_id or license/phone exact). Keeping quarantined."
                        quarantine_data, error = upsert_quarantine_record(
                            db=db,
                            driver_id=driver_id,
                            person_key=person_key,
                            detected_reason=driver_row.detected_reason,
                            creation_rule=creation_rule,
                            evidence_json={**evidence, "weak_evidence_events": [e["event_id"] for e in events_weak_evidence[:5]]},
                            status=OrphanStatus.QUARANTINED,  # Mantener en cuarentena
                            resolution_notes=resolution_notes,
                            dry_run=dry_run
                        )
                else:
                    # Sin eventos - dejar intacto
                    stats["without_events"] += 1
                    driver_report["action"] = "skipped"
                    driver_report["status"] = "quarantined"
                    driver_report["match_strategy"] = "none"
            else:
                # HAY eventos con evidencia fuerte (NIVEL 1 o 2) - crear links
                stats["with_events"] += 1
                events_used = []
                links_created_count = 0
                
                # Determinar source_table principal del evento
                if events:
                    driver_report["matched_source_table"] = events[0]["source_table"]
                
                # Procesar eventos según jerarquía (priorizar NIVEL 1)
                events_sorted = sorted(events, key=lambda x: (x.get("evidence_level", 3), x.get("event_date") or datetime.min), reverse=True)
                
                for event_data in events_sorted:
                    # Convertir dict a objeto Row-like para compatibilidad
                    class EventRow:
                        def __init__(self, data):
                            self.id = data["event_id"]
                            self.source_table = data["source_table"]
                            self.source_pk = data["source_pk"]
                            self.event_date = data["event_date"]
                            self.payload_json = data["payload_json"]
                            self.created_at = data["created_at"]
                            self.match_strategy = data.get("match_strategy")
                            self.evidence_level = data.get("evidence_level")
                    
                    event = EventRow(event_data)
                    # Si no tenemos person_key, intentar obtenerlo del driver
                    if not person_key:
                        query_person = text("""
                            SELECT person_key
                            FROM canon.identity_links
                            WHERE source_table = 'drivers'
                              AND source_pk = :driver_id
                            LIMIT 1
                        """)
                        result = db.execute(query_person, {"driver_id": driver_id})
                        person_row = result.fetchone()
                        if person_row:
                            person_key = person_row.person_key
                    
                    # Si aún no tenemos person_key, no podemos crear links
                    if not person_key:
                        logger.warning(f"Driver {driver_id} no tiene person_key, no se pueden crear links")
                        continue
                    
                    # Solo crear links si evidencia es NIVEL 1 o 2
                    if event.evidence_level <= 2:
                        try:
                            link_data, error = create_lead_link_from_event(
                                db, person_key, event, dry_run=dry_run
                            )
                            
                            if error:
                                if "ya existe" not in error.lower() and "unique" not in error.lower():
                                    logger.warning(f"Driver {driver_id}: {error}")
                                    db.rollback()  # Rollback después de error
                                else:
                                    # Link ya existe - esto es OK
                                    stats["links_skipped"] += 1
                            elif link_data:
                                links_created_count += 1
                                stats["links_created"] += 1
                            events_used.append({
                                "event_id": event.id,
                                "source_table": event.source_table,
                                "source_pk": link_data.get("source_pk"),
                                "match_strategy": event.match_strategy,
                                "evidence_level": event.evidence_level
                            })
                            
                            # Guardar información de normalización en evidencia
                            payload = event.payload_json or {}
                            if event.match_strategy in ["license_exact", "phone_exact", "both_exact"]:
                                driver_report["detected_driver_id_path"] = f"via_{event.match_strategy}_normalized"
                                # Obtener valores normalizados para reporte (masked)
                                if payload.get('driver_license'):
                                    lic = str(payload.get('driver_license'))
                                    driver_report["normalized_event_license"] = lic[:3] + "***" + lic[-2:] if len(lic) > 5 else "***"
                                if payload.get('driver_phone'):
                                    ph = str(payload.get('driver_phone'))
                                    driver_report["normalized_event_phone"] = ph[:3] + "***" + ph[-2:] if len(ph) > 5 else "***"
                            elif event.match_strategy == "driver_id_direct":
                                driver_report["detected_driver_id_path"] = "payload_json.driver_id"
                            
                            if not driver_report.get("matched_source_table"):
                                driver_report["matched_source_table"] = event.source_table
                        except Exception as e:
                            logger.error(f"Error procesando evento {event.id} para driver {driver_id}: {e}", exc_info=True)
                            db.rollback()  # Rollback después de excepción
                            stats["links_skipped"] += 1
                
                evidence["lead_events_used"] = events_used
                evidence["match_strategy"] = primary_strategy
                evidence["evidence_level"] = min([e.get("evidence_level", 3) for e in events]) if events else None
                
                if links_created_count > 0:
                    # Se crearon links - determinar status según evidencia
                    if primary_strategy == "driver_id_direct":
                        # EVIDENCIA NIVEL 1: resolved_relinked
                        new_status = OrphanStatus.RESOLVED_RELINKED
                        resolution_notes = f"Relinked from {links_created_count} lead_event(s) with strong evidence (driver_id direct). Match strategy: {primary_strategy}. Reprocessed from quarantine."
                    elif primary_strategy in ["license_exact", "phone_exact", "both_exact"]:
                        # EVIDENCIA NIVEL 2: resolved_relinked (o resolved_created_lead si aplica)
                        new_status = OrphanStatus.RESOLVED_RELINKED
                        resolution_notes = f"Relinked from {links_created_count} lead_event(s) with medium evidence (normalized license/phone match). Match strategy: {primary_strategy}. Reprocessed from quarantine."
                    else:
                        # Fallback (no debería llegar aquí)
                        new_status = OrphanStatus.RESOLVED_RELINKED
                        resolution_notes = f"Relinked from {links_created_count} lead_event(s). Match strategy: {primary_strategy}. Reprocessed from quarantine."
                    
                    quarantine_data, error = upsert_quarantine_record(
                        db=db,
                        driver_id=driver_id,
                        person_key=person_key,
                        detected_reason=driver_row.detected_reason,
                        creation_rule=creation_rule,
                        evidence_json=evidence,
                        status=new_status,
                        resolution_notes=resolution_notes,
                        dry_run=dry_run
                    )
                    
                    if error:
                        stats["errors"] += 1
                        driver_report["error"] = error
                    else:
                        stats["resolved_relinked"] += 1
                        driver_report["action"] = "resolved_relinked"
                        driver_report["status"] = new_status.value if hasattr(new_status, 'value') else str(new_status)
                        driver_report["links_created"] = links_created_count
                else:
                    # No se pudieron crear links - mantener en cuarentena
                    if events_weak_evidence:
                        driver_report["action"] = "skipped_weak_evidence_only"
                        driver_report["status"] = "quarantined"
                    else:
                        driver_report["action"] = "skipped_no_links_created"
                        driver_report["status"] = "quarantined"
            
            report_data["drivers"].append(driver_report)
        
        # Aplicar cambios si no es dry_run
        if not dry_run:
            try:
                db.commit()
                print(f"\n[OK] Cambios aplicados exitosamente")
            except Exception as e:
                db.rollback()
                print(f"\n[ERROR] Error al hacer commit: {e}")
                stats["errors"] += 1
                logger.error(f"Error en commit: {e}", exc_info=True)
        
        # Actualizar stats en reporte
        report_data["stats"] = stats
        
        # Generar reporte JSON
        with open(report_json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"[OK] Reporte JSON guardado en: {report_json_path}")
        
        # Generar reporte CSV
        csv_fieldnames = [
            'driver_id', 'person_key', 'creation_rule', 'previous_status',
            'lead_events_count', 'matched_event_count', 'match_strategy',
            'action', 'status', 'detected_driver_id_path', 'matched_source_table',
            'matched_event_sample_ids', 'normalized_event_license', 'normalized_event_phone',
            'links_created', 'error'
        ]
        
        with open(report_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=csv_fieldnames, extrasaction='ignore')
            writer.writeheader()
            for driver in report_data["drivers"]:
                # Convertir listas a strings para CSV y limpiar campos None
                driver_copy = {k: v for k, v in driver.items() if k in csv_fieldnames}
                if 'matched_event_sample_ids' in driver_copy and isinstance(driver_copy['matched_event_sample_ids'], list):
                    driver_copy['matched_event_sample_ids'] = ','.join(map(str, driver_copy['matched_event_sample_ids']))
                elif 'matched_event_sample_ids' not in driver_copy:
                    driver_copy['matched_event_sample_ids'] = ''
                # Asegurar que todos los campos requeridos existan
                for field in csv_fieldnames:
                    if field not in driver_copy:
                        driver_copy[field] = None
                writer.writerow(driver_copy)
        print(f"[OK] Reporte CSV guardado en: {report_csv_path}")
        
        # Reporte final en consola
        print(f"\n{'='*80}")
        print(f"RESUMEN:")
        print(f"{'='*80}")
        print(f"Drivers procesados: {stats['processed']}")
        print(f"Drivers con lead_events: {stats['with_events']}")
        print(f"Drivers sin lead_events: {stats['without_events']}")
        print(f"Links creados: {stats['links_created']}")
        print(f"Links omitidos (ya existían): {stats['links_skipped']}")
        print(f"Resueltos (relinked): {stats['resolved_relinked']}")
        print(f"Errores: {stats['errors']}")
        
        if dry_run:
            print(f"\n[TIP] Para aplicar estos cambios, ejecuta con --execute")
        
        print(f"\n{'='*80}\n")
        
        return report_data
        
    except Exception as e:
        print(f"\n[ERROR] Error en reproceso: {e}")
        logger.error(f"Error en reproceso: {e}", exc_info=True)
        if not dry_run:
            db.rollback()
        raise
    finally:
        db.close()


def fix_drivers_without_leads(dry_run=True, limit=None, output_dir=None, reprocess_quarantined=False):
    """
    Corrige drivers sin leads creando los links faltantes desde lead_events
    o enviándolos a cuarentena.
    
    Si reprocess_quarantined=True, reprocesa drivers en cuarentena en lugar de buscar nuevos.
    """
    if reprocess_quarantined:
        return reprocess_quarantined_drivers(dry_run=dry_run, limit=limit, output_dir=output_dir)
    
    db = SessionLocal()
    
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
    else:
        output_path = Path.cwd() / "output"
        output_path.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_json_path = output_path / f"orphans_report_{timestamp}.json"
    report_csv_path = output_path / f"orphans_report_{timestamp}.csv"
    
    try:
        print(f"\n{'='*80}")
        print(f"LIMPIEZA: Corregir Drivers sin Leads (Sistema de Cuarentena)")
        print(f"{'='*80}")
        print(f"Modo: {'DRY RUN (solo lectura)' if dry_run else 'EJECUTAR (aplicar cambios)'}")
        if limit:
            print(f"Límite: {limit} drivers")
        print(f"Directorio de salida: {output_path}")
        print(f"{'='*80}\n")
        
        # Encontrar drivers sin leads (excluyendo ya en cuarentena)
        drivers_without_leads = find_drivers_without_leads(db, exclude_quarantined=True)
        
        if limit:
            drivers_without_leads = list(drivers_without_leads[:limit])
        
        print(f"Total de drivers sin leads encontrados: {len(drivers_without_leads)}\n")
        
        stats = {
            "processed": 0,
            "with_events": 0,
            "without_events": 0,
            "links_created": 0,
            "links_skipped": 0,
            "quarantined": 0,
            "resolved_relinked": 0,
            "errors": 0
        }
        
        report_data = {
            "timestamp": timestamp,
            "dry_run": dry_run,
            "mode": "fix_new_orphans",
            "stats": stats,
            "drivers": []
        }
        
        for driver_row in drivers_without_leads:
            stats["processed"] += 1
            person_key = driver_row.person_key
            driver_id = driver_row.driver_id
            creation_rule = driver_row.creation_rule
            
            # Construir evidencia
            evidence = {
                "creation_rule": creation_rule,
                "linked_at": driver_row.linked_at.isoformat() if driver_row.linked_at else None,
                "original_evidence": driver_row.evidence,
                "primary_phone": driver_row.primary_phone,
                "primary_license": driver_row.primary_license,
                "primary_full_name": driver_row.primary_full_name
            }
            
            # Buscar lead_events para este driver
            try:
                events = find_lead_events_for_driver(db, driver_id)
            except Exception as e:
                logger.error(f"Error buscando lead_events para {driver_id}: {e}")
                db.rollback()
                events = []
            
            driver_report = {
                "driver_id": driver_id,
                "person_key": str(person_key),
                "creation_rule": creation_rule,
                "lead_events_count": len(events),
                "action": None,
                "status": None,
                "detected_driver_id_path": None,
                "event_source_table": None,
                "error": None
            }
            
            if not events:
                # NO hay lead_events - enviar a cuarentena
                stats["without_events"] += 1
                detected_reason = OrphanDetectedReason.NO_LEAD_NO_EVENTS
                
                driver_report["detected_driver_id_path"] = "no_events_found"
                driver_report["action"] = "quarantined"
                driver_report["status"] = "quarantined"
                
                quarantine_data, error = upsert_quarantine_record(
                    db=db,
                    driver_id=driver_id,
                    person_key=person_key,
                    detected_reason=detected_reason,
                    creation_rule=creation_rule,
                    evidence_json=evidence,
                    status=OrphanStatus.QUARANTINED,
                    dry_run=dry_run
                )
                
                if error:
                    stats["errors"] += 1
                    driver_report["error"] = error
                    logger.error(f"Error en cuarentena para {driver_id}: {error}")
                else:
                    stats["quarantined"] += 1
                
            else:
                # HAY lead_events - intentar crear links
                stats["with_events"] += 1
                events_used = []
                links_created_count = 0
                
                for event in events:
                    link_data, error = create_lead_link_from_event(
                        db, person_key, event, dry_run=dry_run
                    )
                    
                    if error:
                        if "ya existe" not in error.lower():
                            logger.warning(f"Driver {driver_id}: {error}")
                        stats["links_skipped"] += 1
                    elif link_data:
                        links_created_count += 1
                        stats["links_created"] += 1
                        events_used.append({
                            "event_id": event.id,
                            "source_table": event.source_table,
                            "source_pk": link_data.get("source_pk")
                        })
                
                evidence["lead_events_used"] = events_used
                
                # Determinar qué path se usó para extraer driver_id (usar el primer evento)
                if events:
                    first_event = events[0]
                    payload = first_event.payload_json or {}
                    if payload.get('driver_id'):
                        driver_report["detected_driver_id_path"] = "payload_json.driver_id"
                    elif payload.get('driver_license') or payload.get('driver_phone'):
                        driver_report["detected_driver_id_path"] = "via_license_phone_mapping"
                    elif first_event.person_key:
                        driver_report["detected_driver_id_path"] = "via_person_key"
                    driver_report["event_source_table"] = first_event.source_table
                
                if links_created_count > 0:
                    # Se crearon links - marcar como resolved_relinked
                    detected_reason = OrphanDetectedReason.NO_LEAD_NO_EVENTS  # Originalmente no tenía lead
                    resolution_notes = f"Relinked from {links_created_count} lead_event(s). Created by fix_drivers_without_leads."
                    
                    quarantine_data, error = upsert_quarantine_record(
                        db=db,
                        driver_id=driver_id,
                        person_key=person_key,
                        detected_reason=detected_reason,
                        creation_rule=creation_rule,
                        evidence_json=evidence,
                        status=OrphanStatus.RESOLVED_RELINKED,
                        resolution_notes=resolution_notes,
                        dry_run=dry_run
                    )
                    
                    if error:
                        stats["errors"] += 1
                        driver_report["error"] = error
                    else:
                        stats["resolved_relinked"] += 1
                        driver_report["action"] = "resolved_relinked"
                        driver_report["status"] = "resolved_relinked"
                        driver_report["links_created"] = links_created_count
                else:
                    # No se pudieron crear links - enviar a cuarentena con razón especial
                    detected_reason = OrphanDetectedReason.NO_LEAD_HAS_EVENTS_REPAIR_FAILED
                    evidence["failed_repair_attempts"] = len(events)
                    
                    driver_report["action"] = "quarantined_repair_failed"
                    driver_report["status"] = "quarantined"
                    
                    quarantine_data, error = upsert_quarantine_record(
                        db=db,
                        driver_id=driver_id,
                        person_key=person_key,
                        detected_reason=detected_reason,
                        creation_rule=creation_rule,
                        evidence_json=evidence,
                        status=OrphanStatus.QUARANTINED,
                        resolution_notes="Had lead_events but failed to create links (may already exist)",
                        dry_run=dry_run
                    )
                    
                    if error:
                        stats["errors"] += 1
                        driver_report["error"] = error
                    else:
                        stats["quarantined"] += 1
            
            report_data["drivers"].append(driver_report)
        
        # Aplicar cambios si no es dry_run
        if not dry_run:
            try:
                db.commit()
                print(f"\n[OK] Cambios aplicados exitosamente")
            except Exception as e:
                db.rollback()
                print(f"\n[ERROR] Error al hacer commit: {e}")
                stats["errors"] += 1
                logger.error(f"Error en commit: {e}", exc_info=True)
        
        # Actualizar stats en reporte
        report_data["stats"] = stats
        
        # Generar reporte JSON
        with open(report_json_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False, default=str)
        print(f"[OK] Reporte JSON guardado en: {report_json_path}")
        
        # Generar reporte CSV
        with open(report_csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=[
                'driver_id', 'person_key', 'creation_rule', 'lead_events_count',
                'action', 'status', 'detected_driver_id_path', 'event_source_table', 'error'
            ])
            writer.writeheader()
            for driver in report_data["drivers"]:
                writer.writerow(driver)
        print(f"[OK] Reporte CSV guardado en: {report_csv_path}")
        
        # Reporte final en consola
        print(f"\n{'='*80}")
        print(f"RESUMEN:")
        print(f"{'='*80}")
        print(f"Drivers procesados: {stats['processed']}")
        print(f"Drivers con lead_events: {stats['with_events']}")
        print(f"Drivers sin lead_events: {stats['without_events']}")
        print(f"Links creados: {stats['links_created']}")
        print(f"Links omitidos (ya existían): {stats['links_skipped']}")
        print(f"Resueltos (relinked): {stats['resolved_relinked']}")
        print(f"Enviados a cuarentena: {stats['quarantined']}")
        print(f"Errores: {stats['errors']}")
        
        # Muestra de drivers procesados
        if report_data["drivers"]:
            print(f"\n{'='*80}")
            print(f"MUESTRA DE DRIVERS (primeros 10):")
            print(f"{'='*80}")
            print(f"{'Driver ID':<35} {'Eventos':<8} {'Acción':<25} {'Estado':<20} {'Path':<30}")
            print(f"{'-'*118}")
            for d in report_data["drivers"][:10]:
                path = d.get('detected_driver_id_path', 'N/A')[:28]
                print(f"{d['driver_id']:<35} {d.get('lead_events_count', 0):<8} {d.get('action', 'N/A'):<25} {d.get('status', 'N/A'):<20} {path:<30}")
            if len(report_data["drivers"]) > 10:
                print(f"... y {len(report_data['drivers']) - 10} más")
        
        if dry_run:
            print(f"\n[TIP] Para aplicar estos cambios, ejecuta con --execute")
        
        print(f"\n{'='*80}\n")
        
        return report_data
        
    except Exception as e:
        print(f"\n[ERROR] Error en limpieza: {e}")
        logger.error(f"Error en limpieza: {e}", exc_info=True)
        if not dry_run:
            db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Corregir drivers sin leads con sistema de cuarentena")
    parser.add_argument("--execute", action="store_true", help="Aplicar cambios (sin esto es dry-run)")
    parser.add_argument("--limit", type=int, help="Limitar número de drivers a procesar")
    parser.add_argument("--output-dir", type=str, help="Directorio para guardar reportes (default: ./output)")
    parser.add_argument("--reprocess-quarantined", action="store_true", help="Reprocesar drivers en cuarentena en lugar de buscar nuevos")
    
    args = parser.parse_args()
    
    fix_drivers_without_leads(
        dry_run=not args.execute, 
        limit=args.limit,
        output_dir=args.output_dir,
        reprocess_quarantined=args.reprocess_quarantined
    )
