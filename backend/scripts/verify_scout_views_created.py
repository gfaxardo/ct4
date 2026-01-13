#!/usr/bin/env python3
"""Verificar que las vistas de scout attribution se crearon correctamente"""

import sys
from pathlib import Path

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.config import settings
from sqlalchemy import create_engine, text

engine = create_engine(settings.database_url)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT viewname 
        FROM pg_views 
        WHERE schemaname = 'ops' 
        AND viewname LIKE '%scout_attribution%' 
        ORDER BY viewname
    """))
    
    views = result.fetchall()
    if views:
        print("Vistas encontradas:")
        for view in views:
            print(f"  - {view[0]}")
        
        # Verificar conteos
        for view_name in [v[0] for v in views]:
            try:
                count_result = conn.execute(text(f"SELECT COUNT(*) FROM ops.{view_name}"))
                count = count_result.fetchone()[0]
                print(f"  {view_name}: {count} filas")
            except Exception as e:
                print(f"  {view_name}: Error al contar - {str(e)[:100]}")
    else:
        print("No se encontraron vistas de scout_attribution")





