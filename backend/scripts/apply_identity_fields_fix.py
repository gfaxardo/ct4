#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para aplicar el fix de campos de identidad para PAID_MISAPPLIED
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
            
            for stmt in statements:
                if stmt:
                    conn.execute(text(stmt))
            conn.commit()
        print(f"  Exito!")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

def refresh_materialized_view(view_name: str):
    """Refresca una vista materializada"""
    print(f"\nRefrescando {view_name}...")
    try:
        with engine.connect() as conn:
            conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name};"))
            conn.commit()
        print(f"  {view_name} refrescada exitosamente")
        return True
    except Exception as e:
        print(f"  Advertencia: No se puede usar CONCURRENTLY, usando modo normal...")
        try:
            with engine.connect() as conn:
                conn.execute(text(f"REFRESH MATERIALIZED VIEW {view_name};"))
                conn.commit()
            print(f"  {view_name} refrescada exitosamente")
            return True
        except Exception as e2:
            print(f"  ERROR: {e2}")
            return False

def main():
    print("="*70)
    print("APLICAR FIX: Campos de Identidad para PAID_MISAPPLIED")
    print("="*70)
    
    sql_dir = Path(__file__).parent.parent / "sql" / "ops"
    
    # Paso 1: Aplicar el fix
    print("\n" + "="*70)
    print("PASO 1: Aplicar fix a v_claims_payment_status_cabinet")
    print("="*70)
    if not execute_sql_file(
        sql_dir / "fix_identity_fields_for_misapplied.sql",
        "Aplicando fix de campos de identidad"
    ):
        print("ERROR: No se pudo aplicar el fix")
        return 1
    
    # Paso 2: Refrescar vistas materializadas
    print("\n" + "="*70)
    print("PASO 2: Refrescar vistas materializadas")
    print("="*70)
    print("NOTA: Esto puede tomar varios minutos...")
    
    views_to_refresh = [
        "ops.mv_claims_payment_status_cabinet",
        "ops.mv_yango_cabinet_claims_for_collection",
    ]
    
    for view_name in views_to_refresh:
        if not refresh_materialized_view(view_name):
            print(f"ERROR: No se pudo refrescar {view_name}")
            return 1
    
    print("\n" + "="*70)
    print("PROCESO COMPLETADO")
    print("="*70)
    print("\nAhora los campos identity_status, match_rule, match_confidence")
    print("deberian tener valores para PAID_MISAPPLIED.")
    print("\nEjecuta el script de verificacion:")
    print("  backend/sql/ops/check_reconcilable_results.sql")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())








