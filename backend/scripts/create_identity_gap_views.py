"""Script para crear las vistas de Identity Gap"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db import engine
from sqlalchemy import text
from pathlib import Path

def execute_sql_file(file_path: Path):
    """Ejecuta un archivo SQL"""
    with open(file_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    
    with engine.connect() as conn:
        # Primero ejecutar el CREATE VIEW completo (hasta el primer ; después de CREATE)
        # Luego ejecutar los COMMENTs
        lines = sql.split('\n')
        create_view_sql = []
        comment_sqls = []
        in_create = False
        
        for line in lines:
            if line.strip().startswith('CREATE') or line.strip().startswith('CREATE OR REPLACE'):
                in_create = True
                create_view_sql.append(line)
            elif in_create:
                create_view_sql.append(line)
                if line.strip().endswith(';'):
                    # Fin del CREATE VIEW
                    create_view_sql_str = '\n'.join(create_view_sql)
                    try:
                        conn.execute(text(create_view_sql_str))
                        conn.commit()
                        print(f"OK Vista creada")
                    except Exception as e:
                        print(f"ERROR creando vista: {e}")
                        conn.rollback()
                    in_create = False
                    create_view_sql = []
            elif line.strip().startswith('COMMENT'):
                comment_sqls.append(line)
        
        # Ejecutar COMMENTs
        for comment_line in comment_sqls:
            if comment_line.strip():
                try:
                    conn.execute(text(comment_line))
                    conn.commit()
                except Exception as e:
                    # Los COMMENTs pueden fallar si la vista no existe, pero eso es OK
                    pass

def main():
    base_path = Path(__file__).parent.parent.parent / "backend" / "sql" / "ops"
    
    views = [
        "v_identity_gap_analysis.sql",
        "v_identity_gap_alerts.sql"
    ]
    
    for view_file in views:
        file_path = base_path / view_file
        if file_path.exists():
            print(f"\nCreando vista desde {view_file}...")
            execute_sql_file(file_path)
        else:
            print(f"ERROR: Archivo no encontrado: {file_path}")
    
    # Verificar que las vistas existen
    print("\nVerificando vistas...")
    with engine.connect() as conn:
        for view_name in ["v_identity_gap_analysis", "v_identity_gap_alerts"]:
            result = conn.execute(text(
                f"SELECT EXISTS (SELECT 1 FROM pg_views WHERE schemaname = 'ops' AND viewname = '{view_name}')"
            ))
            exists = result.fetchone()[0]
            status = "OK" if exists else "ERROR"
            print(f"{status} Vista {view_name}: {'existe' if exists else 'NO existe'}")

if __name__ == "__main__":
    main()
