#!/usr/bin/env python3
"""
Script para obtener el payload JSON de un driver específico desde el endpoint driver-matrix
Útil para debug del problema de grano temporal M1/M5
"""
import requests
import json
import sys
from typing import Optional

API_BASE_URL = "http://localhost:8000"

def get_driver_matrix_payload(driver_id: Optional[str] = None, limit: int = 200):
    """
    Obtiene el payload JSON del endpoint driver-matrix
    Si se proporciona driver_id, filtra por ese driver
    """
    url = f"{API_BASE_URL}/api/v1/ops/payments/driver-matrix"
    params = {"limit": limit, "offset": 0}
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if driver_id:
            # Filtrar por driver_id
            filtered_data = [
                row for row in data.get("data", [])
                if row.get("driver_id") == driver_id
            ]
            if filtered_data:
                return {
                    "meta": data.get("meta"),
                    "data": filtered_data
                }
            else:
                print(f"No se encontró driver_id: {driver_id}")
                return None
        else:
            return data
    except requests.exceptions.RequestException as e:
        print(f"Error al obtener datos: {e}")
        return None

if __name__ == "__main__":
    driver_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    payload = get_driver_matrix_payload(driver_id)
    
    if payload:
        print(json.dumps(payload, indent=2, default=str))
    else:
        print("No se pudo obtener el payload")



