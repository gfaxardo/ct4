"""
Tests para endpoints de driver-matrix
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_driver_matrix_endpoint_returns_200():
    """Test que /driver-matrix retorna 200 y JSON válido"""
    response = client.get("/api/v1/payments/driver-matrix?page=1&limit=10")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verificar estructura de respuesta
    assert "rows" in data
    assert "meta" in data
    assert "totals" in data
    
    # Verificar meta
    assert "page" in data["meta"]
    assert "limit" in data["meta"]
    assert "total_rows" in data["meta"]
    
    # Verificar totals
    assert "drivers" in data["totals"]
    assert "expected_yango_sum" in data["totals"]
    assert "paid_sum" in data["totals"]
    assert "receivable_sum" in data["totals"]
    assert "expired_count" in data["totals"]
    assert "in_window_count" in data["totals"]
    
    # Verificar que rows es una lista
    assert isinstance(data["rows"], list)


def test_driver_matrix_export_returns_200_and_csv():
    """Test que /driver-matrix/export retorna 200, text/csv y BOM presente"""
    response = client.get("/api/v1/payments/driver-matrix/export")
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    
    # Verificar que el contenido tiene BOM UTF-8 (EF BB BF)
    content_bytes = response.content
    assert len(content_bytes) >= 3, "El contenido debe tener al menos 3 bytes (BOM)"
    
    # Verificar BOM: primeros 3 bytes deben ser EF BB BF
    bom = content_bytes[:3]
    assert bom == b'\xef\xbb\xbf', f"BOM no encontrado. Primeros bytes: {bom.hex()}"
    
    # Verificar que es CSV válido (debe tener headers)
    content_text = content_bytes[3:].decode('utf-8')
    lines = content_text.strip().split('\n')
    assert len(lines) > 0, "CSV debe tener al menos una línea (headers)"
    
    # Verificar que la primera línea contiene headers esperados
    headers = lines[0].split(',')
    assert 'driver_id' in headers or 'driver_id' in content_text, "CSV debe contener columna driver_id"


def test_driver_matrix_with_filters():
    """Test que los filtros funcionan correctamente"""
    # Test con search
    response = client.get("/api/v1/payments/driver-matrix?search=test&page=1&limit=10")
    assert response.status_code == 200
    
    # Test con only_pending
    response = client.get("/api/v1/payments/driver-matrix?only_pending=true&page=1&limit=10")
    assert response.status_code == 200
    
    # Test con week_from y week_to
    response = client.get("/api/v1/payments/driver-matrix?week_from=2025-01-01&week_to=2025-12-31&page=1&limit=10")
    assert response.status_code == 200


def test_driver_matrix_export_with_filters():
    """Test que el export funciona con filtros"""
    response = client.get("/api/v1/payments/driver-matrix/export?only_pending=true")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    
    # Verificar BOM
    content_bytes = response.content
    assert content_bytes[:3] == b'\xef\xbb\xbf'


def test_driver_matrix_pagination():
    """Test que la paginación funciona correctamente"""
    # Primera página
    response1 = client.get("/api/v1/payments/driver-matrix?page=1&limit=10")
    assert response1.status_code == 200
    data1 = response1.json()
    
    # Segunda página
    response2 = client.get("/api/v1/payments/driver-matrix?page=2&limit=10")
    assert response2.status_code == 200
    data2 = response2.json()
    
    # Verificar que las páginas son diferentes (si hay suficientes datos)
    if data1["meta"]["total_rows"] > 10:
        assert data1["meta"]["page"] == 1
        assert data2["meta"]["page"] == 2
        assert len(data1["rows"]) <= 10
        assert len(data2["rows"]) <= 10


