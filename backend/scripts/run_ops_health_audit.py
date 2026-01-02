#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CT4 Ops Health — Script de Auditoría Automática

Ejecuta el flujo completo de discovery, registry y validaciones,
generando reportes automáticos (Markdown + JSON).

Nota: En Windows, asegurar que la consola use UTF-8:
    chcp 65001
    O ejecutar: $OutputEncoding = [System.Text.Encoding]::UTF8
"""
import sys
import io

# Forzar UTF-8 en Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
import subprocess
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

# Verificar dependencias críticas
try:
    from sqlalchemy import create_engine, text
except ImportError:
    print("ERROR: sqlalchemy no está instalado.")
    print("   Instalar dependencias: pip install -r backend/requirements.txt")
    print("   O activar entorno virtual: source venv/bin/activate (Linux) o venv\\Scripts\\activate (Windows)")
    sys.exit(2)

# Intentar importar settings, con fallback a variable de entorno
try:
    from app.config import settings
    DATABASE_URL = settings.database_url
except ImportError as e:
    # Si no se puede importar (dependencias faltantes), usar variable de entorno
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("=" * 70)
        print("ERROR: No se puede importar app.config y DATABASE_URL no está definida.")
        print("=" * 70)
        print("\nSolución:")
        print("  1. Instalar dependencias:")
        print("     pip install -r backend/requirements.txt")
        print("\n  2. O definir DATABASE_URL como variable de entorno:")
        print("     export DATABASE_URL='postgresql://user:pass@host:port/db'  # Linux/Mac")
        print("     $env:DATABASE_URL='postgresql://user:pass@host:port/db'    # Windows PowerShell")
        print(f"\nError específico: {e}")
        sys.exit(2)
    print("⚠️  Usando DATABASE_URL desde variable de entorno (app.config no disponible)")
    print("   Recomendación: Instalar dependencias para mejor compatibilidad")

# Colores para output
class Colors:
    OK = '\033[92m'
    WARN = '\033[93m'
    ERROR = '\033[91m'
    INFO = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Imprime un header formateado."""
    print(f"\n{Colors.BOLD}{Colors.INFO}{'='*70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.INFO}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.INFO}{'='*70}{Colors.RESET}\n")


def print_success(text: str):
    """Imprime mensaje de éxito."""
    try:
        print(f"{Colors.OK}✓{Colors.RESET} {text}")
    except UnicodeEncodeError:
        print(f"[OK] {text}")


def print_warning(text: str):
    """Imprime mensaje de advertencia."""
    try:
        print(f"{Colors.WARN}⚠{Colors.RESET} {text}")
    except UnicodeEncodeError:
        print(f"[WARN] {text}")


def print_error(text: str):
    """Imprime mensaje de error."""
    try:
        print(f"{Colors.ERROR}✗{Colors.RESET} {text}")
    except UnicodeEncodeError:
        print(f"[ERROR] {text}")


def run_discovery_script(script_name: str) -> bool:
    """Ejecuta un script de discovery y retorna True si exitoso."""
    script_path = Path(__file__).parent / script_name
    if not script_path.exists():
        print_error(f"Script no encontrado: {script_name}")
        return False
    
    print(f"  Ejecutando {script_name}...")
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True,
            check=True
        )
        print_success(f"{script_name} completado")
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"    {line}")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"{script_name} falló con código {e.returncode}")
        if e.stdout:
            print(f"    STDOUT: {e.stdout}")
        if e.stderr:
            print(f"    STDERR: {e.stderr}")
        return False
    except Exception as e:
        print_error(f"Error ejecutando {script_name}: {e}")
        return False


def run_populate_registry() -> bool:
    """Ejecuta populate_source_registry.py y retorna True si exitoso."""
    script_path = Path(__file__).parent / "populate_source_registry.py"
    if not script_path.exists():
        print_error("populate_source_registry.py no encontrado")
        return False
    
    print(f"  Ejecutando populate_source_registry.py...")
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True,
            check=True
        )
        print_success("Registry poblado exitosamente")
        if result.stdout:
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    print(f"    {line}")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"populate_source_registry.py falló con código {e.returncode}")
        if e.stdout:
            print(f"    STDOUT: {e.stdout}")
        if e.stderr:
            print(f"    STDERR: {e.stderr}")
        return False
    except Exception as e:
        print_error(f"Error ejecutando populate_source_registry.py: {e}")
        return False


def execute_query_safe(engine, query: str, description: str = None, params: dict = None):
    """
    Ejecuta una query de forma aislada (nueva conexión) y retorna resultados.
    
    Si hay un error técnico (vista faltante, error SQL), retorna None y registra
    el error en infra_warnings. Esto previene que errores técnicos aborten
    otras validaciones.
    
    Args:
        engine: SQLAlchemy engine (no conexión)
        query: Query SQL a ejecutar
        description: Descripción de la query (para logging)
        params: Parámetros para la query (opcional)
    
    Returns:
        tuple: (rows, error_message) donde rows es lista de resultados o None si error,
               y error_message es None si exitoso o mensaje de error si falló
    """
    try:
        if description:
            print(f"  {description}...")
        
        # Crear nueva conexión aislada para esta query
        # Esto previene que errores en una query afecten otras
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})
            rows = result.fetchall()
            
            if description:
                print_success(f"{description}: {len(rows)} resultados")
            return rows, None
            
    except Exception as e:
        # Error técnico: vista faltante, error SQL, etc.
        # NO es un error de negocio, solo un problema de infraestructura
        error_msg = str(e)
        if description:
            print_warning(f"{description} falló (error técnico): {error_msg[:100]}")
        return None, error_msg


def get_coverage_stats(engine) -> tuple:
    """
    Obtiene estadísticas de cobertura usando conexiones aisladas.
    
    Returns:
        tuple: (stats_dict, infra_warnings_list)
    """
    stats = {}
    infra_warnings = []
    
    # Total objetos descubiertos (desde CSV) - no requiere DB
    csv_file = Path(__file__).parent.parent / "sql" / "ops" / "discovery_objects.csv"
    discovered_count = 0
    if csv_file.exists():
        import csv
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            discovered_count = sum(1 for _ in reader)
    
    stats["discovered_objects"] = discovered_count
    
    # Total objetos en registry - query aislada
    query = "SELECT COUNT(*) FROM ops.source_registry"
    rows, error = execute_query_safe(engine, query, "Total objetos en registry")
    if rows is None:
        infra_warnings.append(f"No se pudo obtener total de objetos en registry: {error}")
        stats["registered_objects"] = 0
    else:
        stats["registered_objects"] = rows[0][0] if rows else 0
    
    # Objetos en DB pero no en registry - query aislada
    query = """
        SELECT n.nspname AS schema_name, c.relname AS object_name
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname IN ('public', 'ops', 'canon', 'raw', 'observational')
            AND c.relkind IN ('r', 'v', 'm')
            AND NOT c.relname LIKE 'pg_%'
            AND NOT EXISTS (
                SELECT 1 FROM ops.source_registry r
                WHERE r.schema_name = n.nspname AND r.object_name = c.relname
            )
        ORDER BY n.nspname, c.relname
    """
    rows, error = execute_query_safe(engine, query, "Objetos en DB no registrados")
    if rows is None:
        infra_warnings.append(f"No se pudieron obtener objetos no registrados: {error}")
        stats["unregistered_objects"] = []
    else:
        stats["unregistered_objects"] = [
            {"schema_name": row[0], "object_name": row[1]} 
            for row in rows
        ]
    
    # Objetos registrados pero no existentes - query aislada
    query = """
        SELECT r.schema_name, r.object_name
        FROM ops.source_registry r
        WHERE NOT EXISTS (
            SELECT 1
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = r.schema_name
                AND c.relname = r.object_name
                AND c.relkind IN ('r', 'v', 'm')
        )
        ORDER BY r.schema_name, r.object_name
    """
    rows, error = execute_query_safe(engine, query, "Objetos registrados pero no existentes")
    if rows is None:
        infra_warnings.append(f"No se pudieron obtener objetos faltantes: {error}")
        stats["missing_objects"] = []
    else:
        stats["missing_objects"] = [
            {"schema_name": row[0], "object_name": row[1]} 
            for row in rows
        ]
    
    return stats, infra_warnings


def get_health_checks(engine) -> tuple:
    """
    Obtiene todos los health checks usando conexión aislada.
    
    Returns:
        tuple: (checks_list, infra_warnings_list)
    """
    query = """
        SELECT 
            check_key,
            severity,
            status,
            message,
            drilldown_url,
            last_evaluated_at
        FROM ops.v_health_checks
        ORDER BY 
            CASE severity 
                WHEN 'error' THEN 1 
                WHEN 'warning' THEN 2 
                WHEN 'info' THEN 3 
            END,
            check_key
    """
    rows, error = execute_query_safe(engine, query, "Obteniendo health checks")
    
    if rows is None:
        # Vista no existe o error técnico
        warning_msg = f"Vista ops.v_health_checks no disponible: {error}"
        return [], [warning_msg]
    
    checks = []
    for row in rows:
        checks.append({
            "check_key": row[0],
            "severity": row[1],
            "status": row[2],
            "message": row[3],
            "drilldown_url": row[4],
            "last_evaluated_at": row[5].isoformat() if row[5] else None
        })
    
    return checks, []


def get_global_health(engine) -> tuple:
    """
    Obtiene estado global de salud usando conexión aislada.
    
    Si la vista no existe, retorna UNKNOWN y registra advertencia.
    
    Returns:
        tuple: (global_health_dict, infra_warnings_list)
    """
    query = "SELECT * FROM ops.v_health_global"
    rows, error = execute_query_safe(engine, query, "Obteniendo estado global")
    
    if rows is None:
        # Vista no existe - esto es un error técnico, no de negocio
        warning_msg = f"Vista ops.v_health_global no disponible: {error}"
        return {
            "global_status": "UNKNOWN",
            "error_count": 0,
            "warn_count": 0,
            "ok_count": 0,
            "calculated_at": datetime.now().isoformat()
        }, [warning_msg]
    
    if not rows:
        return {
            "global_status": "UNKNOWN",
            "error_count": 0,
            "warn_count": 0,
            "ok_count": 0,
            "calculated_at": datetime.now().isoformat()
        }, []
    
    row = rows[0]
    return {
        "global_status": row[0],
        "error_count": row[1],
        "warn_count": row[2],
        "ok_count": row[3],
        "calculated_at": row[4].isoformat() if row[4] else datetime.now().isoformat()
    }, []


def get_unregistered_used_objects(engine) -> tuple:
    """
    Obtiene objetos usados pero no registrados usando conexiones aisladas.
    
    Returns:
        tuple: (used_objects_list, infra_warnings_list)
    """
    csv_file = Path(__file__).parent.parent / "sql" / "ops" / "discovery_usage_backend.csv"
    used_objects = []
    infra_warnings = []
    
    if not csv_file.exists():
        print_warning(f"CSV de uso no encontrado: {csv_file}")
        return used_objects, []
    
    try:
        import csv
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                schema_name = row.get("schema_name", "").strip()
                object_name = row.get("object_name", "").strip()
                usage_context = row.get("usage_context", "").strip()
                
                if not schema_name or not object_name:
                    continue
                
                # Verificar si está en registry - query aislada por objeto
                query = """
                    SELECT COUNT(*) FROM ops.source_registry
                    WHERE schema_name = :schema_name AND object_name = :object_name
                """
                rows, error = execute_query_safe(
                    engine, query, None,
                    {"schema_name": schema_name, "object_name": object_name}
                )
                
                if rows is None:
                    # Error técnico al verificar este objeto - continuar con los demás
                    infra_warnings.append(
                        f"Error verificando {schema_name}.{object_name} en registry: {error}"
                    )
                    continue
                
                # Convertir Decimal a int si es necesario
                count = rows[0][0] if rows else 0
                count_int = int(count) if isinstance(count, Decimal) else (int(count) if count else 0)
                if count_int == 0:
                    used_objects.append({
                        "schema_name": schema_name,
                        "object_name": object_name,
                        "usage_context": usage_context
                    })
    except Exception as e:
        warning_msg = f"Error leyendo CSV de uso: {e}"
        print_warning(warning_msg)
        infra_warnings.append(warning_msg)
    
    return used_objects, infra_warnings


def get_critical_impacts(engine) -> tuple:
    """
    Obtiene impactos críticos usando conexiones aisladas.
    
    Cada query se ejecuta de forma independiente para evitar que errores
    en una afecten a las demás.
    
    Returns:
        tuple: (impacts_dict, infra_warnings_list)
    """
    impacts = {
        "raw_stale_affecting_critical": [],
        "mv_refresh_failed": [],
        "mv_not_populated": [],
        "critical_mv_no_refresh_log": []
    }
    infra_warnings = []
    
    # RAW stale afectando MV crítica - query aislada
    query = """
        SELECT 
            r_raw.schema_name,
            r_raw.object_name,
            r_mv.schema_name AS mv_schema,
            r_mv.object_name AS mv_name,
            v.business_days_lag
        FROM ops.source_registry r_raw
        JOIN ops.v_data_health_status v ON v.source_name = r_raw.object_name
        JOIN ops.source_registry r_mv ON (
            r_mv.depends_on @> jsonb_build_array(
                jsonb_build_object('schema', r_raw.schema_name, 'name', r_raw.object_name)
            )
            AND (r_mv.is_critical = true OR r_mv.criticality = 'critical')
            AND r_mv.object_type = 'matview'
        )
        WHERE r_raw.layer = 'RAW'
            AND v.business_days_lag > 2
        ORDER BY v.business_days_lag DESC
    """
    rows, error = execute_query_safe(engine, query, "RAW stale afectando MVs críticas")
    if rows is None:
        infra_warnings.append(f"No se pudieron obtener RAW stale afectando MVs críticas: {error}")
    else:
        impacts["raw_stale_affecting_critical"] = [
            {
                "raw_schema": row[0],
                "raw_name": row[1],
                "mv_schema": row[2],
                "mv_name": row[3],
                "days_lag": float(row[4]) if row[4] is not None else 0.0
            }
            for row in rows
        ]
    
    # MVs con refresh fallido - query aislada
    query = """
        SELECT DISTINCT
            l.schema_name,
            l.mv_name,
            l.error_message,
            l.refreshed_at
        FROM ops.mv_refresh_log l
        WHERE l.status = 'FAILED'
            AND l.refreshed_at = (
                SELECT MAX(l2.refreshed_at)
                FROM ops.mv_refresh_log l2
                WHERE l2.schema_name = l.schema_name
                    AND l2.mv_name = l.mv_name
            )
        ORDER BY l.refreshed_at DESC
    """
    rows, error = execute_query_safe(engine, query, "MVs con refresh fallido")
    if rows is None:
        infra_warnings.append(f"No se pudieron obtener MVs con refresh fallido: {error}")
    else:
        impacts["mv_refresh_failed"] = [
            {
                "schema_name": row[0],
                "mv_name": row[1],
                "error_message": row[2],
                "refreshed_at": row[3].isoformat() if row[3] else None
            }
            for row in rows
        ]
    
    # MVs no pobladas - query aislada
    query = """
        SELECT m.schemaname, m.matviewname
        FROM pg_matviews m
        WHERE m.schemaname IN ('ops', 'canon')
            AND NOT m.ispopulated
        ORDER BY m.schemaname, m.matviewname
    """
    rows, error = execute_query_safe(engine, query, "MVs no pobladas")
    if rows is None:
        infra_warnings.append(f"No se pudieron obtener MVs no pobladas: {error}")
    else:
        impacts["mv_not_populated"] = [
            {"schema_name": row[0], "mv_name": row[1]}
            for row in rows
        ]
    
    # MVs críticas sin refresh log - query aislada
    query = """
        SELECT r.schema_name, r.object_name
        FROM ops.source_registry r
        WHERE r.object_type = 'matview'
            AND (r.is_critical = true OR r.criticality = 'critical')
            AND NOT EXISTS (
                SELECT 1
                FROM ops.mv_refresh_log l
                WHERE l.schema_name = r.schema_name
                    AND l.mv_name = r.object_name
            )
        ORDER BY r.schema_name, r.object_name
    """
    rows, error = execute_query_safe(engine, query, "MVs críticas sin refresh log")
    if rows is None:
        infra_warnings.append(f"No se pudieron obtener MVs críticas sin refresh log: {error}")
    else:
        impacts["critical_mv_no_refresh_log"] = [
            {"schema_name": row[0], "mv_name": row[1]}
            for row in rows
        ]
    
    return impacts, infra_warnings


def classify_status(checks: list, global_health: dict, infra_warnings: list) -> tuple:
    """
    Clasifica el estado: CRITICAL, WARNING, o OK.
    
    IMPORTANTE: Solo errores de NEGOCIO (checks con severity=error y status=ERROR)
    hacen que el estado sea CRITICAL. Errores técnicos (infra_warnings) solo
    generan WARNING.
    
    Args:
        checks: Lista de health checks
        global_health: Estado global de salud
        infra_warnings: Lista de advertencias de infraestructura (errores técnicos)
    
    Returns:
        tuple: (status_string, exit_code)
    """
    has_critical = False
    has_warning = False
    
    # Verificar checks con severity=error y status=ERROR (errores de negocio)
    for check in checks:
        if check["severity"] == "error" and check["status"] == "ERROR":
            # Este es un error de negocio real, no técnico
            has_critical = True
        elif check["status"] in ("WARN", "ERROR"):
            has_warning = True
    
    # Verificar estado global (solo si no es UNKNOWN)
    if global_health["global_status"] == "ERROR":
        # ERROR en estado global indica errores de negocio
        has_critical = True
    elif global_health["global_status"] == "WARN":
        has_warning = True
    elif global_health["global_status"] == "UNKNOWN":
        # UNKNOWN es un error técnico, no de negocio
        # Se maneja como warning si hay infra_warnings
        if infra_warnings:
            has_warning = True
    
    # Errores técnicos (infra_warnings) solo generan WARNING, nunca CRITICAL
    if infra_warnings:
        has_warning = True
    
    # Clasificación final
    if has_critical:
        # CRITICAL solo por errores de negocio
        return ("CRITICAL", 2)
    elif has_warning:
        # WARNING por advertencias o errores técnicos
        return ("WARNING", 1)
    else:
        return ("OK", 0)


def generate_markdown_report(
    timestamp: datetime,
    summary_status: str,
    coverage_stats: dict,
    checks: list,
    global_health: dict,
    unregistered_used: list,
    critical_impacts: dict,
    infra_warnings: list
) -> str:
    """Genera reporte en Markdown."""
    report = []
    
    # Header
    report.append("# CT4 Ops Health — Reporte de Auditoría Automática\n")
    report.append(f"**Fecha:** {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**Estado:** {summary_status}\n")
    report.append("\n---\n")
    
    # Resumen Ejecutivo
    report.append("## Resumen Ejecutivo\n")
    report.append(f"- **Estado Global:** {global_health['global_status']}\n")
    report.append(f"- **Errores:** {global_health['error_count']}\n")
    report.append(f"- **Advertencias:** {global_health['warn_count']}\n")
    report.append(f"- **OK:** {global_health['ok_count']}\n")
    report.append(f"- **Objetos Descubiertos:** {coverage_stats['discovered_objects']}\n")
    report.append(f"- **Objetos Registrados:** {coverage_stats['registered_objects']}\n")
    report.append(f"- **Objetos No Registrados:** {len(coverage_stats['unregistered_objects'])}\n")
    report.append(f"- **Objetos Faltantes:** {len(coverage_stats['missing_objects'])}\n")
    report.append("\n---\n")
    
    # Advertencias de Infraestructura (errores técnicos)
    if infra_warnings:
        report.append("## ⚠️ Advertencias de Infraestructura\n\n")
        report.append("Los siguientes errores técnicos fueron detectados (vistas faltantes, errores SQL, etc.).\n")
        report.append("Estos errores **NO** indican problemas de negocio, solo problemas de infraestructura.\n\n")
        for warning in infra_warnings:
            report.append(f"- {warning}\n")
        report.append("\n---\n")
    
    # Checks Fallidos
    failed_checks = [c for c in checks if c['status'] != 'OK']
    if failed_checks:
        report.append("## Checks Fallidos\n\n")
        report.append("| Check | Severidad | Estado | Mensaje |\n")
        report.append("|-------|-----------|--------|----------|\n")
        for check in failed_checks:
            severity_icon = "🔴" if check['severity'] == 'error' else "🟡"
            report.append(
                f"| `{check['check_key']}` | {severity_icon} {check['severity']} | "
                f"{check['status']} | {check['message'][:100]}... |\n"
            )
        report.append("\n---\n")
    
    # Objetos No Registrados
    if coverage_stats['unregistered_objects']:
        report.append("## Objetos en DB No Registrados\n\n")
        report.append("| Schema | Objeto |\n")
        report.append("|--------|--------|\n")
        for obj in coverage_stats['unregistered_objects'][:20]:  # Limitar a 20
            report.append(f"| `{obj['schema_name']}` | `{obj['object_name']}` |\n")
        if len(coverage_stats['unregistered_objects']) > 20:
            report.append(f"\n*... y {len(coverage_stats['unregistered_objects']) - 20} más*\n")
        report.append("\n---\n")
    
    # Objetos Usados Pero No Registrados
    if unregistered_used:
        report.append("## Objetos Usados Pero No Registrados\n\n")
        report.append("| Schema | Objeto | Contexto de Uso |\n")
        report.append("|--------|--------|-----------------|\n")
        for obj in unregistered_used[:20]:  # Limitar a 20
            report.append(
                f"| `{obj['schema_name']}` | `{obj['object_name']}` | "
                f"`{obj['usage_context']}` |\n"
            )
        if len(unregistered_used) > 20:
            report.append(f"\n*... y {len(unregistered_used) - 20} más*\n")
        report.append("\n---\n")
    
    # Impactos Críticos
    has_impacts = False
    if critical_impacts['raw_stale_affecting_critical']:
        has_impacts = True
        report.append("## RAW Stale Afectando MVs Críticas\n\n")
        report.append("| RAW Source | MV Crítica | Días de Retraso |\n")
        report.append("|------------|------------|-----------------|\n")
        for impact in critical_impacts['raw_stale_affecting_critical']:
            report.append(
                f"| `{impact['raw_schema']}.{impact['raw_name']}` | "
                f"`{impact['mv_schema']}.{impact['mv_name']}` | "
                f"{impact['days_lag']:.1f} días |\n"
            )
        report.append("\n---\n")
    
    if critical_impacts['mv_refresh_failed']:
        has_impacts = True
        report.append("## MVs con Refresh Fallido\n\n")
        report.append("| Schema | MV | Error | Último Intento |\n")
        report.append("|--------|----|-------|----------------|\n")
        for impact in critical_impacts['mv_refresh_failed']:
            error_msg = impact['error_message'][:50] + "..." if impact['error_message'] else "N/A"
            report.append(
                f"| `{impact['schema_name']}` | `{impact['mv_name']}` | "
                f"`{error_msg}` | {impact['refreshed_at']} |\n"
            )
        report.append("\n---\n")
    
    if critical_impacts['mv_not_populated']:
        has_impacts = True
        report.append("## MVs No Pobladas\n\n")
        report.append("| Schema | MV |\n")
        report.append("|--------|----|\n")
        for impact in critical_impacts['mv_not_populated']:
            report.append(f"| `{impact['schema_name']}` | `{impact['mv_name']}` |\n")
        report.append("\n---\n")
    
    if critical_impacts['critical_mv_no_refresh_log']:
        has_impacts = True
        report.append("## MVs Críticas Sin Historial de Refresh\n\n")
        report.append("| Schema | MV |\n")
        report.append("|--------|----|\n")
        for impact in critical_impacts['critical_mv_no_refresh_log']:
            report.append(f"| `{impact['schema_name']}` | `{impact['mv_name']}` |\n")
        report.append("\n---\n")
    
    # Recomendaciones
    report.append("## Recomendaciones Automáticas\n\n")
    
    if failed_checks:
        report.append("### Acciones Inmediatas:\n\n")
        for check in [c for c in failed_checks if c['severity'] == 'error']:
            report.append(f"- **{check['check_key']}**: {check['message']}\n")
            if check.get('drilldown_url'):
                report.append(f"  - Ver detalles: {check['drilldown_url']}\n")
        report.append("\n")
    
    if unregistered_used:
        report.append("### Objetos a Registrar:\n\n")
        report.append("Ejecutar discovery y poblar registry para cubrir objetos usados:\n\n")
        for obj in unregistered_used[:10]:
            report.append(f"- `{obj['schema_name']}.{obj['object_name']}` (usado en: {obj['usage_context']})\n")
        report.append("\n")
    
    if coverage_stats['unregistered_objects']:
        report.append("### Objetos a Revisar:\n\n")
        report.append("Los siguientes objetos existen en DB pero no están en registry:\n\n")
        for obj in coverage_stats['unregistered_objects'][:10]:
            report.append(f"- `{obj['schema_name']}.{obj['object_name']}`\n")
        report.append("\n")
    
    if not failed_checks and not unregistered_used and not coverage_stats['unregistered_objects']:
        report.append("✅ **Sistema saludable.** No se requieren acciones inmediatas.\n")
    
    report.append("\n---\n")
    report.append(f"\n*Reporte generado automáticamente el {timestamp.strftime('%Y-%m-%d %H:%M:%S')}*\n")
    
    return "".join(report)


def json_serializer(obj):
    """
    Serializador personalizado para JSON que convierte tipos no serializables.
    
    Convierte Decimal a float, datetime a string ISO, etc.
    """
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def generate_json_report(
    timestamp: datetime,
    summary_status: str,
    coverage_stats: dict,
    checks: list,
    global_health: dict,
    unregistered_used: list,
    critical_impacts: dict,
    infra_warnings: list
) -> dict:
    """Genera reporte en JSON."""
    return {
        "timestamp": timestamp.isoformat(),
        "summary": {
            "status": summary_status,
            "global_status": global_health["global_status"],
            "error_count": global_health["error_count"],
            "warn_count": global_health["warn_count"],
            "ok_count": global_health["ok_count"]
        },
        "coverage": {
            "discovered_objects": coverage_stats["discovered_objects"],
            "registered_objects": coverage_stats["registered_objects"],
            "unregistered_count": len(coverage_stats["unregistered_objects"]),
            "missing_count": len(coverage_stats["missing_objects"])
        },
        "checks": checks,
        "uncovered_objects": coverage_stats["unregistered_objects"],
        "missing_objects": coverage_stats["missing_objects"],
        "unregistered_used_objects": unregistered_used,
        "critical_impacts": critical_impacts,
        "infra_warnings": infra_warnings
    }


def main():
    """Función principal del script de auditoría."""
    timestamp = datetime.now()
    
    print_header("CT4 OPS HEALTH — AUDITORÍA AUTOMÁTICA")
    print(f"Inicio: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Fase 1: Discovery
    print_header("FASE 1: DISCOVERY")
    
    if not run_discovery_script("discovery_objects.py"):
        print_error("Discovery de objetos falló. Abortando.")
        sys.exit(2)
    
    if not run_discovery_script("discovery_dependencies.py"):
        print_error("Discovery de dependencias falló. Abortando.")
        sys.exit(2)
    
    if not run_discovery_script("discovery_usage_backend.py"):
        print_error("Discovery de uso falló. Abortando.")
        sys.exit(2)
    
    # Fase 2: Registry
    print_header("FASE 2: SOURCE REGISTRY")
    
    if not run_populate_registry():
        print_error("Población de registry falló. Abortando.")
        sys.exit(2)
    
    # Fase 3: Validaciones
    print_header("FASE 3: VALIDACIONES")
    
    # Crear engine (no conexión) - cada query usará su propia conexión aislada
    engine = create_engine(DATABASE_URL)
    
    # Acumulador de advertencias de infraestructura (errores técnicos)
    all_infra_warnings = []
    
    try:
        # Coverage - query aislada
        print("\n### A. Coverage Real")
        coverage_stats, infra_warnings = get_coverage_stats(engine)
        all_infra_warnings.extend(infra_warnings)
        
        # Health Checks - query aislada
        print("\n### B. Health Checks")
        checks, infra_warnings = get_health_checks(engine)
        all_infra_warnings.extend(infra_warnings)
        
        # Global Health - query aislada
        print("\n### C. Estado Global")
        global_health, infra_warnings = get_global_health(engine)
        all_infra_warnings.extend(infra_warnings)
        
        # Uso sin registro - queries aisladas
        print("\n### D. Objetos Usados Sin Registro")
        unregistered_used, infra_warnings = get_unregistered_used_objects(engine)
        all_infra_warnings.extend(infra_warnings)
        
        # Impactos críticos - queries aisladas
        print("\n### E. Impactos Críticos")
        critical_impacts, infra_warnings = get_critical_impacts(engine)
        all_infra_warnings.extend(infra_warnings)
        
        # Clasificar estado (infra_warnings no hacen CRITICAL, solo WARNING)
        summary_status, exit_code = classify_status(checks, global_health, all_infra_warnings)
        
        # Fase 4: Reportes
        print_header("FASE 4: GENERACIÓN DE REPORTES")
        
        # Generar Markdown
        md_report = generate_markdown_report(
            timestamp, summary_status, coverage_stats, checks,
            global_health, unregistered_used, critical_impacts, all_infra_warnings
        )
        
        # Generar reportes en docs/backend/
        docs_dir = Path(__file__).parent.parent.parent / "docs" / "backend"
        docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Generar Markdown
        md_file = docs_dir / "OPS_HEALTH_AUDIT_REPORT.md"
        with open(md_file, "w", encoding="utf-8") as f:
            f.write(md_report)
        print_success(f"Reporte Markdown generado: {md_file}")
        
        # Generar JSON
        json_report = generate_json_report(
            timestamp, summary_status, coverage_stats, checks,
            global_health, unregistered_used, critical_impacts, all_infra_warnings
        )
        
        json_file = docs_dir / "OPS_HEALTH_AUDIT_REPORT.json"
        with open(json_file, "w", encoding="utf-8") as f:
            # Serializar con conversión de Decimal a float
            json.dump(json_report, f, indent=2, ensure_ascii=False, default=json_serializer)
        print_success(f"Reporte JSON generado: {json_file}")
        
        # Resumen final
        print_header("RESUMEN FINAL")
        
        status_color = Colors.ERROR if exit_code == 2 else (Colors.WARN if exit_code == 1 else Colors.OK)
        print(f"{status_color}{Colors.BOLD}Estado: {summary_status}{Colors.RESET}\n")
        
        print(f"  Errores: {global_health['error_count']}")
        print(f"  Advertencias: {global_health['warn_count']}")
        print(f"  OK: {global_health['ok_count']}")
        print(f"\n  Objetos descubiertos: {coverage_stats['discovered_objects']}")
        print(f"  Objetos registrados: {coverage_stats['registered_objects']}")
        print(f"  Objetos no registrados: {len(coverage_stats['unregistered_objects'])}")
        print(f"  Objetos usados sin registro: {len(unregistered_used)}")
        
        if all_infra_warnings:
            print(f"\n  Advertencias de infraestructura: {len(all_infra_warnings)}")
            print("    (Errores técnicos que no afectan el estado de negocio)")
        
        if exit_code == 2:
            print_error("\n⚠️  SISTEMA EN ESTADO CRÍTICO")
            print("   Revisar reportes para acciones inmediatas.")
        elif exit_code == 1:
            print_warning("\n⚠️  SISTEMA CON ADVERTENCIAS")
            print("   Revisar reportes para recomendaciones.")
        else:
            print_success("\n✅ SISTEMA SALUDABLE")
        
        print(f"\nReportes disponibles en:")
        print(f"  - {md_file}")
        print(f"  - {json_file}\n")
        
        sys.exit(exit_code)
    
    except Exception as e:
        print_error(f"Error en validaciones: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()

