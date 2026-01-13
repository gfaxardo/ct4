"""
Script para ejecutar diagnóstico de matches entre drivers en cuarentena y lead_events
Ejecuta los queries SQL de diagnose_quarantined_matches.sql y muestra resultados
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_diagnosis_sample():
    """Ejecuta queries de diagnóstico de matches"""
    db = SessionLocal()
    
    try:
        print("\n" + "="*80)
        print("DIAGNÓSTICO: Matches entre Drivers en Cuarentena y lead_events")
        print("="*80 + "\n")
        
        # Query 1: Matches por driver_id directo
        print("1. MATCHES POR DRIVER_ID DIRECTO (migrations):")
        print("-" * 80)
        
        query1 = text("""
            WITH quarantined_sample AS (
                SELECT driver_id, person_key
                FROM canon.driver_orphan_quarantine
                WHERE status = 'quarantined'
                LIMIT 20
            ),
            driver_id_matches AS (
                SELECT 
                    q.driver_id,
                    q.person_key,
                    le.id as event_id,
                    le.source_table,
                    le.source_pk,
                    le.event_date,
                    le.payload_json->>'driver_id' as event_driver_id,
                    'driver_id_direct' as match_strategy
                FROM quarantined_sample q
                INNER JOIN observational.lead_events le ON (
                    le.payload_json->>'driver_id' = q.driver_id
                    OR le.payload_json->>'driverId' = q.driver_id
                    OR le.payload_json->>'id' = q.driver_id
                )
                WHERE le.payload_json IS NOT NULL
            )
            SELECT 
                COUNT(DISTINCT driver_id) as drivers_with_driver_id_matches,
                COUNT(*) as total_driver_id_matches,
                COUNT(DISTINCT source_table) as source_tables_count
            FROM driver_id_matches
        """)
        
        result1 = db.execute(query1).fetchone()
        if result1:
            print(f"   Drivers con matches por driver_id: {result1.drivers_with_driver_id_matches}")
            print(f"   Total matches encontrados: {result1.total_driver_id_matches}")
            print(f"   Source tables distintas: {result1.source_tables_count}")
        else:
            print("   [INFO] No se encontraron matches por driver_id")
        
        # Query 2: Matches por license/phone normalizado
        print("\n2. MATCHES POR LICENSE/PHONE NORMALIZADO (scouting_daily):")
        print("-" * 80)
        
        query2 = text("""
            WITH quarantined_sample AS (
                SELECT driver_id, person_key
                FROM canon.driver_orphan_quarantine
                WHERE status = 'quarantined'
                LIMIT 20
            ),
            driver_normalized AS (
                SELECT 
                    q.driver_id,
                    q.person_key,
                    COALESCE(
                        di.license_norm,
                        UPPER(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                            COALESCE(d.license_normalized_number::text, d.license_number::text),
                            '[^A-Z0-9]', '', 'g'
                        ), ' ', '', 'g'), '-', '', 'g'))
                    ) as driver_license_norm,
                    COALESCE(
                        di.phone_norm,
                        REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                            d.phone::text,
                            '[^0-9]', '', 'g'
                        ), ' ', '', 'g'), '-', '', 'g'), '\\(', '', 'g')
                    ) as driver_phone_norm
                FROM quarantined_sample q
                LEFT JOIN canon.drivers_index di ON di.driver_id = q.driver_id
                LEFT JOIN public.drivers d ON d.driver_id::text = q.driver_id
            ),
            events_normalized AS (
                SELECT 
                    le.id as event_id,
                    le.source_table,
                    le.source_pk,
                    le.event_date,
                    UPPER(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                        le.payload_json->>'driver_license',
                        '[^A-Z0-9]', '', 'g'
                    ), ' ', '', 'g'), '-', '', 'g')) as event_license_norm,
                    REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                        le.payload_json->>'driver_phone',
                        '[^0-9]', '', 'g'
                    ), ' ', '', 'g'), '-', '', 'g'), '\\(', '', 'g') as event_phone_norm
                FROM observational.lead_events le
                WHERE le.source_table = 'module_ct_scouting_daily'
                  AND le.payload_json IS NOT NULL
                  AND (le.payload_json ? 'driver_license' OR le.payload_json ? 'driver_phone')
            ),
            license_phone_matches AS (
                SELECT 
                    dn.driver_id,
                    en.event_id,
                    en.source_table,
                    CASE 
                        WHEN dn.driver_license_norm IS NOT NULL 
                             AND en.event_license_norm IS NOT NULL 
                             AND dn.driver_license_norm = en.event_license_norm 
                             AND dn.driver_phone_norm IS NOT NULL 
                             AND en.event_phone_norm IS NOT NULL 
                             AND dn.driver_phone_norm = en.event_phone_norm THEN 'both_exact'
                        WHEN dn.driver_license_norm IS NOT NULL 
                             AND en.event_license_norm IS NOT NULL 
                             AND dn.driver_license_norm = en.event_license_norm THEN 'license_exact'
                        WHEN dn.driver_phone_norm IS NOT NULL 
                             AND en.event_phone_norm IS NOT NULL 
                             AND dn.driver_phone_norm = en.event_phone_norm THEN 'phone_exact'
                        ELSE NULL
                    END as match_strategy
                FROM driver_normalized dn
                INNER JOIN events_normalized en ON (
                    (dn.driver_license_norm IS NOT NULL 
                     AND en.event_license_norm IS NOT NULL 
                     AND dn.driver_license_norm = en.event_license_norm)
                    OR
                    (dn.driver_phone_norm IS NOT NULL 
                     AND en.event_phone_norm IS NOT NULL 
                     AND dn.driver_phone_norm = en.event_phone_norm)
                )
                WHERE dn.driver_license_norm IS NOT NULL 
                   OR dn.driver_phone_norm IS NOT NULL
            )
            SELECT 
                COUNT(DISTINCT driver_id) as drivers_with_license_phone_matches,
                COUNT(*) as total_license_phone_matches,
                COUNT(DISTINCT CASE WHEN match_strategy = 'license_exact' THEN driver_id END) as drivers_license_match,
                COUNT(DISTINCT CASE WHEN match_strategy = 'phone_exact' THEN driver_id END) as drivers_phone_match,
                COUNT(DISTINCT CASE WHEN match_strategy = 'both_exact' THEN driver_id END) as drivers_both_match
            FROM license_phone_matches
            WHERE match_strategy IS NOT NULL
        """)
        
        result2 = db.execute(query2).fetchone()
        if result2:
            print(f"   Drivers con matches por license/phone: {result2.drivers_with_license_phone_matches}")
            print(f"   Total matches encontrados: {result2.total_license_phone_matches}")
            print(f"   - Matches por license: {result2.drivers_license_match}")
            print(f"   - Matches por phone: {result2.drivers_phone_match}")
            print(f"   - Matches por ambos: {result2.drivers_both_match}")
        else:
            print("   [INFO] No se encontraron matches por license/phone")
        
        # Query 3: Muestra detallada de matches
        print("\n3. MUESTRA DETALLADA (primeros 5 drivers con matches):")
        print("-" * 80)
        
        query3 = text("""
            WITH quarantined_sample AS (
                SELECT driver_id, person_key
                FROM canon.driver_orphan_quarantine
                WHERE status = 'quarantined'
                LIMIT 5
            ),
            driver_normalized AS (
                SELECT 
                    q.driver_id,
                    COALESCE(
                        di.license_norm,
                        UPPER(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                            COALESCE(d.license_normalized_number::text, d.license_number::text),
                            '[^A-Z0-9]', '', 'g'
                        ), ' ', '', 'g'), '-', '', 'g'))
                    ) as driver_license_norm,
                    COALESCE(
                        di.phone_norm,
                        REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                            d.phone::text,
                            '[^0-9]', '', 'g'
                        ), ' ', '', 'g'), '-', '', 'g'), '\\(', '', 'g')
                    ) as driver_phone_norm
                FROM quarantined_sample q
                LEFT JOIN canon.drivers_index di ON di.driver_id = q.driver_id
                LEFT JOIN public.drivers d ON d.driver_id::text = q.driver_id
            ),
            events_normalized AS (
                SELECT 
                    le.id as event_id,
                    le.source_table,
                    le.source_pk,
                    UPPER(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                        le.payload_json->>'driver_license',
                        '[^A-Z0-9]', '', 'g'
                    ), ' ', '', 'g'), '-', '', 'g')) as event_license_norm,
                    REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(REGEXP_REPLACE(
                        le.payload_json->>'driver_phone',
                        '[^0-9]', '', 'g'
                    ), ' ', '', 'g'), '-', '', 'g'), '\\(', '', 'g') as event_phone_norm
                FROM observational.lead_events le
                WHERE le.source_table = 'module_ct_scouting_daily'
                  AND le.payload_json IS NOT NULL
                  AND (le.payload_json ? 'driver_license' OR le.payload_json ? 'driver_phone')
            ),
            matches_detail AS (
                SELECT 
                    dn.driver_id,
                    en.event_id,
                    en.source_table,
                    CASE 
                        WHEN dn.driver_license_norm = en.event_license_norm 
                             AND dn.driver_phone_norm = en.event_phone_norm THEN 'both_exact'
                        WHEN dn.driver_license_norm = en.event_license_norm THEN 'license_exact'
                        WHEN dn.driver_phone_norm = en.event_phone_norm THEN 'phone_exact'
                        ELSE NULL
                    END as match_strategy,
                    LEFT(dn.driver_license_norm, 3) || '***' || RIGHT(dn.driver_license_norm, 2) as driver_license_masked,
                    LEFT(dn.driver_phone_norm, 3) || '***' || RIGHT(dn.driver_phone_norm, 2) as driver_phone_masked
                FROM driver_normalized dn
                INNER JOIN events_normalized en ON (
                    (dn.driver_license_norm IS NOT NULL 
                     AND en.event_license_norm IS NOT NULL 
                     AND dn.driver_license_norm = en.event_license_norm)
                    OR
                    (dn.driver_phone_norm IS NOT NULL 
                     AND en.event_phone_norm IS NOT NULL 
                     AND dn.driver_phone_norm = en.event_phone_norm)
                )
                WHERE (dn.driver_license_norm IS NOT NULL OR dn.driver_phone_norm IS NOT NULL)
            )
            SELECT *
            FROM matches_detail
            WHERE match_strategy IS NOT NULL
            ORDER BY driver_id, event_id DESC
            LIMIT 10
        """)
        
        result3 = db.execute(query3).fetchall()
        if result3:
            print(f"{'Driver ID':<35} {'Event ID':<10} {'Source':<25} {'Strategy':<20} {'License':<15} {'Phone':<15}")
            print("-" * 120)
            for row in result3:
                print(f"{row.driver_id:<35} {row.event_id:<10} {row.source_table:<25} {row.match_strategy:<20} {row.driver_license_masked or 'N/A':<15} {row.driver_phone_masked or 'N/A':<15}")
        else:
            print("   [INFO] No se encontraron matches detallados")
        
        print("\n" + "="*80)
        print("CONCLUSIÓN:")
        print("="*80)
        
        total_matches = (result1.drivers_with_driver_id_matches if result1 else 0) + (result2.drivers_with_license_phone_matches if result2 else 0)
        
        if total_matches == 0:
            print("   Los drivers en cuarentena NO tienen matches con lead_events.")
            print("   Esto confirma que son drivers legacy sin respaldo de eventos.")
            print("   RECOMENDACIÓN: Mantener en cuarentena y excluir del funnel/claims.")
        else:
            print(f"   Se encontraron {total_matches} drivers en cuarentena con matches.")
            print("   RECOMENDACIÓN: Ejecutar --reprocess-quarantined para relinkear estos drivers.")
        
        print("="*80 + "\n")
        
    except Exception as e:
        logger.error(f"Error en diagnóstico: {e}", exc_info=True)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_diagnosis_sample()



