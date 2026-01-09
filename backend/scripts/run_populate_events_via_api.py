#!/usr/bin/env python3
"""
Script para poblar lead_events vía API.
Usa requests para llamar al endpoint directamente.
"""

import requests
import json
from datetime import date, timedelta
import sys

API_BASE_URL = "http://localhost:8000/api/v1"

def populate_events(date_from=None, date_to=None):
    """Pobla lead_events desde las tablas fuente."""
    data = {
        "source_tables": ["module_ct_scouting_daily", "module_ct_cabinet_leads"]
    }
    
    if date_from:
        data["date_from"] = str(date_from)
    if date_to:
        data["date_to"] = str(date_to)
    
    try:
        print(f"Poblando eventos con parámetros: {data}")
        response = requests.post(
            f"{API_BASE_URL}/attribution/populate-events",
            json=data
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"[OK] Eventos poblados exitosamente")
            print(f"Stats: {json.dumps(result.get('stats', {}), indent=2)}")
            return True
        else:
            print(f"[ERROR] Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] Error ejecutando populate_events: {e}")
        return False

def main():
    """Función principal."""
    print("=" * 60)
    print("Poblando lead_events")
    print("=" * 60)
    
    # Usar últimos 30 días por defecto
    date_to = date.today()
    date_from = date_to - timedelta(days=30)
    
    print(f"Rango de fechas: {date_from} hasta {date_to}")
    
    success = populate_events(date_from=date_from, date_to=date_to)
    
    if success:
        print("\n[OK] Proceso completado. Verificar logs del servidor para detalles.")
        return 0
    else:
        print("\n[ERROR] El proceso falló.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)



