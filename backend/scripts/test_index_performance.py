#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar rendimiento antes/después de crear índice parcial
Ejecuta EXPLAIN ANALYZE de la consulta objetivo
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

QUERY = """
SELECT * FROM ops.mv_yango_cabinet_claims_for_collection
WHERE yango_payment_status='PAID_MISAPPLIED' AND is_reconcilable_enriched=true
LIMIT 50;
"""

def get_explain_analyze() -> str:
    """Obtiene el plan de ejecución con EXPLAIN ANALYZE"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text(f"EXPLAIN ANALYZE {QUERY}"))
            plan_lines = [row[0] for row in result]
            return "\n".join(plan_lines)
    except Exception as e:
        return f"ERROR: {e}"

def execute_query() -> tuple:
    """Ejecuta la consulta y mide el tiempo"""
    start = time.time()
    try:
        with engine.connect() as conn:
            result = conn.execute(text(QUERY))
            rows = result.fetchall()
            elapsed = time.time() - start
            return True, elapsed, len(rows), None
    except Exception as e:
        elapsed = time.time() - start
        return False, elapsed, 0, str(e)

def analyze_table():
    """Ejecuta ANALYZE en la tabla para actualizar estadísticas"""
    try:
        with engine.connect() as conn:
            conn.execute(text("ANALYZE ops.mv_yango_cabinet_claims_for_collection;"))
            conn.commit()
            return True
    except Exception as e:
        print(f"  ADVERTENCIA: No se pudo ejecutar ANALYZE: {e}")
        return False

def get_table_stats():
    """Obtiene estadísticas de la tabla"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) AS total_rows,
                    COUNT(*) FILTER (WHERE yango_payment_status = 'PAID_MISAPPLIED') AS misapplied_count,
                    COUNT(*) FILTER (WHERE is_reconcilable_enriched = true) AS reconcilable_count,
                    COUNT(*) FILTER (WHERE yango_payment_status = 'PAID_MISAPPLIED' AND is_reconcilable_enriched = true) AS misapplied_reconcilable_count
                FROM ops.mv_yango_cabinet_claims_for_collection;
            """))
            return dict(result.fetchone()._mapping)
    except Exception as e:
        return None

def main():
    print("="*70)
    print("PRUEBA DE RENDIMIENTO - Indice Parcial")
    print("="*70)
    print("\nConsulta:")
    print(QUERY)
    print("\n" + "="*70)
    
    # Obtener estadísticas
    print("\nEstadisticas de la tabla:")
    stats = get_table_stats()
    if stats:
        print(f"  Total de filas: {stats['total_rows']}")
        print(f"  PAID_MISAPPLIED: {stats['misapplied_count']}")
        print(f"  is_reconcilable_enriched=true: {stats['reconcilable_count']}")
        print(f"  PAID_MISAPPLIED + is_reconcilable_enriched=true: {stats['misapplied_reconcilable_count']}")
        if stats['misapplied_reconcilable_count'] == 0:
            print("\n  NOTA: No hay filas que cumplan ambas condiciones, por eso retorna 0 filas.")
    
    # Ejecutar ANALYZE para actualizar estadísticas
    print("\nEjecutando ANALYZE para actualizar estadisticas...")
    analyze_table()
    print("  ANALYZE completado")
    
    # Ejecutar consulta
    print("\nEjecutando consulta...")
    success, elapsed, row_count, error = execute_query()
    
    if success:
        print(f"  Exito: {elapsed:.3f}s ({row_count} filas)")
    else:
        print(f"  ERROR: {error}")
    
    # Obtener EXPLAIN ANALYZE
    print("\n" + "="*70)
    print("PLAN DE EJECUCION (EXPLAIN ANALYZE):")
    print("="*70)
    plan = get_explain_analyze()
    print(plan)
    
    print("\n" + "="*70)
    print("RESUMEN:")
    print("="*70)
    if success:
        print(f"  Tiempo de ejecucion: {elapsed:.3f}s")
        print(f"  Filas retornadas: {row_count}")
    else:
        print(f"  Estado: ERROR - {error}")
    
    # Verificar si se usa el índice
    if "Index Scan" in plan or "Bitmap Index Scan" in plan:
        if "idx_mv_yango_cabinet_claims_misapplied_reconcilable" in plan:
            print("\n  INDICE PARCIAL DETECTADO: El indice se esta usando correctamente")
        else:
            print("\n  INDICE DETECTADO: Se esta usando un indice (puede ser otro)")
    elif "Seq Scan" in plan:
        print("\n  ADVERTENCIA: Se esta usando Seq Scan en lugar del indice")
        print("  Posibles razones:")
        print("    - La tabla es pequena (< 1000 filas) y PostgreSQL prefiere Seq Scan")
        print("    - El costo de leer el indice es mayor que leer toda la tabla")
        print("    - Las estadisticas pueden necesitar actualizarse (ANALYZE ya ejecutado)")
        
        # Probar forzando el uso del índice
        print("\n  Probando con Seq Scan deshabilitado (forzando indice)...")
        try:
            with engine.connect() as conn:
                conn.execute(text("SET enable_seqscan = off;"))
                plan_forced = get_explain_analyze()
                conn.execute(text("SET enable_seqscan = on;"))
                
                if "Index Scan" in plan_forced or "Bitmap Index Scan" in plan_forced:
                    print("  El indice puede usarse cuando se fuerza:")
                    print("  " + "\n  ".join(plan_forced.split("\n")[:5]))
                else:
                    print("  El indice no se usa ni cuando se fuerza")
        except Exception as e:
            print(f"  ERROR al forzar indice: {e}")
    else:
        print("\n  ADVERTENCIA: No se pudo determinar el tipo de scan")

if __name__ == "__main__":
    main()

