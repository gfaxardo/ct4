"""
Convenciones comunes para scripts del backend.

Uso de base de datos:
- Necesitas una sesión (consultas ORM o text()): usa `from app.core.db import SessionLocal` y
  `db = SessionLocal()`; cierra con `db.close()` en un bloque finally.
- Necesitas la URL (subprocess psql, etc.): usa `from app.core.db import get_db_url`.
- Config (database_url, etc.): usa `from app.core.config import settings` y `settings.database_url`.

No crear engine/sessionmaker propios; usar app.db para reutilizar pool y configuración.
"""
from contextlib import contextmanager
from typing import Generator

# Importar app después de que el script haya añadido backend al path (sys.path.insert)
@contextmanager
def get_session() -> Generator:
    """Context manager que proporciona una sesión de DB y la cierra al salir."""
    from app.core.db import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
