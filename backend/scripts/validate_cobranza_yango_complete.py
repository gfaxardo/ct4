#!/usr/bin/env python3
"""
Script de Validación Completa: Cobranza Yango Cabinet 14d
Ejecuta validaciones SQL + HTTP + correlación para evitar regresiones.
"""

import os
import sys
import json
import time
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List

# Agregar el directorio raíz del proyecto al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import text
from app.db import get_db

try:
    import requests
except ImportError:
    print("⚠️  requests no está instalado. Instalar con: pip install requests")
    requests = None

# Configuración
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def run_sql_validation(db) -> Dict[str, Any]:
    """Ejecuta validaciones SQL"""
    results = {}
    
    # 1. Conteo MV total
    result = db.execute(text("""
        SELECT 
            COUNT(*) AS total_rows,
            COUNT(CASE WHEN scout_id IS NOT NULL THEN 1 END) AS with_scout,
            COUNT(CASE WHEN scout_id IS NULL THEN 1 END) AS missing_scout,
            ROUND(COUNT(CASE WHEN scout_id IS NOT NULL THEN 1 END)::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) AS pct_with_scout
        FROM ops.mv_yango_cabinet_cobranza_enriched_14d
    """))
    row = result.fetchone()
    results["mv_stats"] = {
        "total_rows": row.total_rows or 0,
        "with_scout": row.with_scout or 0,
        "missing_scout": row.missing_scout or 0,
        "pct_with_scout": float(row.pct_with_scout) if row.pct_with_scout else 0.0
    }
    
    # 2. Distribución por bucket
    result = db.execute(text("""
        SELECT 
            scout_quality_bucket,
            COUNT(*) AS count
        FROM ops.mv_yango_cabinet_cobranza_enriched_14d
        WHERE scout_id IS NOT NULL
        GROUP BY scout_quality_bucket
        ORDER BY count DESC
    """))
    results["bucket_distribution"] = {
        row.scout_quality_bucket: row.count
        for row in result.fetchall()
    }
    
    # 3. Top 20 drivers con milestone pero sin scout
    result = db.execute(text("""
        SELECT 
            driver_id,
            lead_date,
            reached_m1_14d,
            reached_m5_14d,
            reached_m25_14d,
            amount_due_yango,
            expected_total_yango
        FROM ops.mv_yango_cabinet_cobranza_enriched_14d
        WHERE (reached_m1_14d = true OR reached_m5_14d = true OR reached_m25_14d = true)
            AND scout_id IS NULL
        ORDER BY amount_due_yango DESC NULLS LAST, lead_date DESC NULLS LAST
        LIMIT 20
    """))
    results["top_missing_with_milestone"] = [
        {
            "driver_id": r.driver_id,
            "lead_date": r.lead_date.isoformat() if r.lead_date else None,
            "reached_m1": bool(r.reached_m1_14d),
            "reached_m5": bool(r.reached_m5_14d),
            "reached_m25": bool(r.reached_m25_14d),
            "amount_due_yango": float(r.amount_due_yango) if r.amount_due_yango else 0.0,
            "expected_total_yango": float(r.expected_total_yango) if r.expected_total_yango else 0.0
        }
        for r in result.fetchall()
    ]
    
    return results


def run_api_tests() -> Dict[str, Any]:
    """Ejecuta tests HTTP de endpoints"""
    results = {}
    
    if requests is None:
        results["error"] = "requests no está instalado. Saltando tests HTTP."
        return results
    
    endpoints = [
        {
            "name": "table_endpoint",
            "url": f"{API_BASE_URL}/api/v1/ops/payments/cabinet-financial-14d",
            "params": {"limit": 100, "only_with_debt": "true"}
        },
        {
            "name": "scout_kpi_endpoint",
            "url": f"{API_BASE_URL}/api/v1/payments/yango/cabinet/cobranza-yango/scout-attribution-metrics",
            "params": {"only_with_debt": "true"}
        },
        {
            "name": "weekly_kpi_endpoint",
            "url": f"{API_BASE_URL}/api/v1/payments/yango/cabinet/cobranza-yango/weekly-kpis",
            "params": {"only_with_debt": "true", "limit_weeks": "52"}
        }
    ]
    
    for endpoint in endpoints:
        try:
            start_time = time.time()
            response = requests.get(endpoint["url"], params=endpoint["params"], timeout=30)
            elapsed_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                results[endpoint["name"]] = {
                    "status": response.status_code,
                    "response_time_ms": round(elapsed_ms, 2),
                    "valid_json": True,
                    "has_data": len(data.get("data", data.get("weeks", data.get("metrics", {})))) > 0
                }
            else:
                results[endpoint["name"]] = {
                    "status": response.status_code,
                    "response_time_ms": round(elapsed_ms, 2),
                    "valid_json": False,
                    "error": response.text[:200]
                }
        except Exception as e:
            results[endpoint["name"]] = {
                "status": "error",
                "response_time_ms": 0,
                "valid_json": False,
                "error": str(e)[:200]
            }
    
    return results


def run_correlation_checks(db) -> Dict[str, Any]:
    """Valida correlación: SUM semanal == global (tolerancia 0)"""
    results = {}
    
    # Obtener totales globales
    global_result = db.execute(text("""
        SELECT 
            COUNT(*) AS total_rows,
            SUM(amount_due_yango) AS debt_sum
        FROM ops.mv_yango_cabinet_cobranza_enriched_14d
        WHERE amount_due_yango > 0
    """))
    global_row = global_result.fetchone()
    global_total = global_row.total_rows or 0
    global_debt = float(global_row.debt_sum or 0)
    
    # Obtener suma semanal
    weekly_result = db.execute(text("""
        SELECT 
            COUNT(*) AS total_rows,
            SUM(amount_due_yango) AS debt_sum
        FROM ops.mv_yango_cabinet_cobranza_enriched_14d
        WHERE amount_due_yango > 0
            AND week_start IS NOT NULL
    """))
    weekly_row = weekly_result.fetchone()
    weekly_total = weekly_row.total_rows or 0
    weekly_debt = float(weekly_row.debt_sum or 0)
    
    # Agregación por semana
    weekly_agg_result = db.execute(text("""
        SELECT 
            SUM(total_rows) AS sum_total_rows,
            SUM(debt_sum) AS sum_debt_sum
        FROM (
            SELECT 
                week_start,
                COUNT(*) AS total_rows,
                SUM(amount_due_yango) AS debt_sum
            FROM ops.mv_yango_cabinet_cobranza_enriched_14d
            WHERE amount_due_yango > 0
                AND week_start IS NOT NULL
            GROUP BY week_start
        ) weekly_agg
    """))
    weekly_agg_row = weekly_agg_result.fetchone()
    weekly_agg_total = weekly_agg_row.sum_total_rows or 0
    weekly_agg_debt = float(weekly_agg_row.sum_debt_sum or 0)
    
    # Validación: debe coincidir exactamente (tolerancia 0)
    debt_match = abs(global_debt - weekly_agg_debt) < 0.01  # Tolerancia mínima por redondeo
    total_match = global_total == weekly_agg_total
    
    results["debt_sum_match"] = debt_match
    results["total_rows_match"] = total_match
    results["global_debt"] = global_debt
    results["weekly_agg_debt"] = weekly_agg_debt
    results["debt_difference"] = abs(global_debt - weekly_agg_debt)
    results["global_total"] = global_total
    results["weekly_agg_total"] = weekly_agg_total
    
    if not debt_match or not total_match:
        results["discrepancies"] = {
            "debt_difference": abs(global_debt - weekly_agg_debt),
            "total_difference": abs(global_total - weekly_agg_total),
            "warning": "Correlación falló - revisar datos"
        }
    
    return results


def run_performance_check(db) -> Dict[str, Any]:
    """Verifica performance de queries típicas"""
    results = {}
    
    # Query con filtros típicos (only_with_debt + milestone M25)
    start_time = time.time()
    result = db.execute(text("""
        SELECT 
            driver_id,
            driver_name,
            lead_date,
            amount_due_yango,
            scout_id,
            scout_name
        FROM ops.mv_yango_cabinet_cobranza_enriched_14d
        WHERE amount_due_yango > 0
            AND reached_m25_14d = true
        ORDER BY lead_date DESC NULLS LAST, driver_id
        LIMIT 100
    """))
    rows = result.fetchall()
    elapsed_ms = (time.time() - start_time) * 1000
    
    results["table_query_ms"] = round(elapsed_ms, 2)
    results["target_ms"] = 300
    results["meets_target"] = elapsed_ms < 300
    results["rows_returned"] = len(rows)
    
    return results


def main():
    """Función principal"""
    print("=" * 80)
    print("VALIDACIÓN COMPLETA: Cobranza Yango Cabinet 14d")
    print("=" * 80)
    print()
    
    db = next(get_db())
    report = {
        "timestamp": datetime.now().isoformat() + "Z",
        "validation_results": {}
    }
    
    try:
        # 1. Validaciones SQL
        print("1. Ejecutando validaciones SQL...")
        sql_results = run_sql_validation(db)
        report["validation_results"]["sql"] = sql_results
        print(f"   [OK] Total filas: {sql_results['mv_stats']['total_rows']}")
        print(f"   [OK] Con scout: {sql_results['mv_stats']['with_scout']} ({sql_results['mv_stats']['pct_with_scout']:.2f}%)")
        print(f"   [OK] Sin scout: {sql_results['mv_stats']['missing_scout']}")
        print()
        
        # 2. Tests HTTP
        print("2. Ejecutando tests HTTP...")
        api_results = run_api_tests()
        report["validation_results"]["api_tests"] = api_results
        for name, result in api_results.items():
            status_icon = "[OK]" if result.get("status") == 200 else "[FAIL]"
            print(f"   {status_icon} {name}: {result.get('status')} ({result.get('response_time_ms', 0):.2f}ms)")
        print()
        
        # 3. Validación correlación
        print("3. Validando correlación (SUM semanal == global)...")
        correlation_results = run_correlation_checks(db)
        report["validation_results"]["correlation_checks"] = correlation_results
        debt_icon = "[OK]" if correlation_results["debt_sum_match"] else "[FAIL]"
        total_icon = "[OK]" if correlation_results["total_rows_match"] else "[FAIL]"
        print(f"   {debt_icon} Debt sum match: {correlation_results['debt_sum_match']}")
        print(f"   {total_icon} Total rows match: {correlation_results['total_rows_match']}")
        if not correlation_results["debt_sum_match"] or not correlation_results["total_rows_match"]:
            print(f"   [WARN] Discrepancias detectadas!")
            print(f"      Debt difference: {correlation_results.get('debt_difference', 0):.2f}")
        print()
        
        # 4. Performance
        print("4. Verificando performance...")
        perf_results = run_performance_check(db)
        report["validation_results"]["performance"] = perf_results
        perf_icon = "[OK]" if perf_results["meets_target"] else "[FAIL]"
        print(f"   {perf_icon} Query con filtros: {perf_results['table_query_ms']:.2f}ms (target: <300ms)")
        print()
        
        # Resumen final
        print("=" * 80)
        print("RESUMEN")
        print("=" * 80)
        all_passed = (
            sql_results["mv_stats"]["pct_with_scout"] >= 70 and  # Ajustar según expectativa
            all(r.get("status") == 200 for r in api_results.values()) and
            correlation_results["debt_sum_match"] and
            correlation_results["total_rows_match"] and
            perf_results["meets_target"]
        )
        
        if all_passed:
            print("[OK] Todas las validaciones pasaron")
        else:
            print("[FAIL] Algunas validaciones fallaron - revisar detalles")
        
        report["all_passed"] = all_passed
        
    except Exception as e:
        print(f"[ERROR] Error durante validacion: {e}")
        report["error"] = str(e)
        import traceback
        report["traceback"] = traceback.format_exc()
    
    finally:
        db.close()
    
    # Guardar reporte JSON
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = os.path.join(REPORTS_DIR, f"cobranza_yango_validation_{timestamp_str}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    
    print()
    print(f"Reporte guardado en: {report_path}")
    print("=" * 80)
    
    return 0 if report.get("all_passed", False) else 1


if __name__ == "__main__":
    sys.exit(main())
