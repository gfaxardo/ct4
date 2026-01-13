#!/usr/bin/env python
"""
Verificación: canon.identity_origin se crea SOLO cuando hay link válido.
NO debe haber identity_origin sin identity_link correspondiente.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from sqlalchemy import text

def verify_identity_origin_creation():
    """Verifica que identity_origin se crea solo cuando hay link válido"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("VERIFICACIÓN: Creación de identity_origin")
        print("=" * 80)
        print()
        
        # 1. Obtener identity_origin para cabinet_lead
        print("1. Obteniendo identity_origin para cabinet_lead...")
        origin_query = text("""
            SELECT 
                person_key,
                origin_tag,
                origin_source_id
            FROM canon.identity_origin
            WHERE origin_tag = 'cabinet_lead'
            LIMIT 20
        """)
        origin_result = db.execute(origin_query)
        origin_rows = origin_result.fetchall()
        
        print(f"   Encontrados {len(origin_rows)} origins para cabinet_lead (sample)")
        print()
        
        # 2. Verificar que cada origin tiene un link correspondiente
        print("2. Verificando que cada origin tiene un link correspondiente...")
        issues = []
        
        for origin_row in origin_rows:
            person_key = origin_row.person_key
            origin_source_id = origin_row.origin_source_id
            
            # Verificar link
            link_query = text("""
                SELECT 
                    source_pk,
                    person_key
                FROM canon.identity_links
                WHERE source_table = 'module_ct_cabinet_leads'
                    AND source_pk = :origin_source_id
                    AND person_key = :person_key
                LIMIT 1
            """)
            link_result = db.execute(link_query, {
                "origin_source_id": origin_source_id,
                "person_key": person_key
            })
            link_row = link_result.fetchone()
            
            if not link_row:
                # Verificar si existe link con diferente person_key
                link_any_query = text("""
                    SELECT 
                        source_pk,
                        person_key
                    FROM canon.identity_links
                    WHERE source_table = 'module_ct_cabinet_leads'
                        AND source_pk = :origin_source_id
                    LIMIT 1
                """)
                link_any_result = db.execute(link_any_query, {"origin_source_id": origin_source_id})
                link_any_row = link_any_result.fetchone()
                
                if link_any_row:
                    issues.append({
                        "type": "person_key_mismatch",
                        "origin_source_id": origin_source_id,
                        "origin_person_key": person_key,
                        "link_person_key": link_any_row.person_key
                    })
                    print(f"   [WARNING] origin_source_id={origin_source_id[:30]}...")
                    print(f"       origin_person_key={person_key}")
                    print(f"       link_person_key={link_any_row.person_key}")
                    print(f"       → MISMATCH: person_key diferente")
                else:
                    issues.append({
                        "type": "no_link",
                        "origin_source_id": origin_source_id,
                        "origin_person_key": person_key
                    })
                    print(f"   [ERROR] origin_source_id={origin_source_id[:30]}...")
                    print(f"       origin_person_key={person_key}")
                    print(f"       → ERROR: NO tiene identity_link (ORPHAN)")
            else:
                print(f"   [OK] origin_source_id={origin_source_id[:30]}...")
                print(f"       person_key={person_key}")
                print(f"       → OK: Tiene identity_link correspondiente")
            print()
        
        # 3. Verificar que NO hay origins orphan (sin link)
        print("3. Buscando origins orphan (sin link)...")
        orphan_query = text("""
            SELECT 
                io.person_key,
                io.origin_tag,
                io.origin_source_id
            FROM canon.identity_origin io
            WHERE io.origin_tag = 'cabinet_lead'
                AND NOT EXISTS (
                    SELECT 1
                    FROM canon.identity_links il
                    WHERE il.source_table = 'module_ct_cabinet_leads'
                        AND il.source_pk = io.origin_source_id
                        AND il.person_key = io.person_key
                )
            LIMIT 10
        """)
        orphan_result = db.execute(orphan_query)
        orphan_rows = orphan_result.fetchall()
        
        if len(orphan_rows) > 0:
            print(f"   ❌ Encontrados {len(orphan_rows)} origins orphan (sin link)")
            for orphan_row in orphan_rows:
                print(f"      person_key={orphan_row.person_key}, origin_source_id={orphan_row.origin_source_id[:30]}...")
            print()
            issues.append({
                "type": "orphan_origins",
                "count": len(orphan_rows),
                "sample": [{"person_key": str(row.person_key), "origin_source_id": row.origin_source_id} for row in orphan_rows]
            })
        else:
            print(f"   [OK] No se encontraron origins orphan")
            print()
        
        # 4. Resumen
        print("=" * 80)
        print("RESUMEN")
        print("=" * 80)
        if len(issues) == 0:
            print("[OK] EXITO: Todos los identity_origin tienen links válidos")
            print(f"Origins verificados: {len(origin_rows)}")
            print(f"Issues encontrados: 0")
            return {"status": "success", "verified": len(origin_rows), "issues": 0}
        else:
            print(f"[WARNING] ADVERTENCIA: {len(issues)} issues encontrados")
            print(f"Origins verificados: {len(origin_rows)}")
            print(f"Issues encontrados: {len(issues)}")
            for issue in issues:
                print(f"  - {issue['type']}: {issue.get('origin_source_id', issue.get('count', 'N/A'))}")
            return {"status": "warning", "verified": len(origin_rows), "issues": issues}
    
    except Exception as e:
        print(f"[ERROR] ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    result = verify_identity_origin_creation()
    if result["status"] == "warning" and result.get("issues", []):
        sys.exit(1)
