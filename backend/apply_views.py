"""Script para aplicar vistas SQL actualizadas"""
import sys
from pathlib import Path
from sqlalchemy import text
from app.db import SessionLocal

# Lista de vistas a aplicar en orden
views_to_apply = [
    "backend/sql/ops/v_driver_orphans.sql",
    "backend/sql/ops/v_cabinet_funnel_status.sql",
    "backend/sql/ops/v_payment_calculation.sql",
    "backend/sql/ops/v_ct4_eligible_drivers.sql",
]

project_root = Path(__file__).parent.parent
db = SessionLocal()

try:
    print(f"[OK] Aplicando vistas SQL...")
    print(f"[OK] Directorio raiz: {project_root}\n")
    
    for view_path in views_to_apply:
        full_path = project_root / view_path
        if not full_path.exists():
            print(f"[ERROR] Archivo no encontrado: {full_path}")
            continue
        
        print(f"[OK] Aplicando: {view_path}")
        
        # Extraer nombre de la vista del path
        view_name = full_path.stem.replace('v_', 'v_')
        schema_name = 'ops'
        
        # Intentar eliminar la vista si existe (para permitir cambios estructurales)
        try:
            drop_sql = f"DROP VIEW IF EXISTS {schema_name}.{view_name} CASCADE;"
            db.execute(text(drop_sql))
            print(f"[OK] Vista eliminada si existia: {view_name}")
        except Exception as e:
            print(f"[WARNING] No se pudo eliminar vista {view_name}: {e}")
        
        # Leer el archivo SQL
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            sql_content = f.read()
        
        # Ejecutar el SQL
        try:
            db.execute(text(sql_content))
            db.commit()
            print(f"[OK] Vista aplicada exitosamente: {view_path}\n")
        except Exception as e:
            db.rollback()
            error_msg = str(e).encode('ascii', errors='ignore').decode('ascii')
            print(f"[ERROR] Error aplicando {view_path}: {error_msg}\n")
            raise
    
    print("[OK] Todas las vistas aplicadas exitosamente")
    
    # Verificar que las vistas existen
    print("\n[OK] Verificando vistas...")
    result = db.execute(text("""
        SELECT table_schema, table_name 
        FROM information_schema.views 
        WHERE (table_schema = 'ops' OR table_schema = 'public')
        AND table_name IN (
            'v_driver_orphans',
            'v_cabinet_funnel_status',
            'v_payment_calculation',
            'v_ct4_eligible_drivers'
        )
        ORDER BY table_schema, table_name
    """))
    
    views = [(row[0], row[1]) for row in result.fetchall()]
    print(f"[OK] Vistas encontradas:")
    for schema, name in views:
        print(f"  - {schema}.{name}")
    
    # Buscar específicamente v_cabinet_funnel_status
    result2 = db.execute(text("""
        SELECT table_schema, table_name 
        FROM information_schema.views 
        WHERE table_name = 'v_cabinet_funnel_status'
    """))
    funnel_view = result2.fetchone()
    if funnel_view:
        print(f"[OK] v_cabinet_funnel_status encontrada en {funnel_view[0]}.{funnel_view[1]}")
    else:
        print(f"[WARNING] v_cabinet_funnel_status NO encontrada")
    
    if len(views) == 4:
        print("[OK] Todas las vistas fueron creadas correctamente")
    else:
        print(f"[INFO] Se esperaban 4 vistas, se encontraron {len(views)}")
        
finally:
    db.close()

