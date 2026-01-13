"""
Tests para endpoints de ops/payments/driver-matrix
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ops_driver_matrix_endpoint_returns_200():
    """Test que /api/v1/ops/payments/driver-matrix retorna 200 y JSON válido"""
    response = client.get("/api/v1/ops/payments/driver-matrix?limit=10&offset=0")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verificar estructura de respuesta
    assert "meta" in data
    assert "data" in data
    
    # Verificar meta
    assert "limit" in data["meta"]
    assert "offset" in data["meta"]
    assert "returned" in data["meta"]
    assert "total" in data["meta"]
    
    # Verificar que data es una lista
    assert isinstance(data["data"], list)
    
    # Verificar que returned coincide con el tamaño de data
    assert data["meta"]["returned"] == len(data["data"])


def test_ops_driver_matrix_only_pending_returns_200():
    """Test que only_pending=true no rompe y retorna 200"""
    response = client.get("/api/v1/ops/payments/driver-matrix?only_pending=true&limit=10&offset=0")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verificar estructura
    assert "meta" in data
    assert "data" in data
    
    # Verificar que meta tiene los campos esperados
    assert "total" in data["meta"]
    assert "returned" in data["meta"]


def test_ops_driver_matrix_with_filters():
    """Test que los filtros funcionan correctamente"""
    # Test con origin_tag
    response = client.get("/api/v1/ops/payments/driver-matrix?origin_tag=cabinet&limit=10&offset=0")
    assert response.status_code == 200
    
    # Test con week_start_from y week_start_to
    response = client.get("/api/v1/ops/payments/driver-matrix?week_start_from=2025-01-01&week_start_to=2025-12-31&limit=10&offset=0")
    assert response.status_code == 200
    
    # Test con order
    response = client.get("/api/v1/ops/payments/driver-matrix?order=lead_date_desc&limit=10&offset=0")
    assert response.status_code == 200


def test_ops_driver_matrix_invalid_origin_tag():
    """Test que origin_tag inválido retorna 400"""
    response = client.get("/api/v1/ops/payments/driver-matrix?origin_tag=invalid&limit=10&offset=0")
    assert response.status_code == 400


def test_ops_driver_matrix_pagination():
    """Test que la paginación funciona correctamente"""
    # Primera página
    response1 = client.get("/api/v1/ops/payments/driver-matrix?limit=10&offset=0")
    assert response1.status_code == 200
    data1 = response1.json()
    
    # Segunda página
    response2 = client.get("/api/v1/ops/payments/driver-matrix?limit=10&offset=10")
    assert response2.status_code == 200
    data2 = response2.json()
    
    # Verificar que las páginas tienen los offsets correctos
    assert data1["meta"]["offset"] == 0
    assert data2["meta"]["offset"] == 10
    assert data1["meta"]["limit"] == 10
    assert data2["meta"]["limit"] == 10





