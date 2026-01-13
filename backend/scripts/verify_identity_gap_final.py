"""Script de verificación final del Identity Gap Killer v2"""
import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal
from sqlalchemy import text

def verify_final_state():
    db = SessionLocal()
    try:
        print("=" * 80)
        print("VERIFICACIÓN FINAL: Identity Gap Killer v2")
        print("=" * 80)
        
        # 1. Estado del gap
        result = db.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE gap_reason = 'resolved') as resolved,
                COUNT(*) FILTER (WHERE gap_reason != 'resolved') as unresolved,
                ROUND(100.0 * COUNT(*) FILTER (WHERE gap_reason != 'resolved') / NULLIF(COUNT(*), 0), 2) as pct_unresolved
            FROM ops.v_identity_gap_analysis
        """))
        row = result.fetchone()
        print(f"\n1. ESTADO DEL GAP:")
        print(f"   Total Leads: {row.total}")
        print(f"   Resolved: {row.resolved} ({100 - row.pct_unresolved:.2f}%)")
        print(f"   Unresolved: {row.unresolved} ({row.pct_unresolved:.2f}%)")
        
        # 2. Breakdown por gap_reason
        result = db.execute(text("""
            SELECT gap_reason, risk_level, COUNT(*) as count
            FROM ops.v_identity_gap_analysis
            GROUP BY gap_reason, risk_level
            ORDER BY count DESC
        """))
        print(f"\n2. BREAKDOWN POR GAP_REASON:")
        for row in result:
            print(f"   {row.gap_reason:20} | {row.risk_level:6} | {row.count:6}")
        
        # 3. Job stats
        result = db.execute(text("""
            SELECT 
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE status = 'matched') as matched,
                COUNT(*) FILTER (WHERE status = 'failed') as failed,
                COUNT(*) FILTER (WHERE status = 'pending') as pending,
                MAX(last_attempt_at) as last_run
            FROM ops.identity_matching_jobs
        """))
        row = result.fetchone()
        print(f"\n3. ESTADO DEL JOB:")
        print(f"   Total Jobs: {row.total}")
        print(f"   Matched: {row.matched}")
        print(f"   Failed: {row.failed}")
        print(f"   Pending: {row.pending}")
        print(f"   Last Run: {row.last_run}")
        
        # 4. Identity links y origins
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM canon.identity_links 
            WHERE source_table = 'module_ct_cabinet_leads'
        """))
        links_count = result.scalar()
        
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM canon.identity_origin 
            WHERE origin_tag = 'cabinet_lead'
        """))
        origins_count = result.scalar()
        
        print(f"\n4. VÍNCULOS CREADOS:")
        print(f"   Identity Links: {links_count}")
        print(f"   Identity Origins: {origins_count}")
        
        # 5. Links sin origin
        result = db.execute(text("""
            SELECT COUNT(*) 
            FROM canon.identity_links il 
            WHERE il.source_table = 'module_ct_cabinet_leads' 
              AND NOT EXISTS (
                  SELECT 1 
                  FROM canon.identity_origin io 
                  WHERE io.person_key = il.person_key 
                    AND io.origin_tag = 'cabinet_lead' 
                    AND io.origin_source_id = il.source_pk
              )
        """))
        links_without_origin = result.scalar()
        print(f"   Links sin Origin: {links_without_origin}")
        
        print("\n" + "=" * 80)
        print("VERIFICACIÓN COMPLETA")
        print("=" * 80)
        
    except Exception as e:
        print(f"Error en verificación: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    verify_final_state()
