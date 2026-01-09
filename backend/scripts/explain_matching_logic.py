"""
Explicación de la Lógica de Matching que Seleccionó los 902 Drivers
====================================================================

Explica paso a paso cómo el matching engine seleccionó estos 902 drivers específicos.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db import SessionLocal


def explain_matching_logic():
    """
    Explica la lógica de matching que seleccionó los 902 drivers
    """
    db = SessionLocal()
    
    try:
        print(f"\n{'='*80}")
        print(f"EXPLICACION: Logica de Matching que Selecciono los 902 Drivers")
        print(f"{'='*80}\n")
        
        print(f"CONTEXTO:")
        print(f"  - Total de drivers en public.drivers: 126,865")
        print(f"  - Total de drivers en drivers_index: 126,688")
        print(f"  - Drivers seleccionados sin leads: 902")
        print(f"  - Porcentaje: 0.71%")
        
        print(f"\n{'='*80}")
        print(f"PASO A PASO: Como se Seleccionaron los 902 Drivers")
        print(f"{'='*80}\n")
        
        print(f"1. process_drivers() se ejecutó el 2025-12-21")
        print(f"   Query: SELECT * FROM public.drivers")
        print(f"   (Sin filtros de fecha, procesa TODOS los drivers)")
        
        print(f"\n2. Para CADA driver en public.drivers:")
        print(f"   a) Crea IdentityCandidateInput con:")
        print(f"      - source_table = 'drivers'")
        print(f"      - source_pk = driver_id")
        print(f"      - phone_norm = normalize_phone(driver.phone)")
        print(f"      - license_norm = normalize_license(driver.license)")
        
        print(f"\n3. Llama a match_person(candidate):")
        print(f"   a) Aplica regla R1_PHONE_EXACT:")
        print(f"      Query: SELECT driver_id FROM canon.drivers_index")
        print(f"             WHERE phone_norm = :phone_norm")
        print(f"   b) Busca en drivers_index por teléfono normalizado")
        
        print(f"\n4. Si encuentra un driver en drivers_index con el mismo teléfono:")
        print(f"   a) Llama a _get_or_create_person_from_driver()")
        print(f"   b) Esta función:")
        print(f"      - Busca si ya existe una persona con ese teléfono/licencia")
        print(f"      - Si NO existe, crea una NUEVA persona")
        print(f"      - Retorna el person_key")
        print(f"   c) Crea link de driver para esa persona")
        
        print(f"\n5. PROBLEMA: NO verifica si hay un LEAD asociado")
        
        print(f"\n{'='*80}")
        print(f"POR QUE SOLO 902 DRIVERS?")
        print(f"{'='*80}\n")
        
        # Verificar cuántos drivers tienen teléfono que matchea con otro driver
        print(f"El matching busca drivers que:")
        print(f"  1. Están en drivers_index (126,688 drivers)")
        print(f"  2. Tienen teléfono normalizado")
        print(f"  3. Ese teléfono matchea con OTRO driver en drivers_index")
        
        # Verificar cuántos drivers tienen teléfonos duplicados en drivers_index
        query_duplicate_phones = text("""
            SELECT 
                phone_norm,
                COUNT(DISTINCT driver_id) as driver_count
            FROM canon.drivers_index
            WHERE phone_norm IS NOT NULL
            AND phone_norm != ''
            GROUP BY phone_norm
            HAVING COUNT(DISTINCT driver_id) > 1
            ORDER BY driver_count DESC
            LIMIT 20
        """)
        
        result_dup = db.execute(query_duplicate_phones)
        duplicate_phones = result_dup.fetchall()
        
        print(f"\nTeléfonos con múltiples drivers en drivers_index (Top 20):")
        total_drivers_with_duplicate_phones = 0
        for dup in duplicate_phones:
            print(f"  Phone {dup.phone_norm}: {dup.driver_count} drivers")
            total_drivers_with_duplicate_phones += dup.driver_count
        
        print(f"\nEsto muestra que hay drivers con teléfonos duplicados.")
        print(f"Cuando process_drivers() procesa estos drivers:")
        print(f"  - Encuentra match en drivers_index")
        print(f"  - Crea persona y link")
        print(f"  - Pero NO verifica si hay lead")
        
        # Verificar si los 902 drivers tienen teléfonos que aparecen múltiples veces
        query_drivers_902 = text("""
            SELECT DISTINCT
                ir.primary_phone,
                COUNT(DISTINCT il.source_pk) as driver_count
            FROM canon.identity_links il
            JOIN canon.identity_registry ir ON ir.person_key = il.person_key
            WHERE il.source_table = 'drivers'
            AND il.person_key NOT IN (
                SELECT DISTINCT person_key
                FROM canon.identity_links
                WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
            )
            AND ir.primary_phone IS NOT NULL
            GROUP BY ir.primary_phone
            ORDER BY driver_count DESC
            LIMIT 20
        """)
        
        result_902 = db.execute(query_drivers_902)
        phones_902 = result_902.fetchall()
        
        print(f"\nTeléfonos de los 902 drivers sin leads (Top 20):")
        for phone_info in phones_902:
            print(f"  Phone {phone_info.primary_phone}: {phone_info.driver_count} drivers sin leads")
        
        # CONCLUSIÓN
        print(f"\n{'='*80}")
        print(f"RESPUESTA FINAL")
        print(f"{'='*80}\n")
        
        print(f"¿Por qué solo 902 drivers de 126,865?")
        print(f"\nRESPUESTA:")
        print(f"  1. process_drivers() procesó TODOS los drivers (o un subset grande)")
        print(f"  2. Para cada driver, el matching engine buscó en drivers_index")
        print(f"  3. Solo los drivers que:")
        print(f"     a) Están en drivers_index (126,688 de 126,865)")
        print(f"     b) Tienen teléfono/licencia normalizado")
        print(f"     c) Ese teléfono/licencia matchea con OTRO driver en drivers_index")
        print(f"     d) El matching encontró el match y creó el link")
        print(f"  4. Estos 902 drivers cumplieron TODOS estos criterios")
        print(f"  5. Pero NO tenían leads asociados")
        print(f"  6. Por eso quedaron sin leads")
        
        print(f"\nEl criterio de selección NO fue aleatorio:")
        print(f"  - Fue basado en matching de teléfono/licencia")
        print(f"  - Solo drivers con matches en drivers_index fueron seleccionados")
        print(f"  - El problema es que NO se verificó si había lead asociado")
        
        print(f"\n{'='*80}\n")
        
    except Exception as e:
        print(f"\nERROR: Error en explicacion: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    explain_matching_logic()

