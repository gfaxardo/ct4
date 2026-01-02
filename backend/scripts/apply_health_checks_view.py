#!/usr/bin/env python3
"""
Script para aplicar la vista ops.v_health_checks
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text
from app.db import engine

def main():
    # Leer el archivo SQL
    sql_file = os.path.join(os.path.dirname(__file__), '..', 'sql', 'ops', 'v_health_checks.sql')
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Ejecutar el SQL
    with engine.begin() as conn:
        # Ejecutar cada statement separado por punto y coma
        # PostgreSQL puede tener múltiples statements
        conn.execute(text(sql_content))
    
    print("Vista ops.v_health_checks aplicada exitosamente")

if __name__ == '__main__':
    main()
