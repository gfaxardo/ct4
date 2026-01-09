"""
Script de Limpieza: Corregir Drivers sin Leads
================================================

Este script corrige los drivers que están en el sistema sin leads asociados.

Estrategia:
1. Identifica drivers sin leads
2. Busca lead_events asociados
3. Crea los links faltantes de leads si existen eventos
4. Marca para revisión manual los que no tienen eventos

IMPORTANTE: Este script es de solo lectura por defecto.
Usar --dry-run para ver qué haría sin hacer cambios.
Usar --execute para aplicar los cambios.
"""

import sys
import os
import argparse
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db import SessionLocal
from app.models.canon import IdentityLink, IdentityRegistry, ConfidenceLevel
from app.models.ops import IngestionRun, JobType, RunStatus
from datetime import datetime
from uuid import UUID
import json


def find_drivers_without_leads(db):
    """Encuentra drivers que no tienen leads asociados"""
    query = text("""
        SELECT DISTINCT
            il.person_key,
            il.source_pk as driver_id,
            il.match_rule,
            il.linked_at,
            il.evidence
        FROM canon.identity_links il
        WHERE il.source_table = 'drivers'
        AND il.person_key NOT IN (
            SELECT DISTINCT person_key
            FROM canon.identity_links
            WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
        )
    """)
    
    result = db.execute(query)
    return result.fetchall()


def find_lead_events_for_driver(db, driver_id):
    """Encuentra lead_events asociados a un driver"""
    query = text("""
        SELECT 
            le.id,
            le.source_table,
            le.event_date,
            le.payload_json,
            le.created_at
        FROM observational.lead_events le
        WHERE (le.payload_json->>'driver_id')::text = :driver_id
        ORDER BY le.event_date DESC, le.created_at DESC
    """)
    
    result = db.execute(query, {"driver_id": driver_id})
    return result.fetchall()


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
    
    # Determinar source_pk según el tipo de lead
    if source_table == 'module_ct_migrations':
        # Para migrations, el source_pk debería estar en el payload o en la tabla original
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
            source_pk = row.id if row else None
    elif source_table == 'module_ct_cabinet_leads':
        source_pk = payload.get('external_id') or payload.get('id')
    elif source_table == 'module_ct_scouting_daily':
        # Para scouting, el source_pk es un hash generado
        source_pk = payload.get('source_pk') or payload.get('id')
    else:
        source_pk = payload.get('id') or payload.get('source_pk')
    
    if not source_pk:
        return None, f"No se pudo determinar source_pk para {source_table}"
    
    # Verificar si ya existe el link
    if find_existing_lead_link(db, person_key, source_table, str(source_pk)):
        return None, f"Link ya existe para {source_table}:{source_pk}"
    
    if dry_run:
        return {
            "person_key": str(person_key),
            "source_table": source_table,
            "source_pk": str(source_pk),
            "event_id": event.id,
            "event_date": str(event.event_date)
        }, None
    
    # Crear el link
    try:
        link = IdentityLink(
            person_key=person_key,
            source_table=source_table,
            source_pk=str(source_pk),
            snapshot_date=event.event_date or datetime.utcnow(),
            match_rule="LEAD_EVENT_RECONSTRUCTION",
            match_score=100,
            confidence_level=ConfidenceLevel.HIGH,
            evidence={
                "created_by": "fix_drivers_without_leads",
                "event_id": event.id,
                "event_date": str(event.event_date),
                "reconstructed_from": "lead_events"
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
        return None, f"Error creando link: {str(e)}"


def fix_drivers_without_leads(dry_run=True, limit=None):
    """
    Corrige drivers sin leads creando los links faltantes desde lead_events.
    """
    db = SessionLocal()
    
    try:
        print(f"\n{'='*80}")
        print(f"LIMPIEZA: Corregir Drivers sin Leads")
        print(f"{'='*80}")
        print(f"Modo: {'DRY RUN (solo lectura)' if dry_run else 'EJECUTAR (aplicar cambios)'}")
        if limit:
            print(f"Límite: {limit} drivers")
        print(f"{'='*80}\n")
        
        # Encontrar drivers sin leads
        drivers_without_leads = find_drivers_without_leads(db)
        
        if limit:
            drivers_without_leads = drivers_without_leads[:limit]
        
        print(f"Total de drivers sin leads encontrados: {len(drivers_without_leads)}\n")
        
        stats = {
            "processed": 0,
            "with_events": 0,
            "without_events": 0,
            "links_created": 0,
            "links_skipped": 0,
            "errors": 0
        }
        
        links_to_create = []
        drivers_without_events = []
        
        for driver_row in drivers_without_leads:
            stats["processed"] += 1
            person_key = driver_row.person_key
            driver_id = driver_row.driver_id
            
            # Buscar lead_events para este driver
            events = find_lead_events_for_driver(db, driver_id)
            
            if not events:
                drivers_without_events.append({
                    "driver_id": driver_id,
                    "person_key": str(person_key),
                    "match_rule": driver_row.match_rule,
                    "linked_at": driver_row.linked_at
                })
                stats["without_events"] += 1
                continue
            
            stats["with_events"] += 1
            
            # Para cada evento, intentar crear el link
            for event in events:
                link_data, error = create_lead_link_from_event(
                    db, person_key, event, dry_run=dry_run
                )
                
                if error:
                    if "ya existe" not in error.lower():
                        print(f"  ⚠️  Driver {driver_id}: {error}")
                    stats["links_skipped"] += 1
                elif link_data:
                    links_to_create.append({
                        "driver_id": driver_id,
                        "event": event,
                        "link_data": link_data
                    })
                    stats["links_created"] += 1
        
        # Aplicar cambios si no es dry_run
        if not dry_run and links_to_create:
            try:
                db.commit()
                print(f"\nOK: {stats['links_created']} links creados exitosamente")
            except Exception as e:
                db.rollback()
                print(f"\nERROR: Error al hacer commit: {e}")
                stats["errors"] += 1
        
        # Reporte final
        print(f"\n{'='*80}")
        print(f"Resumen:")
        print(f"{'='*80}")
        print(f"Drivers procesados: {stats['processed']}")
        print(f"Drivers con lead_events: {stats['with_events']}")
        print(f"Drivers sin lead_events: {stats['without_events']}")
        print(f"Links creados: {stats['links_created']}")
        print(f"Links omitidos (ya existían): {stats['links_skipped']}")
        print(f"Errores: {stats['errors']}")
        
        if drivers_without_events:
            print(f"\n{'='*80}")
            print(f"WARNING: Drivers SIN lead_events (requieren revision manual): {len(drivers_without_events)}")
            print(f"{'='*80}")
            print(f"{'Driver ID':<40} {'Person Key':<40} {'Regla':<20}")
            print(f"{'-'*100}")
            for d in drivers_without_events[:20]:  # Mostrar solo los primeros 20
                print(f"{d['driver_id']:<40} {d['person_key']:<40} {d['match_rule']:<20}")
            if len(drivers_without_events) > 20:
                print(f"... y {len(drivers_without_events) - 20} más")
        
        if dry_run and links_to_create:
            print(f"\n{'='*80}")
            print(f"Links que se crearían (modo dry-run):")
            print(f"{'='*80}")
            for item in links_to_create[:10]:  # Mostrar solo los primeros 10
                print(f"  - {item['link_data']['source_table']}:{item['link_data']['source_pk']} -> {item['link_data']['person_key']}")
            if len(links_to_create) > 10:
                print(f"  ... y {len(links_to_create) - 10} más")
            print(f"\nTIP: Para aplicar estos cambios, ejecuta con --execute")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"\nERROR: Error en limpieza: {e}")
        import traceback
        traceback.print_exc()
        if not dry_run:
            db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Corregir drivers sin leads")
    parser.add_argument("--execute", action="store_true", help="Aplicar cambios (sin esto es dry-run)")
    parser.add_argument("--limit", type=int, help="Limitar número de drivers a procesar")
    
    args = parser.parse_args()
    
    fix_drivers_without_leads(dry_run=not args.execute, limit=args.limit)

