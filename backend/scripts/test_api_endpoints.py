#!/usr/bin/env python3
"""
Test de endpoints API de Scout Attribution
"""

import sys
import io
import requests
import json
from pathlib import Path

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configurar URL base
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1/scouts"

def test_endpoint(endpoint, method="GET", data=None):
    """Test un endpoint"""
    url = f"{API_BASE}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=10)
        else:
            print(f"[SKIP] Método {method} no soportado")
            return False
        
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] {endpoint}: {json.dumps(result, indent=2, default=str)[:200]}...")
            return True
        else:
            print(f"[ERROR] {endpoint}: Status {response.status_code} - {response.text[:200]}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"[SKIP] {endpoint}: Backend no está corriendo en {BASE_URL}")
        return None
    except Exception as e:
        print(f"[ERROR] {endpoint}: {str(e)}")
        return False

def main():
    print("="*80)
    print("TEST: Endpoints API de Scout Attribution")
    print("="*80)
    print(f"URL Base: {BASE_URL}\n")
    
    results = {}
    
    # Test 1: Métricas instantáneas
    print("\n1. GET /attribution/metrics")
    results['metrics'] = test_endpoint("/attribution/metrics")
    
    # Test 2: Métricas diarias
    print("\n2. GET /attribution/metrics/daily?days=30")
    results['metrics_daily'] = test_endpoint("/attribution/metrics/daily?days=30")
    
    # Test 3: Conflictos
    print("\n3. GET /attribution/conflicts?page=1&page_size=10")
    results['conflicts'] = test_endpoint("/attribution/conflicts?page=1&page_size=10")
    
    # Test 4: Backlog
    print("\n4. GET /attribution/backlog")
    results['backlog'] = test_endpoint("/attribution/backlog")
    
    # Test 5: Estado del job
    print("\n5. GET /attribution/job-status")
    results['job_status'] = test_endpoint("/attribution/job-status")
    
    # Test 6: Cobranza Yango
    print("\n6. GET /liquidation/base?page=1&page_size=10")
    results['yango_base'] = test_endpoint("/liquidation/base?page=1&page_size=10")
    
    # Resumen
    print("\n" + "="*80)
    print("RESUMEN")
    print("="*80)
    
    success_count = sum(1 for v in results.values() if v is True)
    skip_count = sum(1 for v in results.values() if v is None)
    error_count = sum(1 for v in results.values() if v is False)
    
    print(f"Exitosos: {success_count}")
    print(f"Omitidos (backend no corriendo): {skip_count}")
    print(f"Errores: {error_count}")
    
    if skip_count > 0:
        print(f"\n⚠️ Backend no está corriendo. Inicia con: cd backend && uvicorn app.main:app --reload")
    
    if success_count == len([v for v in results.values() if v is not None]):
        print("\n[OK] Todos los endpoints funcionando correctamente")
        return 0
    else:
        print("\n[WARN] Algunos endpoints tienen errores")
        return 1

if __name__ == "__main__":
    sys.exit(main())

