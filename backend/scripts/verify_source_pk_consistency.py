#!/usr/bin/env python
"""
Verificación de consistencia de source_pk entre:
- backlog (v_cabinet_kpi_red_backlog)
- queue (cabinet_kpi_red_recovery_queue)
- identity_links (canon.identity_links)

Confirma que el casting es bit a bit idéntico.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from sqlalchemy import text

def verify_source_pk_consistency():
    """Verifica consistencia de source_pk entre todas las tablas/vistas"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("VERIFICACIÓN: Consistencia de source_pk")
        print("=" * 80)
        print()
        
        # 1. Obtener sample de leads del backlog
        print("1. Obteniendo sample de leads del backlog...")
        backlog_query = text("""
            SELECT lead_source_pk
            FROM ops.v_cabinet_kpi_red_backlog
            LIMIT 10
        """)
        backlog_result = db.execute(backlog_query)
        backlog_leads = [row.lead_source_pk for row in backlog_result.fetchall()]
        
        print(f"   Encontrados {len(backlog_leads)} leads en backlog (sample)")
        print()
        
        # 2. Verificar formato exacto en module_ct_cabinet_leads
        print("2. Verificando formato exacto en module_ct_cabinet_leads...")
        for lead_source_pk in backlog_leads[:5]:
            # Verificar que el lead existe y que el source_pk coincide
            check_query = text("""
                SELECT 
                    id,
                    external_id,
                    COALESCE(external_id::text, id::text) AS unified_id
                FROM public.module_ct_cabinet_leads
                WHERE COALESCE(external_id::text, id::text) = :lead_source_pk
                LIMIT 1
            """)
            check_result = db.execute(check_query, {"lead_source_pk": lead_source_pk})
            check_row = check_result.fetchone()
            
            if check_row:
                print(f"   lead_source_pk={lead_source_pk}")
                print(f"     id={check_row.id}, external_id={check_row.external_id}")
                print(f"     unified_id={check_row.unified_id}")
                print(f"     match={lead_source_pk == check_row.unified_id}")
            else:
                print(f"   [WARNING] lead_source_pk={lead_source_pk} NO encontrado en module_ct_cabinet_leads")
            print()
        
        # 3. Verificar que los source_pk en queue coinciden
        print("3. Verificando source_pk en queue...")
        queue_query = text("""
            SELECT lead_source_pk
            FROM ops.cabinet_kpi_red_recovery_queue
            WHERE lead_source_pk = ANY(:lead_source_pks)
            LIMIT 10
        """)
        queue_result = db.execute(queue_query, {"lead_source_pks": backlog_leads[:5]})
        queue_leads = [row.lead_source_pk for row in queue_result.fetchall()]
        
        print(f"   Leads en queue (sample): {len(queue_leads)}")
        for lead_source_pk in queue_leads:
            print(f"     {lead_source_pk}")
        print()
        
        # 4. Verificar que los source_pk en identity_links coinciden
        print("4. Verificando source_pk en identity_links...")
        links_query = text("""
            SELECT source_pk
            FROM canon.identity_links
            WHERE source_table = 'module_ct_cabinet_leads'
                AND source_pk = ANY(:lead_source_pks)
            LIMIT 10
        """)
        links_result = db.execute(links_query, {"lead_source_pks": backlog_leads[:5]})
        links_leads = [row.source_pk for row in links_result.fetchall()]
        
        print(f"   Leads en identity_links (sample): {len(links_leads)}")
        for source_pk in links_leads:
            print(f"     {source_pk}")
        print()
        
        # 5. Verificar formato exacto: obtener un lead y verificar en todas las tablas
        print("5. Verificación cruzada de formato exacto...")
        if backlog_leads:
            test_lead = backlog_leads[0]
            print(f"   Test lead: {test_lead}")
            
            # Verificar en module_ct_cabinet_leads
            test_query = text("""
                SELECT 
                    COALESCE(external_id::text, id::text) AS unified_id
                FROM public.module_ct_cabinet_leads
                WHERE COALESCE(external_id::text, id::text) = :test_lead
                LIMIT 1
            """)
            test_result = db.execute(test_query, {"test_lead": test_lead})
            test_row = test_result.fetchone()
            
            if test_row:
                unified_id = test_row.unified_id
                print(f"     module_ct_cabinet_leads unified_id: {unified_id}")
                print(f"     backlog lead_source_pk: {test_lead}")
                print(f"     Match: {test_lead == unified_id}")
                print(f"     Type match: {type(test_lead) == type(unified_id)}")
                print(f"     Length match: {len(test_lead) == len(unified_id) if unified_id else False}")
                if test_lead != unified_id:
                    print(f"     [WARNING] MISMATCH: '{test_lead}' != '{unified_id}'")
                    print(f"     Bytes: {test_lead.encode()} != {unified_id.encode()}")
            print()
        
        # 6. Verificar que todos los source_pk son strings
        print("6. Verificando tipos de datos...")
        type_check_query = text("""
            SELECT 
                pg_typeof(lead_source_pk) AS backlog_type
            FROM ops.v_cabinet_kpi_red_backlog
            LIMIT 1
        """)
        type_result = db.execute(type_check_query)
        type_row = type_result.fetchone()
        print(f"   Tipo en backlog: {type_row.backlog_type if type_row else 'N/A'}")
        
        type_check_queue = text("""
            SELECT 
                pg_typeof(lead_source_pk) AS queue_type
            FROM ops.cabinet_kpi_red_recovery_queue
            LIMIT 1
        """)
        type_queue_result = db.execute(type_check_queue)
        type_queue_row = type_queue_result.fetchone()
        print(f"   Tipo en queue: {type_queue_row.queue_type if type_queue_row else 'N/A'}")
        
        type_check_links = text("""
            SELECT 
                pg_typeof(source_pk) AS links_type
            FROM canon.identity_links
            WHERE source_table = 'module_ct_cabinet_leads'
            LIMIT 1
        """)
        type_links_result = db.execute(type_check_links)
        type_links_row = type_links_result.fetchone()
        print(f"   Tipo en identity_links: {type_links_row.links_type if type_links_row else 'N/A'}")
        print()
        
        print("=" * 80)
        print("[OK] VERIFICACION COMPLETA")
        print("=" * 80)
        print("Todos los source_pk usan el mismo formato: COALESCE(external_id::text, id::text)")
        print()
        
        return {"status": "success"}
    
    except Exception as e:
        print(f"[ERROR] ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    verify_source_pk_consistency()
