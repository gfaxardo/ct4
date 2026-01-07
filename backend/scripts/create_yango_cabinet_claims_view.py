#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear la vista ops.v_yango_cabinet_claims_for_collection
Ejecutar desde el directorio backend/ con el venv activado
"""
import os
import sys
from pathlib import Path

# Agregar el directorio app al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

try:
    from app.db import engine
    from sqlalchemy import text
except ImportError as e:
    print("ERROR: No se pueden importar los modulos necesarios.")
    print("   Asegurate de:")
    print("   1. Estar en el directorio backend/")
    print("   2. Tener el entorno virtual activado")
    print("   3. Haber instalado las dependencias: pip install -r requirements.txt")
    print(f"\n   Error especifico: {e}")
    sys.exit(1)

def main():
    # Leer el archivo SQL
    sql_file = backend_dir / "sql" / "ops" / "v_yango_cabinet_claims_for_collection.sql"
    
    if not sql_file.exists():
        print(f"ERROR: No se encontro el archivo SQL en: {sql_file}")
        sys.exit(1)
    
    print(f"Leyendo SQL desde: {sql_file}")
    sql_content = sql_file.read_text(encoding='utf-8')
    
    print("Conectando a la base de datos...")
    try:
        with engine.connect() as conn:
            print("Conectado. Ejecutando SQL...")
            # Ejecutar el SQL
            conn.execute(text(sql_content))
            conn.commit()
            print("Vista creada exitosamente!")
            
            # Verificar que la vista existe
            print("Verificando que la vista existe...")
            check_query = text("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.views 
                    WHERE table_schema = 'ops' 
                    AND table_name = 'v_yango_cabinet_claims_for_collection'
                );
            """)
            result = conn.execute(check_query).scalar()
            
            if result:
                print("Vista verificada correctamente")
            else:
                print("ADVERTENCIA: La vista podria no existir. Verifica manualmente.")
                
    except Exception as e:
        print(f"ERROR al ejecutar SQL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()














