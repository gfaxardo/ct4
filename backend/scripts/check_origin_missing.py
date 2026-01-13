#!/usr/bin/env python
"""
Script para verificar que ORIGIN_MISSING = 0 después del recovery.
Verifica:
1. Origins orphan = 0 (origins sin link)
2. Origin_missing para leads matched = 0 (leads matched sin origin)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from sqlalchemy import text

def check_origin_missing():
    """Verifica que ORIGIN_MISSING = 0"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("VERIFICACION: ORIGIN_MISSING = 0")
        print("=" * 80)
        print()
        
        # 1. Verificar origins orphan (sin link)
        print("1. Verificando origins orphan (sin link)...")
        orphan_query = text("""
            SELECT 
                COUNT(*) AS orphan_count
            FROM canon.identity_origin io
            WHERE io.origin_tag = 'cabinet_lead'
                AND NOT EXISTS (
                    SELECT 1
                    FROM canon.identity_links il
                    WHERE il.source_table = 'module_ct_cabinet_leads'
                        AND il.source_pk = io.origin_source_id
                        AND il.person_key = io.person_key
                )
        """)
        orphan_result = db.execute(orphan_query)
        orphan_count = orphan_result.scalar() or 0
        
        print(f"   Origins orphan (sin link): {orphan_count}")
        print()
        
        # 2. Verificar leads matched sin origin
        print("2. Verificando leads matched sin origin...")
        matched_no_origin_query = text("""
            SELECT 
                COUNT(*) AS matched_no_origin_count
            FROM ops.cabinet_kpi_red_recovery_queue q
            INNER JOIN canon.identity_links il
                ON il.source_table = 'module_ct_cabinet_leads'
                AND il.source_pk = q.lead_source_pk
                AND il.person_key = q.matched_person_key
            WHERE q.status = 'matched'
                AND NOT EXISTS (
                    SELECT 1
                    FROM canon.identity_origin io
                    WHERE io.person_key = q.matched_person_key
                        AND io.origin_tag = 'cabinet_lead'
                        AND io.origin_source_id = q.lead_source_pk
                )
        """)
        matched_no_origin_result = db.execute(matched_no_origin_query)
        matched_no_origin_count = matched_no_origin_result.scalar() or 0
        
        print(f"   Leads matched sin origin: {matched_no_origin_count}")
        print()
        
        # 3. Resumen
        print("=" * 80)
        print("RESUMEN")
        print("=" * 80)
        print(f"Origins orphan (sin link): {orphan_count}")
        print(f"Leads matched sin origin: {matched_no_origin_count}")
        print()
        
        if orphan_count == 0 and matched_no_origin_count == 0:
            print("[OK] EXITO: ORIGIN_MISSING = 0")
            print("   - Origins orphan: 0")
            print("   - Leads matched sin origin: 0")
            return {"status": "success", "orphan_count": 0, "matched_no_origin_count": 0}
        else:
            print("[ERROR] FALLO: ORIGIN_MISSING > 0")
            print(f"   - Origins orphan: {orphan_count}")
            print(f"   - Leads matched sin origin: {matched_no_origin_count}")
            return {"status": "failure", "orphan_count": orphan_count, "matched_no_origin_count": matched_no_origin_count}
    
    except Exception as e:
        print(f"[ERROR] ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    result = check_origin_missing()
    if result["status"] == "failure":
        sys.exit(1)
