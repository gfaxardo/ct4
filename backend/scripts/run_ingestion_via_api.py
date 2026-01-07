#!/usr/bin/env python3
"""
Script para ejecutar ingesta de identidad vía API.
Usa requests para llamar al endpoint directamente.
"""

import requests
import json
from datetime import date, timedelta
import sys

API_BASE_URL = "http://localhost:8000/api/v1"

def check_last_run():
    """Verifica la última corrida."""
    try:
        response = requests.get(f"{API_BASE_URL}/identity/runs?limit=1")
        if response.status_code == 200:
            data = response.json()
            if data.get("runs") and len(data["runs"]) > 0:
                last_run = data["runs"][0]
                if last_run.get("status") == "COMPLETED":
                    return last_run
    except Exception as e:
        print(f"Error verificando última corrida: {e}")
    return None

def run_ingestion(date_from=None, date_to=None):
    """Ejecuta ingesta de identidad."""
    params = {}
    if date_from:
        params["date_from"] = str(date_from)
    if date_to:
        params["date_to"] = str(date_to)
    if not date_from and not date_to:
        params["incremental"] = "true"
    
    try:
        print(f"Ejecutando ingesta con parámetros: {params}")
        response = requests.post(f"{API_BASE_URL}/identity/run", params=params)
        
        if response.status_code == 200:
            data = response.json()
            print(f"[OK] Ingesta iniciada: run_id={data.get('id')}, status={data.get('status')}")
            return data
        else:
            print(f"[ERROR] Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"[ERROR] Error ejecutando ingesta: {e}")
        return None

def main():
    """Función principal."""
    print("=" * 60)
    print("Ejecutando Ingesta de Identidad")
    print("=" * 60)
    
    # Verificar última corrida
    last_run = check_last_run()
    
    if last_run:
        scope_to = last_run.get("scope_date_to")
        if scope_to:
            date_from = date.fromisoformat(scope_to)
            date_to = date.today()
            print(f"Modo incremental: desde {date_from} hasta {date_to}")
            run_ingestion(date_from=date_from, date_to=date_to)
        else:
            print("Modo incremental: sin scope_date_to, usando incremental=True")
            run_ingestion()
    else:
        # Primera corrida: últimos 30 días
        date_to = date.today()
        date_from = date_to - timedelta(days=30)
        print(f"Primera corrida: desde {date_from} hasta {date_to}")
        run_ingestion(date_from=date_from, date_to=date_to)
    
    print("\n[OK] Proceso completado. Verificar logs del servidor para detalles.")

if __name__ == "__main__":
    main()

