#!/usr/bin/env python3
"""
Script para crear la vista ops.v_cabinet_financial_14d
y ejecutar el script de verificación
"""

import os
import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from app.config import settings

def execute_sql_file(engine, sql_file_path):
    """Ejecuta un archivo SQL completo"""
    print(f"Ejecutando: {sql_file_path}")
    
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Dividir por punto y coma para ejecutar cada statement
    statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
    
    with engine.connect() as conn:
        for statement in statements:
            if statement:
                try:
                    conn.execute(text(statement))
                    conn.commit()
                except Exception as e:
                    # Algunos errores pueden ser normales (como DROP IF EXISTS cuando no existe)
                    if "does not exist" not in str(e).lower():
                        print(f"  ⚠️  Advertencia: {e}")
        conn.commit()
    
    print(f"✅ Archivo ejecutado: {sql_file_path}")

def main():
    print("=" * 70)
    print("Ejecutando vista ops.v_cabinet_financial_14d")
    print("=" * 70)
    
    # Crear engine
    engine = create_engine(settings.database_url)
    
    # Ruta del archivo SQL de la vista
    sql_file = project_root / "sql" / "ops" / "v_cabinet_financial_14d.sql"
    
    if not sql_file.exists():
        print(f"❌ ERROR: No se encontró el archivo SQL: {sql_file}")
        sys.exit(1)
    
    try:
        # Ejecutar la vista
        execute_sql_file(engine, sql_file)
        
        # Verificar que la vista existe
        print("\nVerificando vista...")
        with engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM ops.v_cabinet_financial_14d LIMIT 1"))
            count = result.scalar()
            print(f"✅ Vista verificada. Existe y es accesible. (Filas: {count})")
        
        print("\n" + "=" * 70)
        print("✅ Proceso completado exitosamente!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        engine.dispose()

if __name__ == "__main__":
    main()


