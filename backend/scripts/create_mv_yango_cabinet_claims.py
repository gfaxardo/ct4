#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear la vista materializada mv_yango_cabinet_claims_for_collection
y sus índices optimizados
"""
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from app.db import engine
    from sqlalchemy import text
except ImportError as e:
    print("ERROR: No se pueden importar los modulos necesarios.")
    print("   Asegurate de:")
    print("   1. Estar en el directorio backend/")
    print("   2. Tener el entorno virtual activado")
    print("   3. Haber instalado las dependencias: pip install -r requirements.txt")
    print(f"\n   Error especifico: {e}")
    sys.exit(1)

def main():
    sql_file = Path(__file__).parent.parent / "sql" / "ops" / "create_mv_yango_cabinet_claims_for_collection.sql"
    
    if not sql_file.exists():
        print(f"ERROR: No se encontro el archivo SQL en: {sql_file}")
        sys.exit(1)
    
    print(f"Leyendo SQL desde: {sql_file}")
    sql_content = sql_file.read_text(encoding='utf-8')
    
    print("Conectando a la base de datos...")
    try:
        with engine.connect() as conn:
            print("Conectado. Ejecutando SQL...")
            conn.execute(text(sql_content))
            conn.commit()
            print("Vista materializada y indices creados exitosamente!")
            print("\nCreado:")
            print("  - ops.mv_yango_cabinet_claims_for_collection")
            print("  - idx_mv_yango_cabinet_claims_misapplied_reconcilable (indice parcial)")
            print("  - Otros indices optimizados")
            print("\nPróximo paso:")
            print("  python scripts/refresh_materialized_views.py mv_yango_cabinet_claims_for_collection")
    except Exception as e:
        print(f"ERROR al ejecutar SQL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()












