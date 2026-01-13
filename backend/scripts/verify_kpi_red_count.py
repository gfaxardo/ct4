#!/usr/bin/env python
"""
Verifica el conteo del KPI rojo directamente.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from sqlalchemy import text

def verify_kpi_red():
    db = SessionLocal()
    
    try:
        # Query exacta del KPI rojo
        sql = text("""
            WITH leads_with_identity AS (
                SELECT DISTINCT
                    COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk
                FROM public.module_ct_cabinet_leads mcl
                INNER JOIN canon.identity_links il
                    ON il.source_table = 'module_ct_cabinet_leads'
                    AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
            ),
            leads_with_claims AS (
                SELECT DISTINCT
                    COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk
                FROM public.module_ct_cabinet_leads mcl
                INNER JOIN canon.identity_links il
                    ON il.source_table = 'module_ct_cabinet_leads'
                    AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
                INNER JOIN ops.v_claims_payment_status_cabinet c
                    ON c.person_key = il.person_key
                    AND c.driver_id IS NOT NULL
            )
            SELECT 
                COUNT(*) AS total_leads,
                COUNT(DISTINCT li.lead_source_pk) AS leads_with_identity,
                COUNT(DISTINCT lc.lead_source_pk) AS leads_with_claims,
                COUNT(*) - COUNT(DISTINCT li.lead_source_pk) AS leads_without_identity,
                COUNT(*) - COUNT(DISTINCT lc.lead_source_pk) AS leads_without_claims,
                COUNT(*) - COUNT(DISTINCT COALESCE(li.lead_source_pk, lc.lead_source_pk)) AS leads_without_both
            FROM public.module_ct_cabinet_leads mcl
            LEFT JOIN leads_with_identity li
                ON li.lead_source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
            LEFT JOIN leads_with_claims lc
                ON lc.lead_source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
        """)
        
        result = db.execute(sql)
        row = result.fetchone()
        
        print("=" * 80)
        print("KPI ROJO - CONTEOS ACTUALES")
        print("=" * 80)
        print(f"Total leads: {row.total_leads}")
        print(f"Leads con identidad: {row.leads_with_identity}")
        print(f"Leads sin identidad: {row.leads_without_identity}")
        print(f"Leads con claims: {row.leads_with_claims}")
        print(f"Leads sin claims: {row.leads_without_claims}")
        print(f"Leads sin identidad NI claims (KPI ROJO): {row.leads_without_both}")
        print()
        
        # Verificar matched last 24h
        matched_query = text("""
            SELECT COUNT(*) as matched_last_24h
            FROM ops.identity_matching_jobs
            WHERE status = 'matched'
                AND last_attempt_at >= NOW() - INTERVAL '24 hours'
        """)
        matched_result = db.execute(matched_query)
        matched_row = matched_result.fetchone()
        print(f"Matched last 24h: {matched_row.matched_last_24h}")
        print()
        
        # Verificar si los matched last 24h tienen links
        matched_with_links_query = text("""
            SELECT COUNT(DISTINCT imj.source_id) as matched_with_links
            FROM ops.identity_matching_jobs imj
            INNER JOIN canon.identity_links il
                ON il.source_table = 'module_ct_cabinet_leads'
                AND il.source_pk = imj.source_id
            WHERE imj.status = 'matched'
                AND imj.last_attempt_at >= NOW() - INTERVAL '24 hours'
        """)
        matched_with_links_result = db.execute(matched_with_links_query)
        matched_with_links_row = matched_with_links_result.fetchone()
        print(f"Matched last 24h con links: {matched_with_links_row.matched_with_links}")
        print()
        
        # Verificar si los matched last 24h están en el KPI rojo
        matched_in_kpi_red_query = text("""
            WITH matched_last_24h AS (
                SELECT DISTINCT source_id AS lead_id
                FROM ops.identity_matching_jobs
                WHERE status = 'matched'
                    AND last_attempt_at >= NOW() - INTERVAL '24 hours'
            ),
            leads_without_both AS (
                SELECT DISTINCT
                    COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk
                FROM public.module_ct_cabinet_leads mcl
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM canon.identity_links il
                    WHERE il.source_table = 'module_ct_cabinet_leads'
                        AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
                )
                AND NOT EXISTS (
                    SELECT 1
                    FROM canon.identity_links il
                    INNER JOIN ops.v_claims_payment_status_cabinet c
                        ON c.person_key = il.person_key
                        AND c.driver_id IS NOT NULL
                    WHERE il.source_table = 'module_ct_cabinet_leads'
                        AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
                )
            )
            SELECT COUNT(*) as matched_in_kpi_red
            FROM matched_last_24h m
            INNER JOIN leads_without_both lwb
                ON lwb.lead_source_pk = m.lead_id
        """)
        matched_in_kpi_red_result = db.execute(matched_in_kpi_red_query)
        matched_in_kpi_red_row = matched_in_kpi_red_result.fetchone()
        print(f"Matched last 24h que están en KPI rojo: {matched_in_kpi_red_row.matched_in_kpi_red}")
        print()
        
    finally:
        db.close()

if __name__ == "__main__":
    verify_kpi_red()
