import sys
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings

def main():
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        print("=" * 80)
        print("VERIFICACIÓN 1: Conteo por attribution_confidence")
        print("=" * 80)
        print("\nQuery:")
        print("SELECT attribution_confidence, COUNT(*) FROM ops.v_attribution_canonical GROUP BY 1 ORDER BY 2 DESC;")
        print("\nResultado:")
        print("-" * 80)
        
        query1 = text("""
            SELECT 
                attribution_confidence, 
                COUNT(*) 
            FROM ops.v_attribution_canonical 
            GROUP BY attribution_confidence 
            ORDER BY COUNT(*) DESC
        """)
        
        result1 = session.execute(query1)
        for row in result1:
            print(f"  {row.attribution_confidence:20s} | {row.count:10,}")
        
        print("\n" + "=" * 80)
        print("VERIFICACIÓN 2: Conteo por lead_origin y attribution_confidence")
        print("=" * 80)
        print("\nQuery:")
        print("SELECT lead_origin, attribution_confidence, COUNT(*) FROM ops.v_attribution_canonical GROUP BY 1,2 ORDER BY 1,2;")
        print("\nResultado:")
        print("-" * 80)
        
        query2 = text("""
            SELECT 
                lead_origin,
                attribution_confidence, 
                COUNT(*) 
            FROM ops.v_attribution_canonical 
            GROUP BY lead_origin, attribution_confidence 
            ORDER BY lead_origin, attribution_confidence
        """)
        
        result2 = session.execute(query2)
        print("  lead_origin      | attribution_confidence | count")
        print("  " + "-" * 70)
        for row in result2:
            print(f"  {row.lead_origin:15s} | {row.attribution_confidence:22s} | {row.count:10,}")
        
        print("\n" + "=" * 80)
        print("VERIFICACIÓN 3: Muestra de medium/unknown (primeras 20 filas)")
        print("=" * 80)
        print("\nQuery:")
        print("SELECT * FROM ops.v_attribution_canonical WHERE attribution_confidence IN ('medium','unknown') ORDER BY person_key LIMIT 20;")
        print("\nResultado:")
        print("-" * 80)
        
        query3 = text("""
            SELECT 
                person_key,
                lead_origin,
                acquisition_scout_id,
                acquisition_scout_name,
                attribution_confidence,
                attribution_rule,
                attribution_evidence
            FROM ops.v_attribution_canonical 
            WHERE attribution_confidence IN ('medium', 'unknown')
            ORDER BY person_key 
            LIMIT 20
        """)
        
        result3 = session.execute(query3)
        rows3 = result3.fetchall()
        
        if rows3:
            print("\n  person_key                             | lead_origin | scout_id | scout_name                    | confidence | rule              | evidence")
            print("  " + "-" * 150)
            for row in rows3:
                scout_id_str = str(row.acquisition_scout_id) if row.acquisition_scout_id else "NULL"
                scout_name_str = (row.acquisition_scout_name or "NULL")[:30]
                evidence_str = str(row.attribution_evidence)[:30] if row.attribution_evidence else "{}"
                print(f"  {str(row.person_key):36s} | {row.lead_origin:11s} | {scout_id_str:8s} | {scout_name_str:30s} | {row.attribution_confidence:10s} | {row.attribution_rule:18s} | {evidence_str}")
        else:
            print("\n  No hay registros con confidence medium o unknown")
        
        print("\n" + "=" * 80)
        print("[OK] TODAS LAS VERIFICACIONES COMPLETADAS")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()




















