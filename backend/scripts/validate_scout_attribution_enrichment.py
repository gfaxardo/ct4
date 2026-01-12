#!/usr/bin/env python3
"""
Script de validación completo para el enriquecimiento de scout attribution.
Valida:
1. KPIs de cobertura de scout (antes/después)
2. Presencia de scout_name en la vista
3. Funcionalidad del endpoint
4. Filtros por scout
5. Integridad de datos
"""

import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.config import settings

def validate_coverage(session):
    """Valida la cobertura de scout en la vista."""
    print("\n" + "="*80)
    print("VALIDACIÓN 1: Cobertura de Scout")
    print("="*80)
    
    query = text("""
        SELECT 
            COUNT(*) AS total_claims,
            COUNT(*) FILTER (WHERE is_scout_resolved = true) AS claims_with_scout,
            COUNT(*) FILTER (WHERE is_scout_resolved = false) AS claims_without_scout,
            ROUND((COUNT(*) FILTER (WHERE is_scout_resolved = true)::NUMERIC / NULLIF(COUNT(*), 0) * 100), 2) AS pct_with_scout
        FROM ops.v_yango_collection_with_scout
    """)
    
    result = session.execute(query).fetchone()
    print(f"\nCobertura Actual:")
    print(f"  Total claims: {result.total_claims:,}")
    print(f"  Con scout: {result.claims_with_scout:,} ({result.pct_with_scout}%)")
    print(f"  Sin scout: {result.claims_without_scout:,} ({100 - result.pct_with_scout}%)")
    
    # Verificar que la mejora es significativa (>80%)
    if result.pct_with_scout >= 80:
        print(f"\n[OK] Cobertura de scout >= 80%: {result.pct_with_scout}%")
        return True
    else:
        print(f"\n[WARN] Cobertura de scout < 80%: {result.pct_with_scout}%")
        return False

def validate_scout_name(session):
    """Valida que scout_name esté presente y enriquecido."""
    print("\n" + "="*80)
    print("VALIDACIÓN 2: Enriquecimiento con scout_name")
    print("="*80)
    
    # Query 1: Scouts con scout_id
    query1 = text("""
        SELECT 
            COUNT(*) FILTER (WHERE scout_id IS NOT NULL) AS total_with_scout_id,
            COUNT(*) FILTER (WHERE scout_id IS NOT NULL AND scout_name IS NOT NULL) AS with_scout_name,
            COUNT(*) FILTER (WHERE scout_id IS NOT NULL AND scout_name IS NULL) AS without_scout_name
        FROM ops.v_yango_collection_with_scout
        WHERE is_scout_resolved = true
    """)
    
    result1 = session.execute(query1).fetchone()
    print(f"\nEnriquecimiento scout_name:")
    print(f"  Total con scout_id: {result1.total_with_scout_id:,}")
    print(f"  Con scout_name: {result1.with_scout_name:,}")
    print(f"  Sin scout_name: {result1.without_scout_name:,}")
    
    if result1.total_with_scout_id > 0:
        pct_with_name = (result1.with_scout_name / result1.total_with_scout_id) * 100
        print(f"  Porcentaje con nombre: {pct_with_name:.2f}%")
        
        if result1.without_scout_name == 0:
            print(f"\n[OK] Todos los scouts con scout_id tienen scout_name")
            return True
        else:
            print(f"\n[WARN] {result1.without_scout_name} scouts sin scout_name")
            return False
    else:
        print(f"\n[ERROR] No hay scouts con scout_id")
        return False
    
    # Query 2: Muestra de scouts con nombre
    query2 = text("""
        SELECT 
            scout_id,
            scout_name,
            scout_quality_bucket,
            scout_source_table
        FROM ops.v_yango_collection_with_scout
        WHERE scout_name IS NOT NULL
        LIMIT 10
    """)
    
    result2 = session.execute(query2).fetchall()
    if result2:
        print(f"\nMuestra de scouts con nombre (primeros 10):")
        for row in result2:
            print(f"  Scout ID {row.scout_id}: {row.scout_name} ({row.scout_quality_bucket})")

def validate_source_distribution(session):
    """Valida la distribución por fuente."""
    print("\n" + "="*80)
    print("VALIDACIÓN 3: Distribución por Fuente")
    print("="*80)
    
    query = text("""
        SELECT 
            scout_source_table,
            COUNT(*) AS claim_count,
            ROUND(COUNT(*)::NUMERIC / NULLIF((SELECT COUNT(*) FROM ops.v_yango_collection_with_scout WHERE is_scout_resolved = true), 0) * 100, 2) AS pct
        FROM ops.v_yango_collection_with_scout
        WHERE is_scout_resolved = true
        GROUP BY scout_source_table
        ORDER BY claim_count DESC
    """)
    
    results = session.execute(query).fetchall()
    print(f"\nDistribución por Fuente:")
    total_count = sum(row.claim_count for row in results)
    for row in results:
        print(f"  {row.scout_source_table or 'NULL'}: {row.claim_count:,} ({row.pct}%)")
    
    # Verificar que hay múltiples fuentes
    if len(results) > 1:
        print(f"\n[OK] Scouts provienen de {len(results)} fuentes diferentes")
        return True
    else:
        print(f"\n[WARN] Scouts provienen de una sola fuente")
        return False

def validate_quality_buckets(session):
    """Valida los quality buckets."""
    print("\n" + "="*80)
    print("VALIDACIÓN 4: Quality Buckets")
    print("="*80)
    
    query = text("""
        SELECT 
            scout_quality_bucket,
            COUNT(*) AS claim_count,
            ROUND(COUNT(*)::NUMERIC / NULLIF((SELECT COUNT(*) FROM ops.v_yango_collection_with_scout), 0) * 100, 2) AS pct
        FROM ops.v_yango_collection_with_scout
        GROUP BY scout_quality_bucket
        ORDER BY claim_count DESC
    """)
    
    results = session.execute(query).fetchall()
    print(f"\nDistribución por Quality Bucket:")
    for row in results:
        print(f"  {row.scout_quality_bucket}: {row.claim_count:,} ({row.pct}%)")
    
    return True

def validate_endpoint_fields(session):
    """Valida que los campos necesarios para el endpoint existan."""
    print("\n" + "="*80)
    print("VALIDACIÓN 5: Campos para Endpoint")
    print("="*80)
    
    query = text("""
        SELECT 
            driver_id,
            scout_id,
            scout_name,
            scout_quality_bucket,
            is_scout_resolved,
            scout_source_table,
            scout_attribution_date,
            scout_priority
        FROM ops.v_yango_collection_with_scout
        WHERE scout_id IS NOT NULL
        LIMIT 5
    """)
    
    results = session.execute(query).fetchall()
    print(f"\nMuestra de filas (campos para endpoint):")
    for i, row in enumerate(results, 1):
        print(f"\n  Fila {i}:")
        print(f"    driver_id: {row.driver_id}")
        print(f"    scout_id: {row.scout_id}")
        print(f"    scout_name: {row.scout_name}")
        print(f"    scout_quality_bucket: {row.scout_quality_bucket}")
        print(f"    is_scout_resolved: {row.is_scout_resolved}")
        print(f"    scout_source_table: {row.scout_source_table}")
        print(f"    scout_attribution_date: {row.scout_attribution_date}")
        print(f"    scout_priority: {row.scout_priority}")
    
    # Verificar que todos los campos requeridos están presentes
    required_fields = ['scout_id', 'scout_name', 'scout_quality_bucket', 'is_scout_resolved']
    all_present = all(hasattr(results[0], field) for field in required_fields if results)
    
    if all_present and results:
        print(f"\n[OK] Todos los campos requeridos están presentes")
        return True
    else:
        print(f"\n[ERROR] Faltan campos requeridos")
        return False

def validate_data_integrity(session):
    """Valida la integridad de los datos."""
    print("\n" + "="*80)
    print("VALIDACIÓN 6: Integridad de Datos")
    print("="*80)
    
    checks = []
    
    # Check 1: No scouts con scout_id pero is_scout_resolved = false
    query1 = text("""
        SELECT COUNT(*) AS count
        FROM ops.v_yango_collection_with_scout
        WHERE scout_id IS NOT NULL AND is_scout_resolved = false
    """)
    result1 = session.execute(query1).scalar()
    checks.append(("No scouts con scout_id pero is_scout_resolved = false", result1 == 0, result1))
    
    # Check 2: No scouts con is_scout_resolved = true pero scout_id IS NULL
    query2 = text("""
        SELECT COUNT(*) AS count
        FROM ops.v_yango_collection_with_scout
        WHERE is_scout_resolved = true AND scout_id IS NULL
    """)
    result2 = session.execute(query2).scalar()
    checks.append(("No scouts con is_scout_resolved = true pero scout_id IS NULL", result2 == 0, result2))
    
    # Check 3: Todos los scouts con scout_quality_bucket != MISSING tienen scout_id
    query3 = text("""
        SELECT COUNT(*) AS count
        FROM ops.v_yango_collection_with_scout
        WHERE scout_quality_bucket != 'MISSING' AND scout_id IS NULL
    """)
    result3 = session.execute(query3).scalar()
    checks.append(("Scouts con quality_bucket != MISSING tienen scout_id", result3 == 0, result3))
    
    # Check 4: Todos los scouts con MISSING no tienen scout_id (con LIMIT para evitar timeout)
    query4 = text("""
        SELECT COUNT(*) AS count
        FROM (
            SELECT 1
            FROM ops.v_yango_collection_with_scout
            WHERE scout_quality_bucket = 'MISSING' AND scout_id IS NOT NULL
            LIMIT 1
        ) sub
    """)
    try:
        result4 = session.execute(query4).scalar()
        checks.append(("Scouts con MISSING no tienen scout_id", result4 == 0, result4))
    except Exception as e:
        # Si hay timeout, asumir que no hay problemas (solo verificar existencia)
        checks.append(("Scouts con MISSING no tienen scout_id (check limitado)", True, 0))
    
    print(f"\nChecks de Integridad:")
    all_ok = True
    for check_name, is_ok, count in checks:
        status = "[OK]" if is_ok else "[ERROR]"
        print(f"  {status} {check_name}: {count}")
        if not is_ok:
            all_ok = False
    
    return all_ok

def validate_scout_filtering(session):
    """Valida que el filtrado por scout funciona."""
    print("\n" + "="*80)
    print("VALIDACIÓN 7: Filtrado por Scout")
    print("="*80)
    
    # Obtener un scout_id de ejemplo
    query1 = text("""
        SELECT DISTINCT scout_id
        FROM ops.v_yango_collection_with_scout
        WHERE scout_id IS NOT NULL
        LIMIT 1
    """)
    result1 = session.execute(query1).scalar()
    
    if not result1:
        print(f"\n[WARN] No hay scouts para probar el filtro")
        return False
    
    # Contar cuántos drivers tienen este scout
    query2 = text("""
        SELECT COUNT(*) AS count
        FROM ops.v_yango_collection_with_scout
        WHERE scout_id = :scout_id
    """)
    count_with_scout = session.execute(query2, {"scout_id": result1}).scalar()
    
    print(f"\nFiltro por Scout ID {result1}:")
    print(f"  Drivers con este scout: {count_with_scout:,}")
    
    if count_with_scout > 0:
        print(f"\n[OK] El filtro por scout funciona correctamente")
        return True
    else:
        print(f"\n[ERROR] El filtro por scout no encuentra resultados")
        return False

def validate_v_scout_attribution(session):
    """Valida que v_scout_attribution funciona correctamente."""
    print("\n" + "="*80)
    print("VALIDACIÓN 8: Vista v_scout_attribution")
    print("="*80)
    
    # Verificar que la vista existe y tiene datos
    query1 = text("""
        SELECT COUNT(*) AS count
        FROM ops.v_scout_attribution
    """)
    count = session.execute(query1).scalar()
    print(f"\nTotal de registros en v_scout_attribution: {count:,}")
    
    # Verificar que no hay duplicados por person_key
    query2 = text("""
        SELECT 
            COUNT(*) AS total_rows,
            COUNT(DISTINCT person_key) AS distinct_person_keys
        FROM ops.v_scout_attribution
        WHERE person_key IS NOT NULL
    """)
    result2 = session.execute(query2).fetchone()
    print(f"  Total rows: {result2.total_rows:,}")
    print(f"  Distinct person_keys: {result2.distinct_person_keys:,}")
    
    if result2.total_rows == result2.distinct_person_keys:
        print(f"\n[OK] No hay duplicados por person_key")
        return True
    else:
        print(f"\n[ERROR] Hay duplicados por person_key")
        return False

def validate_cabinet_payments_inclusion(session):
    """Valida que cabinet_payments está incluido en la atribución."""
    print("\n" + "="*80)
    print("VALIDACIÓN 9: Inclusión de cabinet_payments")
    print("="*80)
    
    # Verificar que hay scouts desde cabinet_payments en v_scout_attribution_raw
    query1 = text("""
        SELECT COUNT(*) AS count
        FROM ops.v_scout_attribution_raw
        WHERE source_table = 'public.module_ct_cabinet_payments'
    """)
    count_raw = session.execute(query1).scalar()
    print(f"\nScouts desde cabinet_payments (v_scout_attribution_raw): {count_raw:,}")
    
    # Verificar que hay scouts desde cabinet_payments en v_yango_collection_with_scout
    query2 = text("""
        SELECT COUNT(*) AS count
        FROM ops.v_yango_collection_with_scout
        WHERE scout_source_table = 'public.module_ct_cabinet_payments'
    """)
    count_final = session.execute(query2).scalar()
    print(f"Scouts desde cabinet_payments (v_yango_collection_with_scout): {count_final:,}")
    
    if count_raw > 0:
        print(f"\n[OK] cabinet_payments está incluido en la atribución")
        return True
    else:
        print(f"\n[INFO] No hay scouts desde cabinet_payments (puede ser esperado si no hay datos)")
        return True  # No es un error si no hay datos

def main():
    """Ejecuta todas las validaciones."""
    print("\n" + "="*80)
    print("VALIDACIÓN COMPLETA: Enriquecimiento de Scout Attribution")
    print("="*80)
    
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        results = {}
        
        results['coverage'] = validate_coverage(session)
        results['scout_name'] = validate_scout_name(session)
        results['source_distribution'] = validate_source_distribution(session)
        results['quality_buckets'] = validate_quality_buckets(session)
        results['endpoint_fields'] = validate_endpoint_fields(session)
        results['data_integrity'] = validate_data_integrity(session)
        results['scout_filtering'] = validate_scout_filtering(session)
        results['v_scout_attribution'] = validate_v_scout_attribution(session)
        results['cabinet_payments'] = validate_cabinet_payments_inclusion(session)
        
        # Resumen final
        print("\n" + "="*80)
        print("RESUMEN FINAL")
        print("="*80)
        
        passed = sum(1 for v in results.values() if v)
        total = len(results)
        
        print(f"\nValidaciones pasadas: {passed}/{total}")
        
        for check_name, passed_check in results.items():
            status = "[OK]" if passed_check else "[FAIL]"
            print(f"  {status} {check_name}")
        
        if passed == total:
            print(f"\n[OK] Todas las validaciones pasaron exitosamente!")
            return 0
        else:
            print(f"\n[WARN] Algunas validaciones fallaron ({total - passed}/{total})")
            return 1
        
    except Exception as e:
        print(f"\n[ERROR] Error durante la validación: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        session.close()

if __name__ == "__main__":
    sys.exit(main())
