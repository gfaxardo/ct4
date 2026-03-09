"""
Fixtures compartidas para los tests del backend.

- client: TestClient de FastAPI (tests de API sin levantar servidor).
- db_session: Sesión de base de datos para tests de integración (requiere DB).
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.db import SessionLocal, Base, engine


@pytest.fixture
def client():
    """Cliente HTTP para tests de endpoints. No requiere base de datos si el endpoint usa mocks."""
    return TestClient(app)


@pytest.fixture
def db_session():
    """
    Sesión de base de datos para tests que tocan la DB.
    Crea las tablas si no existen y cierra la sesión al final.
    Requiere DATABASE_URL configurada (ej. .env o variable de entorno).
    """
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
