#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear índices en la tabla correcta: ops.yango_payment_status_ledger
"""
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from app.db import engine
    from sqlalchemy import text
except ImportError as e:
    print(f"ERROR: {e}")
    sys.exit(1)

def main():
    print("Creando indices en ops.yango_payment_status_ledger...")
    try:
        with engine.connect() as conn:
            # Verificar estructura de la tabla
            check_columns = text("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'ops'
                    AND table_name = 'yango_payment_status_ledger'
                ORDER BY ordinal_position;
            """)
            columns = conn.execute(check_columns).fetchall()
            print(f"\nColumnas en ops.yango_payment_status_ledger:")
            for col in columns:
                print(f"  - {col[0]} ({col[1]})")
            
            # Crear índices optimizados
            indexes_sql = [
                # Índice para búsquedas por driver_id + milestone_value + is_paid
                """
                CREATE INDEX IF NOT EXISTS idx_yango_payment_status_ledger_driver_milestone_paid 
                    ON ops.yango_payment_status_ledger(driver_id, milestone_value, is_paid) 
                    WHERE is_paid = true AND driver_id IS NOT NULL;
                """,
                # Índice para búsquedas por person_key + milestone_value + is_paid
                """
                CREATE INDEX IF NOT EXISTS idx_yango_payment_status_ledger_person_milestone_paid 
                    ON ops.yango_payment_status_ledger(person_key, milestone_value, is_paid) 
                    WHERE is_paid = true AND person_key IS NOT NULL;
                """,
                # Índice compuesto para el LATERAL JOIN exacto
                """
                CREATE INDEX IF NOT EXISTS idx_yango_payment_status_ledger_driver_milestone_exact 
                    ON ops.yango_payment_status_ledger(driver_id, milestone_value, pay_date DESC, payment_key DESC) 
                    WHERE is_paid = true AND driver_id IS NOT NULL;
                """
            ]
            
            for idx_sql in indexes_sql:
                try:
                    conn.execute(text(idx_sql))
                    conn.commit()
                    print("Indice creado exitosamente")
                except Exception as e:
                    print(f"ADVERTENCIA al crear indice: {e}")
            
            # Verificar índices creados
            check_indexes = text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'ops'
                    AND tablename = 'yango_payment_status_ledger'
                    AND indexname LIKE 'idx_yango_payment_status_ledger%'
                ORDER BY indexname;
            """)
            indexes = conn.execute(check_indexes).fetchall()
            print(f"\nIndices creados: {len(indexes)}")
            for idx in indexes:
                print(f"  - {idx[0]}")
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()












