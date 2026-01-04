#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para actualizar v_yango_cabinet_claims_for_collection para usar
directamente la vista materializada mv_yango_cabinet_claims_for_collection
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

SQL = """
-- Actualizar v_yango_cabinet_claims_for_collection para usar directamente la materializada
CREATE OR REPLACE VIEW ops.v_yango_cabinet_claims_for_collection AS
SELECT * FROM ops.mv_yango_cabinet_claims_for_collection;
"""

def main():
    print("Actualizando v_yango_cabinet_claims_for_collection para usar materializada...")
    try:
        with engine.connect() as conn:
            conn.execute(text(SQL))
            conn.commit()
            print("Vista actualizada exitosamente!")
            print("  ops.v_yango_cabinet_claims_for_collection ahora apunta a")
            print("  ops.mv_yango_cabinet_claims_for_collection")
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()







