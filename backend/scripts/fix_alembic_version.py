"""Script para corregir la versión de Alembic en la base de datos"""
from app.db import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Verificar versión actual
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    current = result.fetchone()
    print(f"Versión actual en DB: {current[0] if current else 'None'}")
    
    # Actualizar a 013_identity_origin si está en 014_driver_orphan_quarantine
    if current and current[0] == '014_driver_orphan_quarantine':
        conn.execute(text("UPDATE alembic_version SET version_num = '013_identity_origin'"))
        conn.commit()
        print("✅ Actualizado a 013_identity_origin")
    else:
        print(f"⚠️  Versión actual es {current[0] if current else 'None'}, no se requiere actualización")
