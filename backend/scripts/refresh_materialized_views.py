#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para refrescar vistas materializadas usando REFRESH MATERIALIZED VIEW CONCURRENTLY
Ejecutar desde el directorio backend/ con el venv activado

Uso:
    cd backend
    .\\venv\\Scripts\\activate  # Windows
    python scripts/refresh_materialized_views.py [nombre_vista]
    
    Si no se especifica nombre_vista, refresca todas las vistas materializadas.
    
Ejemplos:
    python scripts/refresh_materialized_views.py
    python scripts/refresh_materialized_views.py mv_claims_payment_status_cabinet
"""
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

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

# Lista de todas las vistas materializadas
ALL_MATERIALIZED_VIEWS = [
    "ops.mv_driver_name_index",
    "ops.mv_yango_payments_ledger_latest",
    "ops.mv_yango_payments_raw_current",
    "ops.mv_yango_payments_ledger_latest_enriched",
    "ops.mv_yango_receivable_payable_detail",
    "ops.mv_claims_payment_status_cabinet",
    "ops.mv_yango_cabinet_claims_for_collection",
]

def refresh_view(view_name: str) -> float:
    """Refresca una vista materializada y retorna el tiempo de ejecución"""
    start_time = time.time()
    try:
        with engine.connect() as conn:
            # REFRESH MATERIALIZED VIEW CONCURRENTLY requiere índices únicos
            # Si no existe, usar REFRESH MATERIALIZED VIEW normal
            refresh_sql = f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name};"
            conn.execute(text(refresh_sql))
            conn.commit()
        elapsed = time.time() - start_time
        return elapsed
    except Exception as e:
        # Si CONCURRENTLY falla (por falta de índice único), intentar sin CONCURRENTLY
        if "concurrently" in str(e).lower() or "unique index" in str(e).lower():
            print(f"  Advertencia: No se puede usar CONCURRENTLY para {view_name}, usando modo normal...")
            start_time = time.time()
            with engine.connect() as conn:
                refresh_sql = f"REFRESH MATERIALIZED VIEW {view_name};"
                conn.execute(text(refresh_sql))
                conn.commit()
            elapsed = time.time() - start_time
            return elapsed
        else:
            raise

def main():
    # Obtener argumento opcional
    view_arg = sys.argv[1] if len(sys.argv) > 1 else None
    
    # Determinar qué vistas refrescar
    if view_arg:
        # Si se especifica una vista, buscar coincidencia
        if view_arg.startswith("ops."):
            views_to_refresh = [view_arg] if view_arg in ALL_MATERIALIZED_VIEWS else []
        else:
            # Buscar por nombre corto
            views_to_refresh = [v for v in ALL_MATERIALIZED_VIEWS if v.endswith(f".{view_arg}")]
        
        if not views_to_refresh:
            print(f"ERROR: Vista '{view_arg}' no encontrada.")
            print(f"\nVistas disponibles:")
            for v in ALL_MATERIALIZED_VIEWS:
                print(f"  - {v}")
            sys.exit(1)
    else:
        # Refrescar todas
        views_to_refresh = ALL_MATERIALIZED_VIEWS
    
    print(f"Refrescando {len(views_to_refresh)} vista(s) materializada(s)...")
    print("NOTA: Esto puede tomar varios minutos dependiendo del tamaño de los datos.\n")
    
    total_start = time.time()
    results = []
    
    try:
        for view_name in views_to_refresh:
            print(f"Refrescando {view_name}...", end=" ", flush=True)
            elapsed = refresh_view(view_name)
            results.append((view_name, elapsed))
            print(f"Completado en {elapsed:.2f} segundos")
        
        total_elapsed = time.time() - total_start
        
        print(f"\n{'='*60}")
        print("Resumen de refresco:")
        print(f"{'='*60}")
        for view_name, elapsed in results:
            print(f"  {view_name:50} {elapsed:>8.2f}s")
        print(f"{'='*60}")
        print(f"Total: {total_elapsed:.2f} segundos")
        
    except Exception as e:
        print(f"\nERROR al refrescar vistas: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

