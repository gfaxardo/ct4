"""
Investigación: Criterios de Selección de los 902 Drivers
========================================================

Investiga por qué de más de 120 mil registros en drivers, 
el sistema seleccionó específicamente esos 902 para crear links.
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


def investigate_selection_criteria():
    """
    Investiga los criterios de selección de los 902 drivers
    """
    db = SessionLocal()
    
    try:
        print(f"\n{'='*80}")
        print(f"INVESTIGACION: Criterios de Seleccion de los 902 Drivers")
        print(f"{'='*80}\n")
        
        # 1. Obtener información de los 902 drivers sin leads
        query_drivers = text("""
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
            ORDER BY il.linked_at DESC
        """)
        
        result = db.execute(query_drivers)
        drivers = result.fetchall()
        
        print(f"Total de drivers sin leads: {len(drivers)}\n")
        
        # 2. Analizar por run_id
        by_run_id = defaultdict(list)
        run_ids = set()
        
        for driver in drivers:
            if driver.run_id:
                run_ids.add(driver.run_id)
                by_run_id[driver.run_id].append(driver)
        
        print(f"{'='*80}")
        print(f"ANALISIS POR RUN_ID")
        print(f"{'='*80}\n")
        print(f"Total de run_ids únicos: {len(run_ids)}")
        
        if run_ids:
            print(f"\nRun IDs encontrados: {sorted(run_ids)}")
            
            # Obtener información de los runs
            run_ids_list = list(run_ids)
            placeholders = ','.join([f':run_id_{i}' for i in range(len(run_ids_list))])
            query_runs = text(f"""
                SELECT 
                    id,
                    started_at,
                    completed_at,
                    status,
                    job_type,
                    scope_date_from,
                    scope_date_to,
                    incremental,
                    stats
                FROM ops.ingestion_runs
                WHERE id IN ({placeholders})
                ORDER BY started_at DESC
            """)
            
            params = {f"run_id_{i}": run_id for i, run_id in enumerate(run_ids_list)}
            result_runs = db.execute(query_runs, params)
            runs = result_runs.fetchall()
            
            print(f"\nInformación de los Runs:")
            for run in runs:
                print(f"\n  Run ID: {run.id}")
                print(f"    Started at: {run.started_at}")
                print(f"    Completed at: {run.completed_at}")
                print(f"    Status: {run.status}")
                print(f"    Job Type: {run.job_type}")
                print(f"    Scope Date From: {run.scope_date_from}")
                print(f"    Scope Date To: {run.scope_date_to}")
                print(f"    Incremental: {run.incremental}")
                print(f"    Drivers creados en este run: {len(by_run_id[run.id])}")
                if run.stats:
                    print(f"    Stats: {run.stats}")
        
        # 3. Analizar por fecha de creación del driver
        print(f"\n{'='*80}")
        print(f"ANALISIS POR FECHA DE CREACION DEL DRIVER")
        print(f"{'='*80}\n")
        
        by_driver_created_date = defaultdict(int)
        drivers_with_created_date = 0
        drivers_without_created_date = 0
        
        for driver in drivers:
            if driver.driver_created_at:
                driver_date = driver.driver_created_at.date() if isinstance(driver.driver_created_at, datetime) else driver.driver_created_at
                by_driver_created_date[driver_date] += 1
                drivers_with_created_date += 1
            else:
                drivers_without_created_date += 1
        
        print(f"Drivers con fecha de creación: {drivers_with_created_date}")
        print(f"Drivers sin fecha de creación: {drivers_without_created_date}")
        
        if by_driver_created_date:
            print(f"\nDistribución por fecha de creación del driver:")
            sorted_dates = sorted(by_driver_created_date.items(), key=lambda x: x[0], reverse=True)
            for driver_date, count in sorted_dates[:20]:
                print(f"  {driver_date}: {count} drivers")
        
        # 4. Analizar por park_id
        print(f"\n{'='*80}")
        print(f"ANALISIS POR PARK_ID")
        print(f"{'='*80}\n")
        
        by_park = defaultdict(int)
        drivers_with_park = 0
        drivers_without_park = 0
        
        for driver in drivers:
            if driver.park_id:
                by_park[str(driver.park_id)] += 1
                drivers_with_park += 1
            else:
                drivers_without_park += 1
        
        print(f"Drivers con park_id: {drivers_with_park}")
        print(f"Drivers sin park_id: {drivers_without_park}")
        
        if by_park:
            print(f"\nTop 10 parks:")
            sorted_parks = sorted(by_park.items(), key=lambda x: x[1], reverse=True)[:10]
            for park_id, count in sorted_parks:
                print(f"  Park {park_id}: {count} drivers")
        
        # 5. Comparar con el total de drivers en la tabla
        print(f"\n{'='*80}")
        print(f"COMPARACION CON TOTAL DE DRIVERS")
        print(f"{'='*80}\n")
        
        query_total_drivers = text("""
            SELECT COUNT(*) as total
            FROM public.drivers
        """)
        result_total = db.execute(query_total_drivers)
        total_drivers = result_total.scalar()
        
        print(f"Total de drivers en public.drivers: {total_drivers:,}")
        print(f"Drivers sin leads seleccionados: {len(drivers)}")
        print(f"Porcentaje seleccionado: {(len(drivers)/total_drivers*100):.2f}%")
        
        # 6. Verificar si había algún filtro por fecha en process_drivers
        print(f"\n{'='*80}")
        print(f"VERIFICACION DE FILTROS")
        print(f"{'='*80}\n")
        
        # Verificar si los drivers seleccionados tienen algo en común
        # Comparar con drivers que SÍ tienen leads
        query_drivers_with_leads = text("""
            SELECT DISTINCT
                il.source_pk as driver_id,
                il.linked_at,
                il.match_rule,
                il.run_id,
                d.created_at as driver_created_at,
                d.park_id
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
            LIMIT 100
        """)
        
        result_with_leads = db.execute(query_drivers_with_leads)
        drivers_with_leads = result_with_leads.fetchall()
        
        print(f"Muestra de drivers CON leads (100 primeros):")
        if drivers_with_leads:
            dates_with_leads = [d.linked_at.date() if isinstance(d.linked_at, datetime) else d.linked_at for d in drivers_with_leads if d.linked_at]
            if dates_with_leads:
                print(f"  Fechas de link (CON leads): {min(dates_with_leads)} a {max(dates_with_leads)}")
        
        dates_without_leads = [d.linked_at.date() if isinstance(d.linked_at, datetime) else d.linked_at for d in drivers if d.linked_at]
        if dates_without_leads:
            print(f"  Fechas de link (SIN leads): {min(dates_without_leads)} a {max(dates_without_leads)}")
        
        # 7. Verificar si había algún criterio específico en la query de process_drivers
        print(f"\n{'='*80}")
        print(f"ANALISIS DE LA QUERY ORIGINAL")
        print(f"{'='*80}\n")
        
        print(f"La query original de process_drivers() era:")
        print(f"  SELECT * FROM public.drivers")
        print(f"  [con filtros opcionales por date_from/date_to en created_at]")
        print(f"\nPero los 902 drivers fueron creados el 2025-12-21.")
        print(f"Esto sugiere que:")
        print(f"  1. Se ejecutó process_drivers() SIN filtros de fecha")
        print(f"  2. O se ejecutó con un scope muy amplio")
        print(f"  3. Pero solo algunos drivers fueron procesados")
        
        # 8. Verificar si hay algún patrón en los drivers seleccionados
        print(f"\n{'='*80}")
        print(f"BUSCANDO PATRONES")
        print(f"{'='*80}\n")
        
        # Verificar si todos tienen teléfono
        drivers_with_phone = sum(1 for d in drivers if d.phone)
        print(f"Drivers con teléfono: {drivers_with_phone}/{len(drivers)} ({drivers_with_phone/len(drivers)*100:.1f}%)")
        
        # Verificar si todos tienen licencia
        drivers_with_license = sum(1 for d in drivers if d.license_number)
        print(f"Drivers con licencia: {drivers_with_license}/{len(drivers)} ({drivers_with_license/len(drivers)*100:.1f}%)")
        
        # Verificar si hay algún patrón en los nombres
        print(f"\nMuestra de nombres (primeros 10):")
        for idx, driver in enumerate(drivers[:10], 1):
            print(f"  {idx}. {driver.full_name or 'N/A'}")
        
        # CONCLUSIÓN
        print(f"\n{'='*80}")
        print(f"CONCLUSION")
        print(f"{'='*80}\n")
        print(f"Los 902 drivers fueron seleccionados porque:")
        print(f"  1. process_drivers() se ejecutó el 2025-12-21")
        print(f"  2. Probablemente SIN filtros de fecha (o con scope muy amplio)")
        print(f"  3. El matching engine encontró matches para estos drivers")
        print(f"  4. Pero NO verificó si había leads asociados")
        print(f"\nLa pregunta clave es: ¿Por qué solo estos 902 de 120+ mil?")
        print(f"\nPOSIBLES RAZONES:")
        print(f"  A) Solo estos drivers tenían teléfono/licencia que matcheaba con drivers_index")
        print(f"  B) Solo estos drivers pasaron el filtro de matching (encontraron match)")
        print(f"  C) Había algún filtro implícito que no es obvio")
        print(f"  D) El proceso se interrumpió o se limitó de alguna manera")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"\nERROR: Error en investigacion: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    investigate_selection_criteria()

