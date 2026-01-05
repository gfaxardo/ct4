#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para crear todas las vistas necesarias para Claims Cabinet
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

def create_view(view_name, sql_file_path):
    """Crea una vista SQL desde un archivo"""
    sql_file = backend_dir / sql_file_path
    
    if not sql_file.exists():
        print(f"ERROR: No se encontro el archivo SQL en: {sql_file}")
        return False
    
    print(f"\n{'='*60}")
    print(f"Creando vista: {view_name}")
    print(f"Archivo: {sql_file}")
    print(f"{'='*60}")
    
    sql_content = sql_file.read_text(encoding='utf-8')
    
    try:
        with engine.connect() as conn:
            print("Ejecutando SQL...")
            conn.execute(text(sql_content))
            conn.commit()
            print(f"Vista {view_name} creada exitosamente!")
            
            # Verificar que la vista existe
            check_query = text("""
                SELECT EXISTS (
                    SELECT 1 
                    FROM information_schema.views 
                    WHERE table_schema = 'ops' 
                    AND table_name = :view_name
                );
            """)
            result = conn.execute(check_query, {"view_name": view_name}).scalar()
            
            if result:
                print(f"Vista {view_name} verificada correctamente")
                return True
            else:
                print(f"ADVERTENCIA: La vista {view_name} podria no existir.")
                return False
                
    except Exception as e:
        print(f"ERROR al ejecutar SQL para {view_name}: {e}")
        return False

def main():
    views_to_create = [
        ("v_yango_cabinet_claims_for_collection", "sql/ops/v_yango_cabinet_claims_for_collection.sql"),
        ("v_claims_cabinet_driver_rollup", "sql/ops/v_claims_cabinet_driver_rollup.sql"),
    ]
    
    print("Creando vistas necesarias para Claims Cabinet...")
    print(f"Total de vistas a crear: {len(views_to_create)}")
    
    results = []
    for view_name, sql_path in views_to_create:
        success = create_view(view_name, sql_path)
        results.append((view_name, success))
    
    print(f"\n{'='*60}")
    print("RESUMEN:")
    print(f"{'='*60}")
    for view_name, success in results:
        status = "OK" if success else "ERROR"
        print(f"  {view_name}: {status}")
    
    all_success = all(success for _, success in results)
    if all_success:
        print("\nTodas las vistas se crearon exitosamente!")
        sys.exit(0)
    else:
        print("\nAlgunas vistas fallaron. Revisa los errores arriba.")
        sys.exit(1)

if __name__ == "__main__":
    main()









