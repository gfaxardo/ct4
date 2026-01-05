#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar la definición del índice y probar diferentes consultas
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

def main():
    print("="*70)
    print("VERIFICACION DE DEFINICION DE INDICE")
    print("="*70)
    
    # 1. Verificar índices
    print("\n1. Indices en mv_yango_cabinet_claims_for_collection:")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE schemaname = 'ops'
                    AND tablename = 'mv_yango_cabinet_claims_for_collection'
                ORDER BY indexname;
            """))
            indexes = result.fetchall()
            if indexes:
                for idx in indexes:
                    print(f"\n   {idx[0]}:")
                    print(f"   {idx[1]}")
            else:
                print("   No se encontraron indices")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 2. Probar consulta con solo PAID_MISAPPLIED
    print("\n2. Probando consulta con solo PAID_MISAPPLIED:")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                EXPLAIN ANALYZE
                SELECT * FROM ops.mv_yango_cabinet_claims_for_collection
                WHERE yango_payment_status='PAID_MISAPPLIED'
                LIMIT 50;
            """))
            plan = "\n".join([row[0] for row in result])
            print(plan)
            if "Index Scan" in plan or "Bitmap Index Scan" in plan:
                print("   INDICE DETECTADO: Se usa un indice")
            else:
                print("   Seq Scan: No se usa indice")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 3. Probar consulta con solo is_reconcilable_enriched
    print("\n3. Probando consulta con solo is_reconcilable_enriched=true:")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                EXPLAIN ANALYZE
                SELECT * FROM ops.mv_yango_cabinet_claims_for_collection
                WHERE is_reconcilable_enriched=true
                LIMIT 50;
            """))
            plan = "\n".join([row[0] for row in result])
            print(plan)
            if "Index Scan" in plan or "Bitmap Index Scan" in plan:
                print("   INDICE DETECTADO: Se usa un indice")
            else:
                print("   Seq Scan: No se usa indice")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 4. Verificar estadísticas del índice
    print("\n4. Estadisticas del indice parcial:")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan AS index_scans,
                    idx_tup_read AS tuples_read,
                    idx_tup_fetch AS tuples_fetched
                FROM pg_stat_user_indexes
                WHERE schemaname = 'ops'
                    AND tablename = 'mv_yango_cabinet_claims_for_collection'
                    AND indexname LIKE '%misapplied%reconcilable%';
            """))
            stats = result.fetchall()
            if stats:
                for stat in stats:
                    print(f"   {stat[2]}:")
                    print(f"     Scans: {stat[3]}")
                    print(f"     Tuples read: {stat[4]}")
                    print(f"     Tuples fetched: {stat[5]}")
            else:
                print("   No se encontraron estadisticas (el indice puede no haberse usado nunca)")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 5. Verificar tamaño
    print("\n5. Tamaño del indice:")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    pg_size_pretty(pg_relation_size('ops.idx_mv_yango_cabinet_claims_misapplied_reconcilable')) AS index_size,
                    pg_size_pretty(pg_relation_size('ops.mv_yango_cabinet_claims_for_collection')) AS table_size;
            """))
            sizes = result.fetchone()
            if sizes:
                print(f"   Tamaño del indice: {sizes[0]}")
                print(f"   Tamaño de la tabla: {sizes[1]}")
    except Exception as e:
        print(f"   ERROR: {e}")
        print("   (El indice puede no existir)")

if __name__ == "__main__":
    main()








