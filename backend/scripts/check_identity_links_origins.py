"""Script rápido para verificar identity_links sin origin"""
import sys
from pathlib import Path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.db import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
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
    count = result.scalar()
    print(f"Identity links sin origin correspondiente: {count}")
    
    # Muestra algunos ejemplos
    if count > 0:
        result = db.execute(text("""
            SELECT il.source_pk, il.person_key, il.linked_at
            FROM canon.identity_links il 
            WHERE il.source_table = 'module_ct_cabinet_leads' 
              AND NOT EXISTS (
                  SELECT 1 
                  FROM canon.identity_origin io 
                  WHERE io.person_key = il.person_key 
                    AND io.origin_tag = 'cabinet_lead' 
                    AND io.origin_source_id = il.source_pk
              )
            LIMIT 5
        """))
        print("\nEjemplos (primeros 5):")
        for row in result:
            print(f"  Lead: {row.source_pk}, Person: {row.person_key}, Linked: {row.linked_at}")
finally:
    db.close()
