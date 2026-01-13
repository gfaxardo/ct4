"""Script para crear identity_origin faltantes para identity_links existentes"""
import sys
from pathlib import Path
from datetime import datetime
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal
from sqlalchemy import text

DEFAULT_CONFIDENCE = 95.0

def backfill_origins():
    """Crea identity_origin para identity_links que no lo tienen"""
    db = SessionLocal()
    try:
        # Encontrar links sin origin
        query = text("""
            SELECT il.source_pk, il.person_key, il.snapshot_date
            FROM canon.identity_links il 
            WHERE il.source_table = 'module_ct_cabinet_leads' 
              AND NOT EXISTS (
                  SELECT 1 
                  FROM canon.identity_origin io 
                  WHERE io.person_key = il.person_key 
                    AND io.origin_tag = 'cabinet_lead' 
                    AND io.origin_source_id = il.source_pk
              )
        """)
        
        result = db.execute(query)
        links = result.fetchall()
        
        print(f"Encontrados {len(links)} identity_links sin origin")
        
        if len(links) == 0:
            print("No hay links sin origin. Todo OK.")
            return
        
        # Crear origins
        created = 0
        errors = 0
        
        for link in links:
            try:
                origin_created_at = link.snapshot_date or datetime.utcnow()
                
                db.execute(text("""
                    INSERT INTO canon.identity_origin 
                    (person_key, origin_tag, origin_source_id, origin_confidence, origin_created_at, decided_by, resolution_status)
                    VALUES (:person_key, 'cabinet_lead', :origin_source_id, :origin_confidence, :origin_created_at, 'system', 'resolved_auto')
                    ON CONFLICT (person_key) DO UPDATE
                    SET origin_tag = 'cabinet_lead',
                        origin_source_id = :origin_source_id,
                        resolution_status = 'resolved_auto',
                        updated_at = NOW()
                """), {
                    "person_key": str(link.person_key),
                    "origin_source_id": link.source_pk,
                    "origin_confidence": DEFAULT_CONFIDENCE,
                    "origin_created_at": origin_created_at
                })
                created += 1
            except Exception as e:
                print(f"Error creando origin para lead {link.source_pk}: {e}")
                errors += 1
        
        db.commit()
        print(f"\nCompletado: {created} origins creados, {errors} errores")
        
    except Exception as e:
        db.rollback()
        print(f"Error en backfill: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    backfill_origins()
