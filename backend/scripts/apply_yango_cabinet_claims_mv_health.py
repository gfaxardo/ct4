#!/usr/bin/env python3
"""
Script para aplicar la vista ops.v_yango_cabinet_claims_mv_health
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from app.db import engine

def main():
    # Leer el archivo SQL desde docs/ops/
    project_root = Path(__file__).parent.parent.parent
    sql_file = project_root / 'docs' / 'ops' / 'yango_cabinet_claims_mv_health.sql'
    
    if not sql_file.exists():
        print(f"Error: No se encontró el archivo {sql_file}")
        sys.exit(1)
    
    print(f"Leyendo archivo SQL: {sql_file}")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Ejecutar el SQL
    print("Ejecutando SQL en la base de datos...")
    with engine.begin() as conn:
        # Ejecutar cada statement separado por punto y coma
        # PostgreSQL puede tener múltiples statements
        conn.execute(text(sql_content))
    
    print("[OK] Vista ops.v_yango_cabinet_claims_mv_health aplicada exitosamente")
    print("\nPara verificar, ejecuta:")
    print("  SELECT * FROM ops.v_yango_cabinet_claims_mv_health;")

if __name__ == '__main__':
    main()

