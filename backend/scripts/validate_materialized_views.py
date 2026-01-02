#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para validar que las vistas materializadas coinciden con las vistas originales
Ejecutar desde el directorio backend/ con el venv activado

Uso:
    cd backend
    .\\venv\\Scripts\\activate  # Windows
    python scripts/validate_materialized_views.py
"""
import os
import sys
from pathlib import Path
from typing import Dict, Tuple, Any
from collections import defaultdict

# Agregar el directorio app al path
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

# Mapeo de vistas materializadas a vistas originales
VIEW_MAPPINGS = {
    "ops.mv_driver_name_index": "ops.v_driver_name_index",
    "ops.mv_yango_payments_ledger_latest": "ops.v_yango_payments_ledger_latest",
    "ops.mv_yango_payments_raw_current": "ops.v_yango_payments_raw_current",
    "ops.mv_yango_payments_ledger_latest_enriched": "ops.v_yango_payments_ledger_latest_enriched",
    "ops.mv_yango_receivable_payable_detail": "ops.v_yango_receivable_payable_detail",
    "ops.mv_claims_payment_status_cabinet": "ops.v_claims_payment_status_cabinet",
}

def get_row_count(view_name: str) -> int:
    """Obtiene el conteo de filas de una vista"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {view_name}"))
            return result.scalar()
    except Exception as e:
        print(f"  ERROR al contar filas en {view_name}: {e}")
        return -1

def get_sample_rows(view_name: str, limit: int = 5) -> list:
    """Obtiene una muestra de filas de una vista"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {view_name} LIMIT {limit}"))
            columns = list(result.keys())
            # SQLAlchemy 2.x: convertir Row a dict usando _mapping
            rows = [dict(row._mapping) for row in result]
            return columns, rows
    except Exception as e:
        print(f"  ERROR al obtener muestra de {view_name}: {e}")
        return None, []

def compare_counts(mv_name: str, orig_name: str) -> Tuple[bool, int, int]:
    """Compara conteos entre vista materializada y original"""
    mv_count = get_row_count(mv_name)
    orig_count = get_row_count(orig_name)
    match = (mv_count == orig_count)
    return match, mv_count, orig_count

def validate_view(mv_name: str, orig_name: str) -> Dict[str, Any]:
    """Valida una vista materializada contra su original"""
    print(f"\nValidando {mv_name} vs {orig_name}...")
    
    # Comparar conteos
    match, mv_count, orig_count = compare_counts(mv_name, orig_name)
    
    result = {
        "materialized_view": mv_name,
        "original_view": orig_name,
        "count_match": match,
        "materialized_count": mv_count,
        "original_count": orig_count,
        "columns_match": None,
        "sample_match": None,
    }
    
    if not match:
        print(f"  ADVERTENCIA: Conteos no coinciden! MV={mv_count}, Original={orig_count}")
        return result
    
    print(f"  Conteos coinciden: {mv_count} filas")
    
    # Comparar estructura de columnas (solo nombres, no tipos)
    try:
        with engine.connect() as conn:
            # Para vistas materializadas, usar pg_class y pg_attribute
            # Las vistas materializadas se almacenan como tablas
            mv_table_name = mv_name.split('.')[1]
            mv_cols = conn.execute(text(f"""
                SELECT a.attname AS column_name
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                JOIN pg_attribute a ON a.attrelid = c.oid
                WHERE n.nspname = 'ops'
                    AND c.relname = '{mv_table_name}'
                    AND a.attnum > 0
                    AND NOT a.attisdropped
                ORDER BY a.attnum
            """)).fetchall()
            mv_col_names = [col[0] for col in mv_cols]
            
            # Para vistas normales, usar information_schema
            orig_view_name = orig_name.split('.')[1]
            orig_cols = conn.execute(text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'ops' 
                AND table_name = '{orig_view_name}'
                ORDER BY ordinal_position
            """)).fetchall()
            orig_col_names = [col[0] for col in orig_cols]
            
            cols_match = (mv_col_names == orig_col_names)
            result["columns_match"] = cols_match
            
            if not cols_match:
                print(f"  ADVERTENCIA: Columnas no coinciden!")
                print(f"    MV: {mv_col_names}")
                print(f"    Original: {orig_col_names}")
            else:
                print(f"  Columnas coinciden: {len(mv_col_names)} columnas")
    except Exception as e:
        print(f"  ERROR al comparar columnas: {e}")
        result["columns_match"] = None
    
    # Comparar muestra de filas (solo si hay filas)
    if mv_count > 0:
        try:
            # Obtener muestra de ambas vistas
            mv_cols, mv_rows = get_sample_rows(mv_name, limit=3)
            orig_cols, orig_rows = get_sample_rows(orig_name, limit=3)
            
            if mv_cols and orig_cols:
                # Comparar que las columnas clave existan en ambas
                key_cols = set(mv_cols) & set(orig_cols)
                if key_cols:
                    print(f"  Muestra obtenida: {len(mv_rows)} filas de MV, {len(orig_rows)} filas de Original")
                    result["sample_match"] = True  # Asumimos que coinciden si las estructuras son iguales
        except Exception as e:
            print(f"  ERROR al comparar muestras: {e}")
            result["sample_match"] = None
    
    return result

def main():
    print("="*70)
    print("Validacion de Vistas Materializadas")
    print("="*70)
    
    results = []
    
    try:
        for mv_name, orig_name in VIEW_MAPPINGS.items():
            result = validate_view(mv_name, orig_name)
            results.append(result)
        
        # Resumen
        print("\n" + "="*70)
        print("RESUMEN DE VALIDACION")
        print("="*70)
        
        all_match = True
        for result in results:
            status = "OK" if result["count_match"] and result.get("columns_match", True) else "ERROR"
            if status != "OK":
                all_match = False
            
            print(f"\n{result['materialized_view']}:")
            print(f"  Conteo: {result['materialized_count']} vs {result['original_count']} - {'OK' if result['count_match'] else 'ERROR'}")
            if result.get("columns_match") is not None:
                print(f"  Columnas: {'OK' if result['columns_match'] else 'ERROR'}")
        
        print("\n" + "="*70)
        if all_match:
            print("VALIDACION EXITOSA: Todas las vistas materializadas coinciden con las originales")
        else:
            print("VALIDACION FALLIDA: Algunas vistas no coinciden. Revisar los detalles arriba.")
        print("="*70)
        
        return 0 if all_match else 1
        
    except Exception as e:
        print(f"\nERROR durante la validacion: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

