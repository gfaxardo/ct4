"""
Script de Diagnóstico: Analizar estructura de lead_events y extracción de driver_id
===============================================================================

Este script analiza la estructura de lead_events para identificar cómo se almacena
el driver_id en payload_json y verificar si los drivers en cuarentena tienen eventos.
"""

import sys
import json
from pathlib import Path
from collections import Counter

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_lead_events_structure(db):
    """Analiza la estructura de lead_events"""
    
    print("\n" + "="*80)
    print("DIAGNÓSTICO: Estructura de lead_events")
    print("="*80 + "\n")
    
    # A. Count total lead_events
    query_a = text("SELECT COUNT(*) FROM observational.lead_events")
    result = db.execute(query_a)
    total_events = result.fetchone()[0]
    print(f"A. Total de lead_events: {total_events:,}")
    
    if total_events == 0:
        print("   [WARN] No hay eventos en lead_events")
        return
    
    # B. Detectar keys más comunes en payload_json
    print(f"\nB. Keys más comunes en payload_json:")
    print("-" * 80)
    query_b = text("""
        SELECT 
            jsonb_object_keys(payload_json) AS key_name,
            COUNT(*) AS count
        FROM observational.lead_events
        WHERE payload_json IS NOT NULL
        GROUP BY key_name
        ORDER BY count DESC
        LIMIT 50
    """)
    result = db.execute(query_b)
    keys_data = result.fetchall()
    
    if keys_data:
        print(f"{'Key':<40} {'Count':<15} {'%':<10}")
        print("-" * 65)
        for row in keys_data:
            percentage = (row.count / total_events) * 100
            print(f"{row.key_name:<40} {row.count:<15,} {percentage:>6.2f}%")
    else:
        print("   [WARN] No se encontraron keys en payload_json")
    
    # C. Verificar variantes de driver_id en payload_json
    print(f"\nC. Variantes de driver_id encontradas:")
    print("-" * 80)
    
    variants = [
        "driver_id",
        "driverId",
        "driver.id",
        "driver.driver_id",
        "id",
        "driver_license",
        "driver_phone"
    ]
    
    for variant in variants:
        if '.' in variant:
            # Path anidado como "driver.id"
            parts = variant.split('.')
            query = text(f"""
                SELECT COUNT(*)
                FROM observational.lead_events
                WHERE payload_json->:part1 ? :part2
                LIMIT 1000
            """)
            result = db.execute(query, {"part1": parts[0], "part2": parts[1]})
        else:
            # Key simple
            query = text("""
                SELECT COUNT(*)
                FROM observational.lead_events
                WHERE payload_json ? :key
                LIMIT 1000
            """)
            result = db.execute(query, {"key": variant})
        
        count = result.fetchone()[0]
        if count > 0:
            print(f"   - {variant:<30} : {count:,} eventos")
    
    # D. Muestra de payload_json para inspección
    print(f"\nD. Muestra de payload_json (primeros 10 con driver_id o variantes):")
    print("-" * 80)
    
    query_d = text("""
        SELECT 
            id,
            source_table,
            source_pk,
            payload_json
        FROM observational.lead_events
        WHERE payload_json IS NOT NULL
            AND (
                payload_json ? 'driver_id'
                OR payload_json ? 'driverId'
                OR payload_json ? 'id'
                OR payload_json ? 'driver_license'
                OR payload_json ? 'driver_phone'
            )
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    result = db.execute(query_d)
    samples = result.fetchall()
    
    if samples:
        for idx, sample in enumerate(samples, 1):
            print(f"\n   Muestra {idx}:")
            print(f"   - Event ID: {sample.id}")
            print(f"   - Source Table: {sample.source_table}")
            print(f"   - Source PK: {sample.source_pk}")
            print(f"   - Payload JSON:")
            payload_str = json.dumps(sample.payload_json, indent=4, ensure_ascii=False, default=str)
            for line in payload_str.split('\n'):
                print(f"     {line}")
    else:
        print("   [WARN] No se encontraron eventos con variantes de driver_id")


def check_quarantined_drivers_events(db, sample_size=20):
    """Verifica si drivers en cuarentena tienen eventos en lead_events"""
    
    print(f"\n" + "="*80)
    print(f"DIAGNÓSTICO: Drivers en cuarentena vs lead_events")
    print("="*80 + "\n")
    
    # Obtener muestra de drivers en cuarentena
    query_quarantine = text("""
        SELECT driver_id
        FROM canon.driver_orphan_quarantine
        WHERE status = 'quarantined'
        LIMIT :limit
    """)
    result = db.execute(query_quarantine, {"limit": sample_size})
    quarantined_drivers = [row.driver_id for row in result.fetchall()]
    
    if not quarantined_drivers:
        print("[INFO] No hay drivers en cuarentena para analizar")
        return
    
    print(f"Muestra de drivers en cuarentena: {len(quarantined_drivers)}")
    print(f"Drivers: {', '.join(quarantined_drivers[:5])}...")
    
    # Buscar eventos para cada driver usando múltiples estrategias
    print(f"\nBuscando eventos para estos drivers:")
    print("-" * 80)
    
    found_count = 0
    not_found_count = 0
    
    for driver_id in quarantined_drivers[:10]:  # Solo primeros 10 para análisis detallado
        # Estrategia 1: payload_json->>'driver_id'
        query1 = text("""
            SELECT COUNT(*) 
            FROM observational.lead_events
            WHERE payload_json->>'driver_id' = :driver_id
        """)
        result1 = db.execute(query1, {"driver_id": driver_id})
        count1 = result1.fetchone()[0]
        
        # Estrategia 2: Buscar como texto en payload_json
        query2 = text("""
            SELECT COUNT(*)
            FROM observational.lead_events
            WHERE payload_json::text ILIKE '%' || :driver_id || '%'
        """)
        result2 = db.execute(query2, {"driver_id": driver_id})
        count2 = result2.fetchone()[0]
        
        # Estrategia 3: Buscar en diferentes paths
        query3 = text("""
            SELECT COUNT(*)
            FROM observational.lead_events
            WHERE 
                payload_json->>'driver_id' = :driver_id
                OR payload_json->>'driverId' = :driver_id
                OR payload_json->>'id' = :driver_id
                OR (payload_json->'driver'->>'id') = :driver_id
                OR (payload_json->'driver'->>'driver_id') = :driver_id
        """)
        result3 = db.execute(query3, {"driver_id": driver_id})
        count3 = result3.fetchone()[0]
        
        if count3 > 0:
            found_count += 1
            print(f"   [FOUND] {driver_id}: {count3} eventos (driver_id: {count1}, texto: {count2}, múltiples: {count3})")
            
            # Obtener muestra de eventos encontrados
            query_sample = text("""
                SELECT id, source_table, source_pk, payload_json->>'driver_id' as driver_id_key,
                       payload_json->>'driverId' as driverId_key,
                       payload_json->>'id' as id_key
                FROM observational.lead_events
                WHERE 
                    payload_json->>'driver_id' = :driver_id
                    OR payload_json->>'driverId' = :driver_id
                    OR payload_json->>'id' = :driver_id
                    OR (payload_json->'driver'->>'id') = :driver_id
                    OR (payload_json->'driver'->>'driver_id') = :driver_id
                LIMIT 3
            """)
            result_sample = db.execute(query_sample, {"driver_id": driver_id})
            for event in result_sample:
                print(f"      - Event {event.id} ({event.source_table}): driver_id_key={event.driver_id_key}, driverId_key={event.driverId_key}, id_key={event.id_key}")
        else:
            not_found_count += 1
            print(f"   [NOT FOUND] {driver_id}")
    
    print(f"\nResumen (muestra de {min(10, len(quarantined_drivers))} drivers):")
    print(f"   - Con eventos encontrados: {found_count}")
    print(f"   - Sin eventos: {not_found_count}")
    
    # Análisis estadístico completo
    print(f"\nAnálisis estadístico completo (todos los drivers en cuarentena):")
    print("-" * 80)
    
    query_stats = text("""
        WITH quarantined_drivers AS (
            SELECT driver_id
            FROM canon.driver_orphan_quarantine
            WHERE status = 'quarantined'
        ),
        events_found AS (
            SELECT DISTINCT qd.driver_id,
                CASE 
                    WHEN COUNT(le.id) > 0 THEN 1
                    ELSE 0
                END as has_events
            FROM quarantined_drivers qd
            LEFT JOIN observational.lead_events le ON (
                le.payload_json->>'driver_id' = qd.driver_id
                OR le.payload_json->>'driverId' = qd.driver_id
                OR le.payload_json->>'id' = qd.driver_id
                OR (le.payload_json->'driver'->>'id') = qd.driver_id
                OR (le.payload_json->'driver'->>'driver_id') = qd.driver_id
                OR le.payload_json::text ILIKE '%' || qd.driver_id || '%'
            )
            GROUP BY qd.driver_id
        )
        SELECT 
            COUNT(*) as total_quarantined,
            SUM(has_events) as with_events,
            COUNT(*) - SUM(has_events) as without_events
        FROM events_found
    """)
    
    result_stats = db.execute(query_stats)
    stats = result_stats.fetchone()
    
    if stats:
        print(f"   - Total en cuarentena: {stats.total_quarantined:,}")
        print(f"   - Con eventos (múltiples estrategias): {stats.with_events:,}")
        print(f"   - Sin eventos: {stats.without_events:,}")
        if stats.total_quarantined > 0:
            percentage = (stats.with_events / stats.total_quarantined) * 100
            print(f"   - Porcentaje con eventos: {percentage:.2f}%")


def determine_driver_id_extraction_pattern(db):
    """Determina el patrón correcto para extraer driver_id"""
    
    print(f"\n" + "="*80)
    print(f"DIAGNÓSTICO: Patrón de extracción de driver_id")
    print("="*80 + "\n")
    
    # Buscar todos los posibles patrones y contar cuántos eventos los usan
    query_patterns = text("""
        SELECT 
            source_table,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE payload_json ? 'driver_id') as has_driver_id,
            COUNT(*) FILTER (WHERE payload_json ? 'driverId') as has_driver_id_camel,
            COUNT(*) FILTER (WHERE payload_json ? 'id') as has_id,
            COUNT(*) FILTER (WHERE payload_json->'driver' IS NOT NULL) as has_driver_obj,
            COUNT(*) FILTER (WHERE payload_json ? 'driver_license') as has_driver_license,
            COUNT(*) FILTER (WHERE payload_json ? 'driver_phone') as has_driver_phone
        FROM observational.lead_events
        WHERE payload_json IS NOT NULL
        GROUP BY source_table
        ORDER BY total DESC
    """)
    
    result = db.execute(query_patterns)
    patterns_data = result.fetchall()
    
    print(f"{'Source Table':<30} {'Total':<10} {'driver_id':<12} {'driverId':<12} {'id':<12} {'driver obj':<15} {'license':<12} {'phone':<12}")
    print("-" * 120)
    
    for row in patterns_data:
        print(f"{row.source_table:<30} {row.total:<10,} {row.has_driver_id:<12,} {row.has_driver_id_camel:<12,} {row.has_id:<12,} {row.has_driver_obj:<15,} {row.has_driver_license:<12,} {row.has_driver_phone:<12,}")
    
    # Recomendaciones
    print(f"\nRecomendaciones de extracción por source_table:")
    print("-" * 80)
    
    for row in patterns_data:
        print(f"\n{row.source_table}:")
        patterns = []
        if row.has_driver_id > 0:
            patterns.append(("payload_json->>'driver_id'", row.has_driver_id, row.total))
        if row.has_driver_id_camel > 0:
            patterns.append(("payload_json->>'driverId'", row.has_driver_id_camel, row.total))
        if row.has_id > 0:
            patterns.append(("payload_json->>'id'", row.has_id, row.total))
        if row.has_driver_obj > 0:
            patterns.append(("payload_json->'driver'->>'id'", row.has_driver_obj, row.total))
        if row.has_driver_license > 0 or row.has_driver_phone > 0:
            # Usar license/phone para buscar driver_id en drivers_index
            patterns.append(("via drivers_index (license/phone)", min(row.has_driver_license, row.has_driver_phone), row.total))
        
        if patterns:
            patterns.sort(key=lambda x: x[1], reverse=True)
            print(f"   Prioridad recomendada:")
            for idx, (pattern, count, total) in enumerate(patterns[:3], 1):
                percentage = (count / total) * 100 if total > 0 else 0
                print(f"   {idx}. {pattern} ({count:,} eventos, {percentage:.1f}%)")


def main():
    """Función principal"""
    db = SessionLocal()
    
    try:
        analyze_lead_events_structure(db)
        check_quarantined_drivers_events(db)
        determine_driver_id_extraction_pattern(db)
        
        print(f"\n" + "="*80)
        print("DIAGNÓSTICO COMPLETADO")
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Error en diagnóstico: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

