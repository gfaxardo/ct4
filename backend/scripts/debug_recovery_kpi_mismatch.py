#!/usr/bin/env python
"""
Script de diagnóstico para detectar el root cause del mismatch entre
"Matched last 24h" (93) y "KPI rojo" (203).

FASE B - PRUEBA CONTROLADA
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from sqlalchemy import text
from datetime import datetime, timedelta

def debug_recovery_kpi_mismatch():
    """
    Analiza 20 leads "matched last 24h" y verifica por qué no bajan el KPI rojo.
    """
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("FASE B - PRUEBA CONTROLADA")
        print("=" * 80)
        print()
        
        # B1) Seleccionar 20 leads matched last 24h desde ops.identity_matching_jobs
        print("B1) Seleccionando 20 leads matched last 24h desde ops.identity_matching_jobs...")
        matched_query = text("""
            SELECT 
                source_id AS lead_id,
                matched_person_key,
                last_attempt_at,
                status
            FROM ops.identity_matching_jobs
            WHERE status = 'matched'
                AND last_attempt_at >= NOW() - INTERVAL '24 hours'
            ORDER BY last_attempt_at DESC
            LIMIT 20
        """)
        
        matched_result = db.execute(matched_query)
        matched_leads = matched_result.fetchall()
        
        if len(matched_leads) == 0:
            print("ERROR: No se encontraron leads matched last 24h")
            return
        
        print(f"Encontrados {len(matched_leads)} leads matched last 24h")
        print()
        
        # B2) Para cada lead, verificar las 5 preguntas
        debug_rows = []
        
        for matched_lead in matched_leads:
            lead_id = matched_lead.lead_id
            matched_person_key = matched_lead.matched_person_key
            
            print(f"Analizando lead_id: {lead_id}")
            
            # 1) ¿Existe vínculo canónico lead_id -> person_key en canon.identity_links?
            link_query = text("""
                SELECT 
                    source_table,
                    source_pk,
                    person_key
                FROM canon.identity_links
                WHERE source_table = 'module_ct_cabinet_leads'
                    AND source_pk = :lead_id
            """)
            link_result = db.execute(link_query, {"lead_id": lead_id})
            link_row = link_result.fetchone()
            
            link_exists = link_row is not None
            link_source_table = link_row.source_table if link_row else None
            link_source_pk = link_row.source_pk if link_row else None
            link_person_key = link_row.person_key if link_row else None
            
            # 2) ¿El source_table usado coincide EXACTO?
            source_table_match = (link_source_table == 'module_ct_cabinet_leads') if link_exists else False
            
            # 3) ¿El source_pk usado coincide EXACTO? (verificar formato del lead_id real)
            # Obtener lead_id real desde module_ct_cabinet_leads
            real_lead_id_query = text("""
                SELECT 
                    COALESCE(external_id::text, id::text) AS unified_lead_id,
                    external_id,
                    id
                FROM public.module_ct_cabinet_leads
                WHERE COALESCE(external_id::text, id::text) = :lead_id
                LIMIT 1
            """)
            real_lead_result = db.execute(real_lead_id_query, {"lead_id": lead_id})
            real_lead_row = real_lead_result.fetchone()
            
            real_unified_lead_id = real_lead_row.unified_lead_id if real_lead_row else None
            source_pk_match = (link_source_pk == real_unified_lead_id) if link_exists else False
            
            # 4) ¿Existe canon.identity_origin?
            origin_query = text("""
                SELECT 
                    person_key,
                    origin_tag,
                    origin_source_id
                FROM canon.identity_origin
                WHERE person_key = :person_key
                    AND origin_tag = 'cabinet_lead'
                    AND origin_source_id = :lead_id
                LIMIT 1
            """)
            origin_result = db.execute(origin_query, {
                "person_key": matched_person_key,
                "lead_id": lead_id
            })
            origin_row = origin_result.fetchone()
            origin_ok = origin_row is not None
            
            # 5) ¿El KPI rojo los sigue contando como "sin identidad"?
            # Aplicar la misma definición exacta del KPI rojo
            kpi_query = text("""
                SELECT COUNT(*) as count
                FROM public.module_ct_cabinet_leads mcl
                WHERE COALESCE(mcl.external_id::text, mcl.id::text) = :lead_id
                    AND NOT EXISTS (
                        SELECT 1
                        FROM canon.identity_links il
                        WHERE il.source_table = 'module_ct_cabinet_leads'
                            AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
                    )
            """)
            kpi_result = db.execute(kpi_query, {"lead_id": lead_id})
            kpi_count = kpi_result.scalar()
            counted_in_kpi_red = (kpi_count > 0)
            
            # Determinar root cause
            root_cause = 'OTHER'
            if not link_exists:
                root_cause = 'NO_LINK_WRITTEN'
            elif not source_table_match:
                root_cause = 'WRONG_SOURCE_TABLE'
            elif not source_pk_match:
                root_cause = 'WRONG_SOURCE_PK'
            elif not origin_ok:
                root_cause = 'ORIGIN_MISSING'
            elif counted_in_kpi_red:
                root_cause = 'KPI_READING_DIFFERENT_VIEW'  # Link existe pero KPI no lo ve
            else:
                root_cause = 'NO_ISSUE'  # Todo OK
            
            debug_rows.append({
                'lead_id': lead_id,
                'matched_person_key': str(matched_person_key) if matched_person_key else None,
                'real_unified_lead_id': real_unified_lead_id,
                'link_exists': link_exists,
                'link_source_table': link_source_table,
                'link_source_pk': link_source_pk,
                'link_person_key': str(link_person_key) if link_person_key else None,
                'source_table_match': source_table_match,
                'source_pk_match': source_pk_match,
                'origin_ok': origin_ok,
                'counted_in_kpi_red': counted_in_kpi_red,
                'root_cause': root_cause
            })
            
            print(f"  link_exists: {link_exists}")
            print(f"  link_source_table: {link_source_table}")
            print(f"  link_source_pk: {link_source_pk}")
            print(f"  real_unified_lead_id: {real_unified_lead_id}")
            print(f"  source_pk_match: {source_pk_match}")
            print(f"  origin_ok: {origin_ok}")
            print(f"  counted_in_kpi_red: {counted_in_kpi_red}")
            print(f"  root_cause: {root_cause}")
            print()
        
        # B3) Resumen y criterio
        print("=" * 80)
        print("B3) RESUMEN")
        print("=" * 80)
        
        bugs = [r for r in debug_rows if r['counted_in_kpi_red']]
        print(f"Leads con bug (matched pero counted_in_kpi_red=true): {len(bugs)}/{len(debug_rows)}")
        print()
        
        if len(bugs) > 0:
            print("ROOT CAUSE DETECTADO:")
            root_causes = {}
            for row in bugs:
                rc = row['root_cause']
                root_causes[rc] = root_causes.get(rc, 0) + 1
            
            for rc, count in root_causes.items():
                print(f"  {rc}: {count} leads")
            print()
            
            print("EJEMPLOS DE LEADS CON BUG:")
            for i, row in enumerate(bugs[:5], 1):
                print(f"{i}. lead_id={row['lead_id']}")
                print(f"   root_cause={row['root_cause']}")
                print(f"   link_exists={row['link_exists']}")
                print(f"   link_source_pk={row['link_source_pk']}")
                print(f"   real_unified_lead_id={row['real_unified_lead_id']}")
                print()
        
        # Guardar tabla debug completa
        print("=" * 80)
        print("TABLA DEBUG COMPLETA")
        print("=" * 80)
        print(f"{'lead_id':<30} {'link_exists':<12} {'source_table_match':<18} {'source_pk_match':<16} {'counted_in_kpi_red':<20} {'root_cause':<25}")
        print("-" * 120)
        for row in debug_rows:
            print(f"{row['lead_id']:<30} {str(row['link_exists']):<12} {str(row['source_table_match']):<18} {str(row['source_pk_match']):<16} {str(row['counted_in_kpi_red']):<20} {row['root_cause']:<25}")
        
        return debug_rows
        
    finally:
        db.close()

if __name__ == "__main__":
    debug_recovery_kpi_mismatch()
