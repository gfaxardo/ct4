#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script completo para aplicar todos los fixes y refrescar vistas materializadas
"""
import os
import sys
import time
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
    print("APLICAR FIXES COMPLETOS Y REFRESCAR VISTAS")
    print("="*70)
    
    sql_dir = Path(__file__).parent.parent / "sql" / "ops"
    
    # Paso 1: Aplicar fix de campos de identidad
    print("\n" + "="*70)
    print("PASO 1: Aplicar fix de campos de identidad")
    print("="*70)
    if not execute_sql_file(
        sql_dir / "fix_identity_fields_for_misapplied.sql",
        "Aplicando fix de campos de identidad"
    ):
        return 1
    
    # Paso 2: Aplicar fix de is_reconcilable_enriched (por si acaso)
    print("\n" + "="*70)
    print("PASO 2: Aplicar fix de is_reconcilable_enriched")
    print("="*70)
    if not execute_sql_file(
        sql_dir / "fix_is_reconcilable_enriched.sql",
        "Aplicando fix de is_reconcilable_enriched"
    ):
        return 1
    
    # Paso 3: Refrescar vistas materializadas en orden correcto
    print("\n" + "="*70)
    print("PASO 3: Refrescar vistas materializadas")
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
        time.sleep(2)  # Pausa entre refrescos
    
    # Paso 4: Verificar resultados
    print("\n" + "="*70)
    print("PASO 4: Verificar que el fix se aplicó")
    print("="*70)
    execute_sql_file(
        sql_dir / "verify_fix_applied.sql",
        "Ejecutando verificacion"
    )
    
    # Paso 5: Verificar resultados finales
    print("\n" + "="*70)
    print("PASO 5: Verificar resultados finales")
    print("="*70)
    execute_sql_file(
        sql_dir / "check_reconcilable_results.sql",
        "Ejecutando verificacion de resultados"
    )
    
    print("\n" + "="*70)
    print("PROCESO COMPLETADO")
    print("="*70)
    print("\nRevisa los resultados para verificar que:")
    print("  1. Los campos de identidad ahora tienen valores")
    print("  2. Hay reconciliables (>0 filas)")
    print("  3. Los montos cuadran")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())











