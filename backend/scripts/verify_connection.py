#!/usr/bin/env python3
"""Verificar conexión a base de datos"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.database_url)
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1"))
        result.scalar()
        print("[OK] Conexion a base de datos OK")
        print(f"  URL: {settings.database_url.split('@')[-1] if '@' in settings.database_url else 'configurada'}")
except Exception as e:
    print(f"[ERROR] Error de conexion: {e}")
    sys.exit(1)

