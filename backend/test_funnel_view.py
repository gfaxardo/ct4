"""Script para probar crear v_cabinet_funnel_status"""
from sqlalchemy import text
from app.db import SessionLocal

db = SessionLocal()

try:
    # Leer el SQL
    with open('backend/sql/ops/v_cabinet_funnel_status.sql', 'r', encoding='utf-8', errors='ignore') as f:
        sql_content = f.read()
    
    print("[OK] Leyendo SQL de v_cabinet_funnel_status...")
    
    # Intentar eliminar la vista primero
    try:
        db.execute(text("DROP VIEW IF EXISTS ops.v_cabinet_funnel_status CASCADE"))
        print("[OK] Vista eliminada si existia")
    except Exception as e:
        print(f"[WARNING] Error eliminando vista: {e}")
    
    # Intentar crear la vista
    try:
        db.execute(text(sql_content))
        db.commit()
        print("[OK] Vista creada exitosamente")
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        # Truncar mensaje de error largo
        if len(error_msg) > 500:
            error_msg = error_msg[:500] + "..."
        print(f"[ERROR] Error creando vista: {error_msg}")
        raise
        
finally:
    db.close()



