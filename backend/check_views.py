"""Script para verificar vistas"""
from sqlalchemy import text
from app.db import SessionLocal

db = SessionLocal()

try:
    # Verificar todas las vistas en ops
    result = db.execute(text("""
        SELECT table_schema, table_name 
        FROM information_schema.views 
        WHERE table_schema = 'ops'
        ORDER BY table_name
    """))
    
    print("Todas las vistas en esquema 'ops':")
    views = result.fetchall()
    for schema, name in views:
        print(f"  - {schema}.{name}")
    
    print(f"\nTotal: {len(views)} vistas")
    
    # Verificar específicamente v_cabinet_funnel_status
    result2 = db.execute(text("""
        SELECT 1 
        FROM information_schema.views 
        WHERE table_schema = 'ops' 
        AND table_name = 'v_cabinet_funnel_status'
    """))
    
    exists = result2.fetchone() is not None
    print(f"\nv_cabinet_funnel_status existe: {exists}")
    
    # Intentar consultar la vista directamente
    if exists:
        try:
            result3 = db.execute(text("SELECT COUNT(*) FROM ops.v_cabinet_funnel_status"))
            count = result3.fetchone()[0]
            print(f"Registros en v_cabinet_funnel_status: {count}")
        except Exception as e:
            print(f"Error consultando vista: {e}")
    else:
        # Intentar crear manualmente para ver el error
        print("\nIntentando verificar si la vista tiene un error...")
        result4 = db.execute(text("""
            SELECT pg_get_viewdef('ops.v_cabinet_funnel_status'::regclass, true)
        """))
        view_def = result4.fetchone()
        if view_def:
            print("Vista definida pero no aparece en information_schema?")
        else:
            print("Vista no existe en el sistema")
            
finally:
    db.close()



