#!/usr/bin/env python3
"""Script para verificar que las vistas existen en la base de datos"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.database_url)

views_to_check = [
    'v_payment_calculation',
    'v_cabinet_milestones_achieved_from_payment_calc',
    'v_claims_payment_status_cabinet',
    'v_yango_cabinet_claims_for_collection',
    'v_yango_collection_with_scout'
]

print("Verificando vistas en la base de datos...")
print(f"Database URL: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'N/A'}\n")

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT schemaname, viewname 
        FROM pg_views 
        WHERE schemaname = 'ops' 
        AND viewname IN :view_names
        ORDER BY viewname
    """), {"view_names": tuple(views_to_check)})
    
    found_views = {row[1] for row in result}
    
    print("Vistas encontradas:")
    for view in views_to_check:
        status = "[OK] EXISTE" if view in found_views else "[ERROR] NO EXISTE"
        print(f"  {status}: ops.{view}")
    
    print(f"\nTotal: {len(found_views)}/{len(views_to_check)} vistas encontradas")
    
    if len(found_views) < len(views_to_check):
        missing = set(views_to_check) - found_views
        print(f"\n[WARNING] Vistas faltantes: {', '.join(missing)}")
        print("Ejecuta: python scripts/create_missing_views.py")
