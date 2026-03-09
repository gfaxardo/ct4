#!/usr/bin/env python3
"""
Muestra cómo está configurada la base de datos y prueba la conexión.

Uso (desde backend/):
  python scripts/verify_connection.py
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# ---- 1. Mostrar de dónde sale la configuración ----
env_file = project_root / ".env"
print("--- Configuración de base de datos ---")
print(f"  Archivo .env existe: {env_file.exists()}  (ruta: {env_file})")
db_url_raw = os.getenv("DATABASE_URL")
if db_url_raw:
    print("  DATABASE_URL: definida por variable de entorno")
else:
    print("  DATABASE_URL: no en entorno → se usa default de app/config.py o .env")

from app.core.config import settings


def _mask_url(url: str) -> str:
    """Oculta contraseña en la URL para mostrarla en pantalla."""
    if not url:
        return "(vacía)"
    if "@" in url and "://" in url:
        try:
            pre, post = url.split("@", 1)
            scheme, rest = pre.split("://", 1)
            if ":" in rest:
                user, _ = rest.rsplit(":", 1)
                return f"{scheme}://{user}:****@{post}"
            return f"{scheme}://****@{post}"
        except Exception:
            pass
    return url[:80] + ("..." if len(url) > 80 else "")


print(f"  URL usada (contraseña oculta): {_mask_url(settings.database_url)}")
# Extraer host y puerto para referencia
if "@" in settings.database_url:
    try:
        parte = settings.database_url.split("@")[-1]
        host_port = parte.split("/")[0]
        db_name = parte.split("/")[1].split("?")[0] if "/" in parte else "?"
        print(f"  Host:puerto: {host_port}  |  Base de datos: {db_name}")
    except Exception:
        pass
print()

# ---- 2. Probar conexión ----
from sqlalchemy import text
from app.core.db import engine

print("--- Prueba de conexión ---")
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        result.scalar()
    print("  [OK] La base de datos está activa y acepta conexiones.")
except Exception as e:
    print(f"  [ERROR] No se pudo conectar: {e}")
    print()
    print("  Posibles causas:")
    print("  - PostgreSQL no está corriendo (prueba: sudo systemctl status postgresql)")
    print("  - DATABASE_URL incorrecta en backend/.env o en el entorno")
    print("  - Host/puerto/firewall bloqueando la conexión")
    sys.exit(1)

