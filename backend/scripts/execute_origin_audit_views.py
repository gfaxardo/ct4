"""
Script para ejecutar las vistas SQL de auditoría de origen.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db import SessionLocal

def execute_sql_file(file_path: Path):
    """Ejecuta un archivo SQL"""
    db = SessionLocal()
    try:
        sql_content = file_path.read_text(encoding='utf-8')
        # Dividir por ; y ejecutar cada statement
        statements = [s.strip() for s in sql_content.split(';') if s.strip()]
        for statement in statements:
            if statement:
                try:
                    db.execute(text(statement))
                    print(f"[OK] Ejecutado: {statement[:50]}...")
                except Exception as e:
                    # Si es "already exists", está bien
                    if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
                        print(f"[SKIP] Ya existe: {statement[:50]}...")
                    else:
                        print(f"[ERROR] Error: {str(e)}")
                        print(f"  Statement: {statement[:100]}...")
        db.commit()
        print(f"\n[OK] Archivo {file_path.name} ejecutado exitosamente")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] Error ejecutando {file_path.name}: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    
    views = [
        project_root / "sql" / "ops" / "v_identity_origin_audit.sql",
        project_root / "sql" / "ops" / "v_identity_origin_alerts.sql",
    ]
    
    for view_file in views:
        if view_file.exists():
            print(f"\nEjecutando {view_file.name}...")
            execute_sql_file(view_file)
        else:
            print(f"[WARN] Archivo no encontrado: {view_file}")

