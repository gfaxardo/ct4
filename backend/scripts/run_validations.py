#!/usr/bin/env python
"""
Script para ejecutar todas las validaciones en orden.
Ejecuta:
1. verify_source_pk_consistency
2. seed_kpi_red_queue
3. recover_kpi_red_leads (limit 1000)
4. validate_kpi_red_impact
5. verify_kpi_red_drain
6. check_origin_missing
"""
import sys
import subprocess
from pathlib import Path

def run_command(cmd, description):
    """Ejecuta un comando y muestra el output"""
    print("=" * 80)
    print(f"EJECUTANDO: {description}")
    print("=" * 80)
    print(f"Comando: {' '.join(cmd)}")
    print()
    
    try:
        result = subprocess.run(
            cmd,
            cwd=str(Path(__file__).parent.parent),
            capture_output=True,
            text=True,
            check=False
        )
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        
        print()
        print(f"Exit code: {result.returncode}")
        print()
        
        return result.returncode == 0
    except Exception as e:
        print(f"[ERROR] Error ejecutando comando: {e}", file=sys.stderr)
        return False

def main():
    """Ejecuta todas las validaciones en orden"""
    print("=" * 80)
    print("EJECUTANDO VALIDACIONES COMPLETAS")
    print("=" * 80)
    print()
    
    validations = [
        (["python", "-m", "scripts.verify_source_pk_consistency"], "Verificar consistencia source_pk"),
        (["python", "-m", "jobs.seed_kpi_red_queue"], "Sembrar cola KPI rojo"),
        (["python", "-m", "jobs.recover_kpi_red_leads", "--limit", "1000"], "Recuperar leads KPI rojo (limit 1000)"),
        (["python", "-m", "scripts.validate_kpi_red_impact", "--limit", "1000"], "Validar impacto real"),
        (["python", "-m", "scripts.verify_kpi_red_drain", "--n", "100"], "Verificar drenaje (guardrail)"),
        (["python", "-m", "scripts.check_origin_missing"], "Verificar ORIGIN_MISSING = 0"),
    ]
    
    results = {}
    for cmd, description in validations:
        success = run_command(cmd, description)
        results[description] = success
        if not success:
            print(f"[WARNING] Validacion fallida: {description}")
            print()
    
    # Resumen final
    print("=" * 80)
    print("RESUMEN FINAL")
    print("=" * 80)
    for description, success in results.items():
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {description}")
    print()
    
    all_passed = all(results.values())
    if all_passed:
        print("[OK] Todas las validaciones pasaron")
        return 0
    else:
        print("[ERROR] Algunas validaciones fallaron")
        return 1

if __name__ == "__main__":
    sys.exit(main())
