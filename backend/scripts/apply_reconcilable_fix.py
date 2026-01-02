#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para aplicar el fix de is_reconcilable_enriched
Ejecuta el diagnóstico, aplica el fix, refresca las vistas y ejecuta la auditoría
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
            # Ejecutar cada statement por separado
            # Dividir por ; pero mantener el contexto
            statements = []
            current = ""
            for line in sql_content.split('\n'):
                stripped = line.strip()
                # Ignorar líneas vacías y comentarios solos
                if not stripped or (stripped.startswith('--') and not current):
                    continue
                current += line + '\n'
                # Si la línea termina con ;, es el final de un statement
                if stripped.endswith(';'):
                    stmt = current.strip()
                    if stmt and not stmt.startswith('--'):
                        statements.append(stmt)
                    current = ""
            
            # Si queda algo sin ; al final, agregarlo
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
        # Si CONCURRENTLY falla, intentar sin CONCURRENTLY
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
    print("APLICAR FIX: is_reconcilable_enriched")
    print("="*70)
    
    sql_dir = Path(__file__).parent.parent / "sql" / "ops"
    
    # Paso 1: Diagnóstico antes del fix
    print("\n" + "="*70)
    print("PASO 1: Diagnóstico ANTES del fix")
    print("="*70)
    execute_sql_file(
        sql_dir / "diagnose_reconcilable_calculation.sql",
        "Ejecutando diagnóstico"
    )
    
    # Paso 2: Aplicar el fix
    print("\n" + "="*70)
    print("PASO 2: Aplicar fix a v_yango_cabinet_claims_for_collection")
    print("="*70)
    if not execute_sql_file(
        sql_dir / "fix_is_reconcilable_enriched.sql",
        "Aplicando fix"
    ):
        print("ERROR: No se pudo aplicar el fix")
        return 1
    
    # Paso 3: Recrear la vista materializada con la lógica corregida
    print("\n" + "="*70)
    print("PASO 3: Recrear vista materializada con lógica corregida")
    print("="*70)
    print("NOTA: Esto puede tomar varios minutos...")
    print("La vista materializada se recreará usando la vista base actualizada")
    
    # Primero eliminar la vista materializada existente
    print("\nEliminando vista materializada existente...")
    try:
        with engine.connect() as conn:
            conn.execute(text("DROP MATERIALIZED VIEW IF EXISTS ops.mv_yango_cabinet_claims_for_collection CASCADE;"))
            conn.commit()
        print("  Vista materializada eliminada")
    except Exception as e:
        print(f"  ERROR al eliminar: {e}")
        return 1
    
    # Ahora recrear con la lógica corregida
    # El script SQL tiene el DROP también, pero ya lo ejecutamos, así que está bien
    if not execute_sql_file(
        sql_dir / "create_mv_yango_cabinet_claims_for_collection.sql",
        "Recreando vista materializada con lógica corregida"
    ):
        print("ERROR: No se pudo recrear la vista materializada")
        return 1
    
    print("  Vista materializada recreada con lógica corregida e índices")
    
    # Paso 4: Auditoría después del fix
    print("\n" + "="*70)
    print("PASO 4: Auditoría DESPUÉS del fix")
    print("="*70)
    execute_sql_file(
        sql_dir / "audit_reconcilable_fix.sql",
        "Ejecutando auditoría"
    )
    
    print("\n" + "="*70)
    print("PROCESO COMPLETADO")
    print("="*70)
    print("\nRevisa los resultados de la auditoría para verificar que:")
    print("  1. Hay reconciliables (>0 filas)")
    print("  2. Los montos cuadran: reconcilable + not_reconcilable = total")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

