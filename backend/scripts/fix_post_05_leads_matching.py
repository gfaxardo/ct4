#!/usr/bin/env python3
"""
Script para ejecutar matching/ingestion de leads post-05/01/2026.
"""

import sys
import os
import requests
import json
from pathlib import Path
from datetime import date

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

def main():
    """Ejecuta matching para leads post-05."""
    base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    print("=" * 80)
    print("FIX: Matching de Leads Post-05/01/2026")
    print("=" * 80)
    print()
    
    # 1. Ejecutar ingestion/matching
    print("1. Ejecutando ingestion/matching para leads post-05...")
    print(f"   Endpoint: {base_url}/api/v1/identity/run")
    print()
    
    payload = {
        "source_tables": ["module_ct_cabinet_leads"],
        "scope_date_from": "2026-01-06",
        "scope_date_to": "2026-01-10",
        "incremental": True,
        "refresh_index": False
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/v1/identity/run",
            json=payload,
            timeout=300  # 5 minutos timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   OK: Job iniciado")
            print(f"   Run ID: {result.get('id', 'N/A')}")
            print(f"   Status: {result.get('status', 'N/A')}")
            print()
            print("   NOTA: El job se ejecuta en background. Verifica el estado con:")
            print(f"   GET {base_url}/api/v1/identity/runs/{result.get('id')}")
        else:
            print(f"   ERROR: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ERROR al conectar con API: {e}")
        print()
        print("   ALTERNATIVA: Ejecutar manualmente desde el código:")
        print("   from app.services.ingestion import IngestionService")
        print("   service = IngestionService(db)")
        print("   service.run_ingestion(")
        print("       source_tables=['module_ct_cabinet_leads'],")
        print("       scope_date_from=date(2026, 1, 6),")
        print("       scope_date_to=date(2026, 1, 10),")
        print("       incremental=True")
        print("   )")
    
    print()
    print("=" * 80)
    print("2. Verificando resultados...")
    print("=" * 80)
    print()
    print("   Ejecuta el script de diagnóstico nuevamente después de que el job termine:")
    print("   python backend/scripts/diagnose_post_05_leads.py")
    print()
    print("   O verifica directamente en la base de datos:")
    print("   SELECT COUNT(*) FROM canon.identity_links")
    print("   WHERE source_table = 'module_ct_cabinet_leads'")
    print("   AND source_pk IN (")
    print("       SELECT COALESCE(external_id::text, id::text)")
    print("       FROM public.module_ct_cabinet_leads")
    print("       WHERE lead_created_at::date > '2026-01-05'")
    print("   )")

if __name__ == "__main__":
    main()
