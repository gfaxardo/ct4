#!/usr/bin/env python
"""
Guardrail obligatorio: Verifica que leads matched NO están en el backlog.
Si algún lead matched aparece en el backlog, el sistema está fallando.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from sqlalchemy import text

def verify_kpi_red_drain(n: int = 100):
    """
    Valida que N leads matched NO están en el backlog.
    
    Args:
        n: Número de leads matched a verificar (default: 100)
    
    Returns:
        dict con resultado de la verificación
    
    Exits:
        exit(1) si algún lead matched está en el backlog
    """
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("GUARDRAIL: Verificación de Drenaje del KPI Rojo")
        print("=" * 80)
        print()
        
        # 1. Obtener N leads matched de la queue
        print(f"1. Obteniendo {n} leads matched de la queue...")
        matched_query = text("""
            SELECT 
                lead_source_pk,
                matched_person_key,
                updated_at
            FROM ops.cabinet_kpi_red_recovery_queue
            WHERE status = 'matched'
            ORDER BY updated_at DESC
            LIMIT :n
        """)
        matched_result = db.execute(matched_query, {"n": n})
        matched_leads = [dict(row._mapping) if hasattr(row, '_mapping') else dict(row) for row in matched_result.fetchall()]
        
        if len(matched_leads) == 0:
            print("   ⚠️  ADVERTENCIA: No se encontraron leads matched en la queue")
            print("   Esto puede ser normal si el job aún no se ha ejecutado.")
            return {"status": "warning", "message": "No matched leads found"}
        
        print(f"   Encontrados {len(matched_leads)} leads matched")
        print()
        
        # 2. Verificar si están en el backlog
        print(f"2. Verificando si están en el backlog...")
        lead_source_pks = [lead['lead_source_pk'] for lead in matched_leads]
        
        backlog_query = text("""
            SELECT lead_source_pk
            FROM ops.v_cabinet_kpi_red_backlog
            WHERE lead_source_pk = ANY(:lead_source_pks)
        """)
        backlog_result = db.execute(backlog_query, {"lead_source_pks": lead_source_pks})
        backlog_leads = [row.lead_source_pk for row in backlog_result.fetchall()]
        
        print(f"   Leads matched: {len(matched_leads)}")
        print(f"   Leads en backlog: {len(backlog_leads)}")
        print()
        
        # 3. Verificar identidad exacta
        print("3. Verificando identidad exacta de source_pk...")
        for lead in matched_leads[:5]:  # Mostrar primeros 5
            lead_source_pk = lead['lead_source_pk']
            in_backlog = lead_source_pk in backlog_leads
            
            # Verificar identity_link
            link_query = text("""
                SELECT source_pk, person_key
                FROM canon.identity_links
                WHERE source_table = 'module_ct_cabinet_leads'
                    AND source_pk = :lead_source_pk
                LIMIT 1
            """)
            link_result = db.execute(link_query, {"lead_source_pk": lead_source_pk})
            link_row = link_result.fetchone()
            has_link = link_row is not None
            
            print(f"   lead_source_pk={lead_source_pk[:30]}...")
            print(f"     matched_person_key={lead.get('matched_person_key')}")
            print(f"     has_identity_link={has_link}")
            print(f"     in_backlog={in_backlog}")
            if in_backlog:
                    print(f"     [ERROR] ERROR: Este lead matched ESTA en el backlog!")
            print()
        
        # 4. Evaluar resultado
        if len(backlog_leads) > 0:
            print("=" * 80)
            print("[ERROR] FALLO: Algunos leads matched ESTAN en el backlog")
            print("=" * 80)
            print(f"Leads matched verificados: {len(matched_leads)}")
            print(f"Leads matched que están en backlog: {len(backlog_leads)}")
            print()
            print("Leads con problema:")
            for lead_source_pk in backlog_leads:
                print(f"  - {lead_source_pk}")
                # Verificar identity_link
                link_query = text("""
                    SELECT source_pk, person_key
                    FROM canon.identity_links
                    WHERE source_table = 'module_ct_cabinet_leads'
                        AND source_pk = :lead_source_pk
                    LIMIT 1
                """)
                link_result = db.execute(link_query, {"lead_source_pk": lead_source_pk})
                link_row = link_result.fetchone()
                if link_row:
                    print(f"    → Tiene identity_link: {link_row.person_key}")
                else:
                    print(f"    → NO tiene identity_link (BUG CRÍTICO)")
            print()
            print("POSIBLES CAUSAS:")
            print("  1. source_pk mismatch (casting diferente)")
            print("  2. identity_link no se creó correctamente")
            print("  3. Vista del backlog no está sincronizada")
            print("  4. Race condition (lead matched después de snapshot del backlog)")
            print()
            sys.exit(1)
        else:
            print("=" * 80)
            print("[OK] EXITO: 0% de leads matched estan en el backlog")
            print("=" * 80)
            print(f"Leads matched verificados: {len(matched_leads)}")
            print(f"Leads en backlog: {len(backlog_leads)}")
            print(f"Tasa de error: 0%")
            print()
            return {
                "status": "success",
                "matched_count": len(matched_leads),
                "backlog_count": len(backlog_leads),
                "error_rate": 0.0
            }
    
    except Exception as e:
        print(f"[ERROR] ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    n = 100
    if len(sys.argv) > 1:
        try:
            n = int(sys.argv[1])
        except ValueError:
            pass
    
    result = verify_kpi_red_drain(n=n)
