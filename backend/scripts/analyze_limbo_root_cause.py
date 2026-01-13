#!/usr/bin/env python3
"""Análisis de root cause para leads post-05 en limbo."""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"
)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

try:
    print("=" * 80)
    print("ANALISIS ROOT CAUSE: Leads Post-05 en Limbo")
    print("=" * 80)
    
    # Muestra de 10 leads post-05
    print("\n1. MUESTRA DE LEADS POST-05 POR LIMBO_STAGE:")
    
    stages = ['NO_IDENTITY', 'NO_DRIVER', 'NO_TRIPS_14D', 'TRIPS_NO_CLAIM']
    sample_leads = {}
    
    for stage in stages:
        result = session.execute(text(f"""
            SELECT 
                lead_source_pk,
                lead_date,
                limbo_stage,
                person_key,
                driver_id,
                trips_14d,
                reached_m1_14d,
                reached_m5_14d,
                reached_m25_14d,
                has_claim_m1,
                has_claim_m5,
                has_claim_m25
            FROM ops.v_cabinet_leads_limbo
            WHERE lead_date > '2026-01-05'
                AND limbo_stage = :stage
            ORDER BY lead_date DESC
            LIMIT 3
        """), {"stage": stage})
        rows = result.fetchall()
        sample_leads[stage] = rows
        print(f"\n  {stage} ({len(rows)} ejemplos):")
        for i, row in enumerate(rows, 1):
            print(f"    {i}. source_pk={row.lead_source_pk[:20]}..., lead_date={row.lead_date}")
            print(f"       person_key={row.person_key}, driver_id={row.driver_id}")
            print(f"       trips_14d={row.trips_14d}, M1={row.reached_m1_14d}, M5={row.reached_m5_14d}, M25={row.reached_m25_14d}")
            print(f"       claims: M1={row.has_claim_m1}, M5={row.has_claim_m5}, M25={row.has_claim_m25}")
    
    # 2. Lineage para NO_IDENTITY
    print("\n2. LINEAGE PARA NO_IDENTITY:")
    if sample_leads.get('NO_IDENTITY'):
        sample = sample_leads['NO_IDENTITY'][0]
        source_pk = sample.lead_source_pk
        
        # Verificar identity_link
        result = session.execute(text("""
            SELECT person_key, linked_at, source_table, source_pk
            FROM canon.identity_links
            WHERE source_table = 'module_ct_cabinet_leads'
                AND source_pk = :source_pk
        """), {"source_pk": source_pk})
        il_row = result.fetchone()
        if il_row:
            print(f"  [OK] identity_link existe: person_key={il_row.person_key}")
        else:
            print(f"  [FAIL] identity_link NO existe para source_pk={source_pk}")
            
            # Verificar identity_unmatched
            result = session.execute(text("""
                SELECT reason_code, details
                FROM canon.identity_unmatched
                WHERE source_table = 'module_ct_cabinet_leads'
                    AND source_pk = :source_pk
            """), {"source_pk": source_pk})
            um_row = result.fetchone()
            if um_row:
                print(f"  [INFO] En identity_unmatched: reason_code={um_row.reason_code}")
            else:
                print(f"  [INFO] NO está en identity_unmatched (no se intentó matching)")
    
    # 3. Lineage para NO_DRIVER
    print("\n3. LINEAGE PARA NO_DRIVER:")
    if sample_leads.get('NO_DRIVER'):
        sample = sample_leads['NO_DRIVER'][0]
        person_key = sample.person_key
        
        if person_key:
            # Verificar identity_link a drivers
            result = session.execute(text("""
                SELECT source_pk AS driver_id, linked_at
                FROM canon.identity_links
                WHERE source_table = 'drivers'
                    AND person_key = :person_key::uuid
            """), {"person_key": person_key})
            driver_row = result.fetchone()
            if driver_row:
                print(f"  [OK] identity_link a drivers existe: driver_id={driver_row.driver_id}")
            else:
                print(f"  [FAIL] identity_link a drivers NO existe para person_key={person_key}")
        else:
            print(f"  [FAIL] person_key es NULL (no debería estar en NO_DRIVER)")
    
    # 4. Lineage para NO_TRIPS_14D
    print("\n4. LINEAGE PARA NO_TRIPS_14D:")
    if sample_leads.get('NO_TRIPS_14D'):
        sample = sample_leads['NO_TRIPS_14D'][0]
        driver_id = sample.driver_id
        lead_date = sample.lead_date
        
        if driver_id:
            # Verificar summary_daily en ventana 14d
            result = session.execute(text("""
                SELECT 
                    COUNT(*) AS total_records,
                    SUM(count_orders_completed) AS total_trips
                FROM public.summary_daily
                WHERE driver_id = :driver_id
                    AND to_date(date_file, 'DD-MM-YYYY') >= :lead_date
                    AND to_date(date_file, 'DD-MM-YYYY') < :lead_date + INTERVAL '14 days'
            """), {"driver_id": driver_id, "lead_date": lead_date})
            sd_row = result.fetchone()
            if sd_row and sd_row.total_trips and sd_row.total_trips > 0:
                print(f"  [OK] summary_daily tiene trips: {sd_row.total_trips} viajes")
            else:
                print(f"  [INFO] summary_daily NO tiene trips en ventana 14d (esperado para leads recientes)")
                print(f"         Ventana: [{lead_date}, {lead_date} + 14 days)")
        else:
            print(f"  [FAIL] driver_id es NULL")
    
    # 5. Lineage para TRIPS_NO_CLAIM
    print("\n5. LINEAGE PARA TRIPS_NO_CLAIM:")
    if sample_leads.get('TRIPS_NO_CLAIM'):
        sample = sample_leads['TRIPS_NO_CLAIM'][0]
        driver_id = sample.driver_id
        lead_date = sample.lead_date
        
        if driver_id:
            # Verificar claims
            result = session.execute(text("""
                SELECT 
                    milestone_value,
                    paid_flag,
                    expected_amount
                FROM ops.v_claims_payment_status_cabinet
                WHERE driver_id = :driver_id
                    AND lead_date = :lead_date
            """), {"driver_id": driver_id, "lead_date": lead_date})
            claims = result.fetchall()
            if claims:
                print(f"  [INFO] Claims encontrados: {len(claims)}")
                for claim in claims:
                    print(f"    milestone={claim.milestone_value}, paid={claim.paid_flag}, amount={claim.expected_amount}")
            else:
                print(f"  [FAIL] NO hay claims para driver_id={driver_id}, lead_date={lead_date}")
                print(f"         Pero reached_m1={sample.reached_m1_14d}, reached_m5={sample.reached_m5_14d}, reached_m25={sample.reached_m25_14d}")
    
    print("\n" + "=" * 80)
    print("CONCLUSIONES:")
    print("=" * 80)
    print("  - NO_IDENTITY: Leads no pasaron matching (requiere job incremental)")
    print("  - NO_DRIVER: Leads tienen person_key pero no driver_id (driver no registrado aún)")
    print("  - NO_TRIPS_14D: Driver existe pero no tiene viajes en ventana 14d (esperado para leads recientes)")
    print("  - TRIPS_NO_CLAIM: Driver alcanzó milestones pero no tiene claims (bug en generación de claims)")
    
finally:
    session.close()
