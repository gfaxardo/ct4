#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar rendimiento de consultas clave antes/después de materialización
Ejecutar desde el directorio backend/ con el venv activado

Uso:
    cd backend
    .\\venv\\Scripts\\activate  # Windows
    python scripts/test_performance.py
"""
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

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

# Consultas clave para probar rendimiento
TEST_QUERIES = [
    {
        "name": "Consulta PAID_MISAPPLIED con LIMIT 10",
        "description": "Consulta que estaba dando timeout",
        "sql": """
            SELECT 
                driver_id,
                milestone_value,
                expected_amount,
                identity_status,
                match_rule,
                match_confidence,
                is_reconcilable_enriched,
                reason_code
            FROM ops.v_yango_cabinet_claims_for_collection
            WHERE yango_payment_status = 'PAID_MISAPPLIED'
                AND is_reconcilable_enriched = false
            ORDER BY expected_amount DESC
            LIMIT 10;
        """,
        "expected_fast": True,
    },
    {
        "name": "Conteo total de claims",
        "description": "Conteo simple de todas las filas",
        "sql": "SELECT COUNT(*) FROM ops.v_yango_cabinet_claims_for_collection;",
        "expected_fast": True,
    },
    {
        "name": "Agregados por payment_status",
        "description": "Agregación por estado de pago",
        "sql": """
            SELECT 
                yango_payment_status,
                COUNT(*) AS total_claims,
                SUM(expected_amount) AS total_amount
            FROM ops.v_yango_cabinet_claims_for_collection
            GROUP BY yango_payment_status;
        """,
        "expected_fast": True,
    },
    {
        "name": "Consulta PAID_MISAPPLIED reconciliables",
        "description": "Filtro por reconciliables",
        "sql": """
            SELECT 
                COUNT(*) AS total_claims,
                SUM(expected_amount) AS total_amount
            FROM ops.v_yango_cabinet_claims_for_collection
            WHERE yango_payment_status = 'PAID_MISAPPLIED'
                AND is_reconcilable_enriched = true;
        """,
        "expected_fast": True,
    },
    {
        "name": "Consulta completa sin filtros (LIMIT 100)",
        "description": "Consulta completa con todas las columnas",
        "sql": """
            SELECT * 
            FROM ops.v_yango_cabinet_claims_for_collection
            ORDER BY expected_amount DESC
            LIMIT 100;
        """,
        "expected_fast": True,
    },
]

def execute_query(sql: str, timeout: int = 60) -> Tuple[bool, float, int, Exception]:
    """
    Ejecuta una consulta y mide el tiempo de ejecución
    Retorna: (success, elapsed_time, row_count, error)
    """
    start_time = time.time()
    try:
        with engine.connect() as conn:
            # Configurar timeout
            conn.execute(text(f"SET statement_timeout = {timeout * 1000};"))
            
            result = conn.execute(text(sql))
            rows = result.fetchall()
            row_count = len(rows)
            
            elapsed = time.time() - start_time
            return True, elapsed, row_count, None
    except Exception as e:
        elapsed = time.time() - start_time
        return False, elapsed, 0, e

def format_time(seconds: float) -> str:
    """Formatea tiempo en formato legible"""
    if seconds < 1:
        return f"{seconds * 1000:.2f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.2f}s"

def test_query(query_def: Dict) -> Dict:
    """Prueba una consulta y retorna resultados"""
    print(f"\n{'='*70}")
    print(f"Prueba: {query_def['name']}")
    print(f"Descripcion: {query_def['description']}")
    print(f"{'='*70}")
    
    print("Ejecutando consulta...")
    success, elapsed, row_count, error = execute_query(query_def['sql'], timeout=120)
    
    result = {
        "name": query_def['name'],
        "description": query_def['description'],
        "success": success,
        "elapsed_time": elapsed,
        "row_count": row_count,
        "error": str(error) if error else None,
        "formatted_time": format_time(elapsed),
    }
    
    if success:
        print(f"  Exito: {result['formatted_time']} ({row_count} filas)")
        if query_def.get('expected_fast') and elapsed > 10:
            print(f"  ADVERTENCIA: Consulta lenta (esperado < 10s)")
    else:
        print(f"  ERROR: {error}")
        if "timeout" in str(error).lower():
            print(f"  TIMEOUT: La consulta excedio el tiempo limite")
    
    return result

def main():
    print("="*70)
    print("PRUEBA DE RENDIMIENTO - Vistas Materializadas")
    print("="*70)
    print("\nEste script prueba el rendimiento de consultas clave que usan")
    print("las vistas materializadas optimizadas.")
    print("\nNOTA: Si las vistas materializadas no estan refrescadas, los")
    print("resultados pueden no ser precisos. Ejecutar primero:")
    print("  python scripts/refresh_materialized_views.py")
    
    input("\nPresiona Enter para continuar...")
    
    results = []
    
    try:
        for query_def in TEST_QUERIES:
            result = test_query(query_def)
            results.append(result)
        
        # Resumen
        print("\n" + "="*70)
        print("RESUMEN DE RENDIMIENTO")
        print("="*70)
        
        total_time = sum(r['elapsed_time'] for r in results)
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful
        
        print(f"\nConsultas ejecutadas: {len(results)}")
        print(f"  Exitosas: {successful}")
        print(f"  Fallidas: {failed}")
        print(f"  Tiempo total: {format_time(total_time)}")
        print(f"  Tiempo promedio: {format_time(total_time / len(results))}")
        
        print("\nDetalle por consulta:")
        for result in results:
            status = "OK" if result['success'] else "ERROR"
            print(f"  {result['name']:50} {result['formatted_time']:>15} [{status}]")
        
        print("\n" + "="*70)
        if failed == 0:
            print("TODAS LAS CONSULTAS COMPLETARON EXITOSAMENTE")
        else:
            print(f"ADVERTENCIA: {failed} consulta(s) fallaron")
        print("="*70)
        
        # Verificar si hay timeouts
        timeouts = [r for r in results if r['error'] and 'timeout' in r['error'].lower()]
        if timeouts:
            print("\nCONSULTAS CON TIMEOUT:")
            for r in timeouts:
                print(f"  - {r['name']}")
            print("\nRecomendaciones:")
            print("  1. Verificar que las vistas materializadas esten refrescadas")
            print("  2. Verificar que los indices esten creados correctamente")
            print("  3. Considerar aumentar el timeout si es necesario")
        
        return 0 if failed == 0 else 1
        
    except KeyboardInterrupt:
        print("\n\nPrueba interrumpida por el usuario")
        return 1
    except Exception as e:
        print(f"\nERROR durante la prueba: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

