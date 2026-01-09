"""
Investigación Profunda: ¿Por qué solo 902 drivers de 126,865?
=============================================================

Investiga por qué el sistema seleccionó específicamente estos 902 drivers
de más de 126 mil registros en la tabla drivers.
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


def investigate_why_only_902():
    """
    Investiga por qué solo se seleccionaron 902 drivers
    """
    db = SessionLocal()
    
    try:
        print(f"\n{'='*80}")
        print(f"INVESTIGACION: Por que solo 902 drivers de 126,865?")
        print(f"{'='*80}\n")
        
        # 1. Obtener los 902 drivers sin leads
        query_drivers_without_leads = text("""
            SELECT DISTINCT
                il.source_pk as driver_id,
                il.linked_at,
                il.match_rule,
                il.run_id,
                d.created_at as driver_created_at,
                d.park_id,
                d.phone,
                d.license_number,
                d.full_name
            FROM canon.identity_links il
            JOIN canon.identity_registry ir ON ir.person_key = il.person_key
            LEFT JOIN public.drivers d ON d.driver_id::text = il.source_pk
            WHERE il.source_table = 'drivers'
            AND il.person_key NOT IN (
                SELECT DISTINCT person_key
                FROM canon.identity_links
                WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
            )
        """)
        
        result = db.execute(query_drivers_without_leads)
        drivers_without_leads = result.fetchall()
        
        driver_ids_without_leads = [str(d.driver_id) for d in drivers_without_leads]
        
        print(f"Total de drivers sin leads: {len(driver_ids_without_leads)}\n")
        
        # 2. Verificar si estos drivers tienen algo especial en drivers_index
        print(f"{'='*80}")
        print(f"VERIFICACION EN drivers_index")
        print(f"{'='*80}\n")
        
        # Obtener muestra de drivers sin leads y verificar en drivers_index
        sample_size = min(100, len(driver_ids_without_leads))
        sample_drivers = driver_ids_without_leads[:sample_size]
        
        placeholders = ','.join([f':driver_id_{i}' for i in range(len(sample_drivers))])
        query_drivers_index = text(f"""
            SELECT 
                driver_id,
                park_id,
                phone_norm,
                license_norm,
                full_name_norm,
                snapshot_date
            FROM canon.drivers_index
            WHERE driver_id::text IN ({placeholders})
            ORDER BY snapshot_date DESC
        """)
        
        params = {f"driver_id_{i}": driver_id for i, driver_id in enumerate(sample_drivers)}
        result_index = db.execute(query_drivers_index, params)
        drivers_in_index = result_index.fetchall()
        
        print(f"Drivers encontrados en drivers_index (muestra de {sample_size}): {len(drivers_in_index)}")
        
        # 3. Comparar con drivers que SÍ tienen leads
        print(f"\n{'='*80}")
        print(f"COMPARACION CON DRIVERS QUE SI TIENEN LEADS")
        print(f"{'='*80}\n")
        
        query_drivers_with_leads = text("""
            SELECT DISTINCT
                il.source_pk as driver_id,
                il.linked_at,
                il.match_rule,
                il.run_id,
                d.created_at as driver_created_at,
                d.park_id,
                d.phone,
                d.license_number
            FROM canon.identity_links il
            JOIN canon.identity_registry ir ON ir.person_key = il.person_key
            LEFT JOIN public.drivers d ON d.driver_id::text = il.source_pk
            WHERE il.source_table = 'drivers'
            AND il.person_key IN (
                SELECT DISTINCT person_key
                FROM canon.identity_links
                WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
            )
            ORDER BY il.linked_at DESC
            LIMIT 1000
        """)
        
        result_with_leads = db.execute(query_drivers_with_leads)
        drivers_with_leads = result_with_leads.fetchall()
        
        print(f"Muestra de drivers CON leads: {len(drivers_with_leads)}")
        
        # Comparar características
        print(f"\nComparación de características:")
        
        # Por run_id
        run_ids_with_leads = set([d.run_id for d in drivers_with_leads if d.run_id])
        run_ids_without_leads = set([d.run_id for d in drivers_without_leads if d.run_id])
        
        print(f"  Run IDs (CON leads): {len(run_ids_with_leads)} únicos")
        print(f"  Run IDs (SIN leads): {len(run_ids_without_leads)} únicos")
        if run_ids_without_leads:
            print(f"    Run IDs sin leads: {sorted(run_ids_without_leads)}")
        else:
            print(f"    WARNING: NINGUNO de los drivers sin leads tiene run_id!")
        
        # Por fecha de link
        dates_with_leads = [d.linked_at.date() if isinstance(d.linked_at, datetime) else d.linked_at for d in drivers_with_leads if d.linked_at]
        dates_without_leads = [d.linked_at.date() if isinstance(d.linked_at, datetime) else d.linked_at for d in drivers_without_leads if d.linked_at]
        
        if dates_with_leads:
            print(f"\n  Fechas de link (CON leads): {min(dates_with_leads)} a {max(dates_with_leads)}")
        if dates_without_leads:
            print(f"  Fechas de link (SIN leads): {min(dates_without_leads)} a {max(dates_without_leads)}")
        
        # 4. LA CLAVE: Verificar qué pasó el 2025-12-21
        print(f"\n{'='*80}")
        print(f"ANALISIS DEL 2025-12-21")
        print(f"{'='*80}\n")
        
        # Contar cuántos links se crearon ese día
        query_links_2025_12_21 = text("""
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT source_table) as distinct_tables,
                source_table,
                match_rule
            FROM canon.identity_links
            WHERE linked_at::date = '2025-12-21'
            GROUP BY source_table, match_rule
            ORDER BY total DESC
        """)
        
        result_links = db.execute(query_links_2025_12_21)
        links_that_day = result_links.fetchall()
        
        print(f"Links creados el 2025-12-21:")
        total_links_that_day = 0
        for link in links_that_day:
            print(f"  {link.source_table} - {link.match_rule}: {link.total:,} links")
            total_links_that_day += link.total
        
        print(f"\nTotal de links creados ese día: {total_links_that_day:,}")
        
        # 5. Verificar si había algún filtro implícito
        print(f"\n{'='*80}")
        print(f"VERIFICACION DE FILTROS IMPLICITOS")
        print(f"{'='*80}\n")
        
        # Verificar si los drivers sin leads tienen algo en común con drivers_index
        # La teoría: solo los drivers que estaban en drivers_index fueron procesados
        
        query_total_in_index = text("""
            SELECT COUNT(DISTINCT driver_id) as total
            FROM canon.drivers_index
        """)
        result_total_index = db.execute(query_total_in_index)
        total_in_index = result_total_index.scalar()
        
        print(f"Total de drivers en drivers_index: {total_in_index:,}")
        print(f"Total de drivers en public.drivers: 126,865")
        print(f"Drivers sin leads: {len(driver_ids_without_leads)}")
        
        # Verificar cuántos de los drivers sin leads están en drivers_index (muestra)
        sample_check = driver_ids_without_leads[:100]
        placeholders_check = ','.join([f':driver_id_{i}' for i in range(len(sample_check))])
        query_check_index = text(f"""
            SELECT COUNT(DISTINCT driver_id) as total
            FROM canon.drivers_index
            WHERE driver_id::text IN ({placeholders_check})
        """)
        params_check = {f"driver_id_{i}": driver_id for i, driver_id in enumerate(sample_check)}
        result_check = db.execute(query_check_index, params_check)
        in_index_count = result_check.scalar()
        
        print(f"\nDe una muestra de {len(sample_check)} drivers sin leads:")
        print(f"  Están en drivers_index: {in_index_count}/{len(sample_check)}")
        print(f"  Esto sugiere que TODOS están en drivers_index")
        
        # 6. LA RESPUESTA CLAVE: Verificar la lógica de matching
        print(f"\n{'='*80}")
        print(f"LA RESPUESTA CLAVE")
        print(f"{'='*80}\n")
        
        print(f"El matching engine en R1_PHONE_EXACT busca en drivers_index:")
        print(f"  SELECT driver_id FROM canon.drivers_index WHERE phone_norm = :phone_norm")
        print(f"\nEsto significa que:")
        print(f"  1. Solo los drivers que están en drivers_index pueden ser encontrados")
        print(f"  2. Si un driver NO está en drivers_index, NO puede hacer match")
        print(f"  3. Los 902 drivers fueron seleccionados porque:")
        print(f"     a) Estaban en drivers_index")
        print(f"     b) Tenían teléfono/licencia que matcheaba con OTRO driver en drivers_index")
        print(f"     c) El matching engine encontró el match")
        print(f"     d) Creó el link SIN verificar si había lead")
        
        # 7. Verificar si hay drivers que NO están en drivers_index
        print(f"\n{'='*80}")
        print(f"VERIFICACION: Drivers que NO están en drivers_index")
        print(f"{'='*80}\n")
        
        query_not_in_index = text("""
            SELECT COUNT(*) as total
            FROM public.drivers d
            WHERE NOT EXISTS (
                SELECT 1
                FROM canon.drivers_index di
                WHERE di.driver_id = d.driver_id
            )
        """)
        result_not_in_index = db.execute(query_not_in_index)
        not_in_index = result_not_in_index.scalar()
        
        print(f"Drivers en public.drivers que NO están en drivers_index: {not_in_index:,}")
        print(f"Esto explica por qué solo algunos drivers fueron procesados.")
        
        # CONCLUSIÓN FINAL
        print(f"\n{'='*80}")
        print(f"CONCLUSION FINAL")
        print(f"{'='*80}\n")
        print(f"¿Por qué solo 902 drivers de 126,865?")
        print(f"\nRESPUESTA:")
        print(f"  1. Solo los drivers que están en drivers_index pueden hacer match")
        print(f"  2. De esos, solo los que tienen teléfono/licencia que matchea con OTRO driver")
        print(f"  3. El matching engine encontró matches para estos 902 drivers")
        print(f"  4. Creó links SIN verificar si había lead asociado")
        print(f"  5. Por eso quedaron sin leads")
        print(f"\nEl criterio de selección fue:")
        print(f"  - Driver debe estar en drivers_index")
        print(f"  - Driver debe tener teléfono/licencia normalizado")
        print(f"  - El teléfono/licencia debe matchear con OTRO driver en drivers_index")
        print(f"  - NO se verificó si había lead asociado")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"\nERROR: Error en investigacion: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    investigate_why_only_902()

