#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script final para aplicar todos los fixes de una vez
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
    print(f"\n   Error especifico: {e}")
    sys.exit(1)

def execute_sql_file(sql_file: Path, description: str):
    """Ejecuta un archivo SQL"""
    if not sql_file.exists():
        print(f"ERROR: No se encontro el archivo: {sql_file}")
        return False
    
    print(f"\n{description}...")
    print(f"Leyendo: {sql_file}")
    sql_content = sql_file.read_text(encoding='utf-8')
    
    try:
        with engine.connect() as conn:
            statements = []
            current = ""
            for line in sql_content.split('\n'):
                stripped = line.strip()
                if not stripped or (stripped.startswith('--') and not current):
                    continue
                current += line + '\n'
                if stripped.endswith(';'):
                    stmt = current.strip()
                    if stmt and not stmt.startswith('--'):
                        statements.append(stmt)
                    current = ""
            if current.strip() and not current.strip().startswith('--'):
                statements.append(current.strip())
            
            print(f"  Ejecutando {len(statements)} statement(s)...")
            for i, stmt in enumerate(statements, 1):
                if stmt:
                    conn.execute(text(stmt))
                    if i % 5 == 0:
                        print(f"    Procesados {i}/{len(statements)} statements...")
            conn.commit()
        print(f"  Exito!")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("="*70)
    print("APLICAR FIX FINAL COMPLETO")
    print("="*70)
    print("\nEste script aplica TODOS los fixes y recrea las vistas materializadas")
    print("NOTA: Esto puede tomar varios minutos...")
    
    sql_dir = Path(__file__).parent.parent / "sql" / "ops"
    
    if not execute_sql_file(
        sql_dir / "final_fix_reconcilable_complete.sql",
        "Aplicando fix final completo"
    ):
        print("\nERROR: No se pudo aplicar el fix final")
        return 1
    
    print("\n" + "="*70)
    print("FIX APLICADO EXITOSAMENTE")
    print("="*70)
    print("\nAhora ejecuta el script de verificacion:")
    print("  backend/sql/ops/deep_diagnosis_reconcilable.sql")
    print("\nO el script de resultados:")
    print("  backend/sql/ops/check_reconcilable_results.sql")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())








