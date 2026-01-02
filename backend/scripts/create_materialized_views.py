#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear las vistas materializadas optimizadas
Ejecutar desde el directorio backend/ con el venv activado

Uso:
    cd backend
    .\\venv\\Scripts\\activate  # Windows
    # o
    source venv/bin/activate  # Linux/Mac
    python scripts/create_materialized_views.py
"""
import os
import sys
from pathlib import Path

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

def main():
    # Leer el archivo SQL
    sql_file = Path(__file__).parent.parent / "sql" / "ops" / "create_materialized_views.sql"
    
    if not sql_file.exists():
        print(f"ERROR: No se encontro el archivo SQL en: {sql_file}")
        sys.exit(1)
    
    print(f"Leyendo SQL desde: {sql_file}")
    sql_content = sql_file.read_text(encoding='utf-8')
    
    print("Conectando a la base de datos...")
    print("NOTA: La creacion de vistas materializadas puede tomar varios minutos...")
    try:
        with engine.connect() as conn:
            print("Conectado. Ejecutando SQL...")
            # Ejecutar el SQL
            conn.execute(text(sql_content))
            conn.commit()
            print("Vistas materializadas creadas exitosamente!")
            print("\nVistas creadas:")
            print("  1. ops.mv_driver_name_index")
            print("  2. ops.mv_yango_payments_ledger_latest")
            print("  3. ops.mv_yango_payments_raw_current")
            print("  4. ops.mv_yango_payments_ledger_latest_enriched")
            print("  5. ops.mv_yango_receivable_payable_detail")
            print("  6. ops.mv_claims_payment_status_cabinet")
            print("\nPróximos pasos:")
            print("  1. Refrescar las vistas: python scripts/refresh_materialized_views.py")
            print("  2. Actualizar vistas dependientes: python scripts/update_views_to_use_materialized.py")
            print("  3. Validar resultados: python scripts/validate_materialized_views.py")
    except Exception as e:
        print(f"ERROR al ejecutar SQL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

