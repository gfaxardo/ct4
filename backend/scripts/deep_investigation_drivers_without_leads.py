"""
Script de Investigación Profunda: Drivers sin Leads
===================================================

Análisis detallado de los 902 drivers restantes sin leads:
- Origen temporal (cuándo fueron creados)
- Características (teléfono, licencia, nombre)
- Posibles causas de entrada al sistema
- Recomendaciones de acción
"""

import sys
from pathlib import Path
from datetime import datetime, date
from collections import defaultdict

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db import SessionLocal
from app.services.normalization import normalize_phone, normalize_license


def deep_investigation():
    """
    Investigación profunda de drivers sin leads
    """
    db = SessionLocal()
    
    try:
        print(f"\n{'='*80}")
        print(f"INVESTIGACION PROFUNDA: Drivers sin Leads")
        print(f"{'='*80}\n")
        
        # Obtener drivers sin leads con información detallada
        query = text("""
            SELECT DISTINCT
                il.source_pk as driver_id,
                ir.person_key,
                ir.primary_phone,
                ir.primary_license,
                ir.primary_full_name,
                il.match_rule,
                il.linked_at,
                il.snapshot_date,
                il.evidence,
                d.created_at as driver_created_at,
                d.hire_date,
                d.park_id
            FROM canon.identity_links il
            JOIN canon.identity_registry ir ON ir.person_key = il.person_key
            LEFT JOIN public.drivers d ON d.driver_id::text = il.source_pk
            WHERE il.source_table = 'drivers'
            AND il.person_key NOT IN (
                SELECT DISTINCT person_key
                FROM canon.identity_links
                WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
            )
            ORDER BY il.linked_at DESC
        """)
        
        result = db.execute(query)
        drivers = result.fetchall()
        
        print(f"Total de drivers sin leads: {len(drivers)}\n")
        
        # Análisis por fecha de creación del link
        by_linked_date = defaultdict(int)
        by_driver_created_date = defaultdict(int)
        by_match_rule = defaultdict(int)
        by_park = defaultdict(int)
        drivers_with_phone = 0
        drivers_with_license = 0
        drivers_with_both = 0
        drivers_with_neither = 0
        
        # Análisis de evidencia
        created_by_ensure = 0
        created_by_matching = 0
        
        for driver in drivers:
            # Por fecha de link
            if driver.linked_at:
                link_date = driver.linked_at.date() if isinstance(driver.linked_at, datetime) else driver.linked_at
                by_linked_date[link_date] += 1
            
            # Por fecha de creación del driver
            if driver.driver_created_at:
                driver_date = driver.driver_created_at.date() if isinstance(driver.driver_created_at, datetime) else driver.driver_created_at
                by_driver_created_date[driver_date] += 1
            
            # Por regla
            by_match_rule[driver.match_rule or 'UNKNOWN'] += 1
            
            # Por parque
            if driver.park_id:
                by_park[str(driver.park_id)] += 1
            
            # Por datos disponibles
            has_phone = bool(driver.primary_phone)
            has_license = bool(driver.primary_license)
            
            if has_phone:
                drivers_with_phone += 1
            if has_license:
                drivers_with_license += 1
            if has_phone and has_license:
                drivers_with_both += 1
            if not has_phone and not has_license:
                drivers_with_neither += 1
            
            # Por evidencia
            if driver.evidence:
                evidence_str = str(driver.evidence)
                if 'ensure_driver_identity_link' in evidence_str:
                    created_by_ensure += 1
                elif 'driver_direct' in evidence_str or driver.match_rule == 'driver_direct':
                    created_by_ensure += 1
                else:
                    created_by_matching += 1
        
        # Reporte
        print(f"{'='*80}")
        print(f"ANALISIS TEMPORAL")
        print(f"{'='*80}\n")
        
        print(f"Por fecha de creación del link (Top 10):")
        sorted_linked = sorted(by_linked_date.items(), key=lambda x: x[0], reverse=True)[:10]
        for link_date, count in sorted_linked:
            print(f"  {link_date}: {count} drivers")
        
        print(f"\nPor fecha de creación del driver (Top 10):")
        sorted_driver = sorted(by_driver_created_date.items(), key=lambda x: x[0], reverse=True)[:10]
        for driver_date, count in sorted_driver:
            print(f"  {driver_date}: {count} drivers")
        
        print(f"\n{'='*80}")
        print(f"ANALISIS POR REGLA DE CREACION")
        print(f"{'='*80}\n")
        for rule, count in sorted(by_match_rule.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / len(drivers)) * 100
            print(f"  {rule}: {count} ({percentage:.1f}%)")
        
        print(f"\n{'='*80}")
        print(f"ANALISIS POR PARQUE (Top 10)")
        print(f"{'='*80}\n")
        sorted_parks = sorted(by_park.items(), key=lambda x: x[1], reverse=True)[:10]
        for park_id, count in sorted_parks:
            print(f"  Park {park_id}: {count} drivers")
        
        print(f"\n{'='*80}")
        print(f"ANALISIS DE DATOS DISPONIBLES")
        print(f"{'='*80}\n")
        print(f"  Con teléfono: {drivers_with_phone} ({drivers_with_phone/len(drivers)*100:.1f}%)")
        print(f"  Con licencia: {drivers_with_license} ({drivers_with_license/len(drivers)*100:.1f}%)")
        print(f"  Con ambos: {drivers_with_both} ({drivers_with_both/len(drivers)*100:.1f}%)")
        print(f"  Sin ninguno: {drivers_with_neither} ({drivers_with_neither/len(drivers)*100:.1f}%)")
        
        print(f"\n{'='*80}")
        print(f"ANALISIS DE ORIGEN")
        print(f"{'='*80}\n")
        print(f"  Creados por ensure_driver_identity_link: {created_by_ensure} ({created_by_ensure/len(drivers)*100:.1f}%)")
        print(f"  Creados por matching engine: {created_by_matching} ({created_by_matching/len(drivers)*100:.1f}%)")
        
        # Verificar si hay drivers recientes que deberían tener leads
        print(f"\n{'='*80}")
        print(f"DRIVERS RECIENTES (últimos 30 días)")
        print(f"{'='*80}\n")
        
        recent_cutoff = datetime.now().date() - timedelta(days=30)
        recent_drivers = [
            d for d in drivers 
            if d.linked_at and (
                (isinstance(d.linked_at, datetime) and d.linked_at.date() >= recent_cutoff) or
                (isinstance(d.linked_at, date) and d.linked_at >= recent_cutoff)
            )
        ]
        
        print(f"Drivers creados en los últimos 30 días: {len(recent_drivers)}")
        if recent_drivers:
            print(f"\nMuestra de drivers recientes (Top 10):")
            for idx, driver in enumerate(recent_drivers[:10], 1):
                print(f"\n{idx}. Driver ID: {driver.driver_id[:20]}...")
                print(f"   Linked at: {driver.linked_at}")
                print(f"   Match Rule: {driver.match_rule}")
                print(f"   Phone: {driver.primary_phone or 'N/A'}")
                print(f"   License: {driver.primary_license or 'N/A'}")
                print(f"   Name: {driver.primary_full_name or 'N/A'}")
        
        # Recomendaciones
        print(f"\n{'='*80}")
        print(f"RECOMENDACIONES")
        print(f"{'='*80}\n")
        
        print(f"1. MODIFICAR FLUJO DE INGESTA:")
        print(f"   - process_drivers() NO debe crear links si no hay lead asociado")
        print(f"   - ensure_driver_identity_link() debe verificar existencia de lead antes de crear link")
        
        print(f"\n2. DECISION SOBRE DRIVERS EXISTENTES:")
        print(f"   - {len(recent_drivers)} drivers recientes pueden tener leads no detectados")
        print(f"   - {drivers_with_neither} drivers sin teléfono ni licencia son casos especiales")
        print(f"   - Considerar marcarlos con flag especial en lugar de eliminarlos")
        
        print(f"\n3. PREVENCION FUTURA:")
        print(f"   - Los drivers solo deben entrar al sistema cuando:")
        print(f"     a) Hay un lead asociado (cabinet/scouting/migrations)")
        print(f"     b) Se está haciendo matching de un lead existente")
        print(f"     c) NO cuando se procesa drivers directamente sin contexto de lead")
        
        print(f"\n{'='*80}\n")
        
        return {
            "total_drivers": len(drivers),
            "by_match_rule": dict(by_match_rule),
            "by_linked_date": {str(k): v for k, v in by_linked_date.items()},
            "drivers_with_phone": drivers_with_phone,
            "drivers_with_license": drivers_with_license,
            "drivers_with_both": drivers_with_both,
            "drivers_with_neither": drivers_with_neither,
            "created_by_ensure": created_by_ensure,
            "created_by_matching": created_by_matching,
            "recent_drivers": len(recent_drivers)
        }
        
    except Exception as e:
        print(f"\nERROR: Error en investigacion: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    from datetime import timedelta
    deep_investigation()

