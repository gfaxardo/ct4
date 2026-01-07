#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar qué índices existen y en qué tablas
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
    print("Verificando indices en ops.yango_payments_ledger...")
    try:
        with engine.connect() as conn:
            # Verificar si la tabla existe
            check_table = text("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.tables 
                    WHERE table_schema = 'ops' 
                    AND table_name = 'yango_payments_ledger'
                );
            """)
            table_exists = conn.execute(check_table).scalar()
            print(f"Tabla ops.yango_payments_ledger existe: {table_exists}")
            
            # Verificar índices en ops
            check_indexes = text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = 'ops'
                    AND tablename LIKE '%yango%'
                ORDER BY tablename, indexname;
            """)
            indexes = conn.execute(check_indexes).fetchall()
            print(f"\nIndices encontrados en schema ops (yango%): {len(indexes)}")
            for idx in indexes:
                print(f"  - {idx[1]}.{idx[2]}")
            
            # Verificar vistas que dependen de v_yango_payments_ledger_latest_enriched
            check_views = text("""
                SELECT 
                    dependent_ns.nspname as dependent_schema,
                    dependent_view.relname as dependent_view,
                    source_ns.nspname as source_schema,
                    source_table.relname as source_table
                FROM pg_depend
                JOIN pg_rewrite ON pg_depend.objid = pg_rewrite.oid
                JOIN pg_class as dependent_view ON pg_rewrite.ev_class = dependent_view.oid
                JOIN pg_class as source_table ON pg_depend.refobjid = source_table.oid
                JOIN pg_namespace dependent_ns ON dependent_view.relnamespace = dependent_ns.oid
                JOIN pg_namespace source_ns ON source_table.relnamespace = source_ns.oid
                WHERE source_ns.nspname = 'ops'
                    AND source_table.relname = 'v_yango_payments_ledger_latest_enriched'
                    AND dependent_view.relkind = 'v';
            """)
            views = conn.execute(check_views).fetchall()
            print(f"\nVistas que dependen de v_yango_payments_ledger_latest_enriched: {len(views)}")
            for v in views:
                print(f"  - {v[0]}.{v[1]}")
                
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()














