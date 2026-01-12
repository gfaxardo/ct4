"""Script para corregir la versión de Alembic directamente"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db import engine
from sqlalchemy import text

def main():
    with engine.connect() as conn:
        # Verificar versión actual
        result = conn.execute(text("SELECT version_num FROM alembic_version"))
        current = result.fetchone()
        print(f"Versión actual en DB: {current[0] if current else 'None'}")
        
        # Actualizar a 013_identity_origin si está en 014_driver_orphan_quarantine
        if current and current[0] == '014_driver_orphan_quarantine':
            conn.execute(text("UPDATE alembic_version SET version_num = '013_identity_origin' WHERE version_num = '014_driver_orphan_quarantine'"))
            conn.commit()
            print("✅ Actualizado a 013_identity_origin")
            
            # Verificar
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            new_version = result.fetchone()
            print(f"Versión nueva: {new_version[0] if new_version else 'None'}")
        else:
            print(f"⚠️  Versión actual es {current[0] if current else 'None'}, no se requiere actualización")

if __name__ == "__main__":
    main()
