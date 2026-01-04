#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar que el índice existe y forzar su uso para comparar rendimiento
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

def check_index_exists():
    """Verifica si el índice existe"""
    query = """
    SELECT 
        schemaname,
        tablename,
        indexname,
        indexdef
    FROM pg_indexes
    WHERE schemaname = 'ops'
        AND tablename = 'mv_yango_cabinet_claims_for_collection'
        AND indexname LIKE '%misapplied%reconcilable%'
    ORDER BY indexname;
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            indexes = result.fetchall()
            return indexes
    except Exception as e:
        print(f"ERROR al verificar indices: {e}")
        return []

def get_table_stats():
    """Obtiene estadísticas de la tabla"""
    query = """
    SELECT 
        COUNT(*) AS total_rows,
        COUNT(*) FILTER (WHERE yango_payment_status = 'PAID_MISAPPLIED') AS misapplied_count,
        COUNT(*) FILTER (WHERE is_reconcilable_enriched = true) AS reconcilable_count,
        COUNT(*) FILTER (WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = true) AS misapplied_reconcilable_count
    FROM ops.mv_yango_cabinet_claims_for_collection;
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            return dict(result.fetchone()._mapping)
    except Exception as e:
        print(f"ERROR al obtener estadisticas: {e}")
        return None

def explain_analyze_with_options(enable_seqscan=True):
    """Ejecuta EXPLAIN ANALYZE con opciones de optimizador"""
    query = """
    SELECT * FROM ops.mv_yango_cabinet_claims_for_collection
    WHERE yango_payment_status='PAID_MISAPPLIED' AND is_reconcilable_enriched=true
    LIMIT 50;
    """
    
    explain_query = f"""
    SET enable_seqscan = {'on' if enable_seqscan else 'off'};
    EXPLAIN ANALYZE {query}
    """
    
    try:
        with engine.connect() as conn:
            # Ejecutar SET y EXPLAIN ANALYZE
            conn.execute(text("SET enable_seqscan = " + ('on' if enable_seqscan else 'off') + ";"))
            result = conn.execute(text(f"EXPLAIN ANALYZE {query}"))
            plan_lines = [row[0] for row in result]
            return "\n".join(plan_lines)
    except Exception as e:
        return f"ERROR: {e}"

def main():
    print("="*70)
    print("VERIFICACION DE INDICE Y RENDIMIENTO")
    print("="*70)
    
    # 1. Verificar que el índice existe
    print("\n1. Verificando indices...")
    indexes = check_index_exists()
    if indexes:
        print(f"   Encontrados {len(indexes)} indice(s):")
        for idx in indexes:
            print(f"     - {idx[2]}")
            print(f"       {idx[3][:100]}...")
    else:
        print("   ADVERTENCIA: No se encontro el indice parcial!")
        print("   Ejecutar: python scripts/create_mv_yango_cabinet_claims.py")
        return
    
    # 2. Obtener estadísticas
    print("\n2. Estadisticas de la tabla:")
    stats = get_table_stats()
    if stats:
        print(f"   Total de filas: {stats['total_rows']}")
        print(f"   PAID_MISAPPLIED: {stats['misapplied_count']}")
        print(f"   is_reconcilable_enriched=true: {stats['reconcilable_count']}")
        print(f"   PAID_MISAPPLIED + is_reconcilable_enriched=true: {stats['misapplied_reconcilable_count']}")
        
        if stats['misapplied_reconcilable_count'] == 0:
            print("\n   ADVERTENCIA: No hay filas que cumplan ambas condiciones!")
            print("   Por eso retorna 0 filas.")
    
    # 3. EXPLAIN ANALYZE con Seq Scan habilitado (comportamiento normal)
    print("\n3. PLAN DE EJECUCION (Seq Scan habilitado - comportamiento normal):")
    print("="*70)
    plan_normal = explain_analyze_with_options(enable_seqscan=True)
    print(plan_normal)
    
    # 4. EXPLAIN ANALYZE con Seq Scan deshabilitado (forzar uso de índice)
    print("\n4. PLAN DE EJECUCION (Seq Scan deshabilitado - forzar indice):")
    print("="*70)
    plan_forced = explain_analyze_with_options(enable_seqscan=False)
    print(plan_forced)
    
    # 5. Análisis
    print("\n" + "="*70)
    print("ANALISIS:")
    print("="*70)
    
    if "Index Scan" in plan_forced or "Bitmap Index Scan" in plan_forced:
        print("  El indice puede usarse cuando se fuerza.")
        if "Seq Scan" in plan_normal:
            print("  El optimizador eligio Seq Scan porque:")
            if stats and stats['total_rows'] < 1000:
                print("    - La tabla es pequena (< 1000 filas)")
            print("    - PostgreSQL prefiere Seq Scan para tablas pequenas")
            print("    - El costo de leer el indice puede ser mayor que leer toda la tabla")
    else:
        print("  ADVERTENCIA: El indice no se usa ni cuando se fuerza.")
        print("  Posibles causas:")
        print("    - El indice no cubre las columnas correctas")
        print("    - La condicion WHERE no coincide con el indice parcial")
        print("    - Necesita ANALYZE en la tabla")
    
    # 6. Sugerencia de ANALYZE
    print("\n" + "="*70)
    print("RECOMENDACION:")
    print("="*70)
    print("  Ejecutar ANALYZE para actualizar estadisticas:")
    print("    ANALYZE ops.mv_yango_cabinet_claims_for_collection;")
    print("\n  Esto ayuda al optimizador a elegir el mejor plan.")

if __name__ == "__main__":
    main()







