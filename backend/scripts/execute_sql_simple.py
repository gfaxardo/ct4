#!/usr/bin/env python3
"""
Script simple para ejecutar archivos SQL en PostgreSQL
No requiere dependencias del proyecto, solo psycopg2
"""

import sys
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("[ERROR] ERROR: psycopg2 no está instalado.")
    print("   Instala con: pip install psycopg2-binary")
    sys.exit(1)

# Configuración de base de datos
DB_CONFIG = {
    'host': '168.119.226.236',
    'port': '5432',
    'database': 'yego_integral',
    'user': 'yego_user',
    'password': '37>MNA&-35+'
}

def execute_sql_file(sql_file_path):
    """Ejecuta un archivo SQL completo"""
    print(f"Ejecutando: {sql_file_path}")
    
    if not Path(sql_file_path).exists():
        print(f"[ERROR] ERROR: No se encontró el archivo: {sql_file_path}")
        return False
    
    with open(sql_file_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Ejecutar el SQL completo
        cur.execute(sql_content)
        
        cur.close()
        conn.close()
        
        print(f"[OK] Archivo ejecutado exitosamente: {sql_file_path}")
        return True
        
    except Exception as e:
        print(f"[ERROR] ERROR al ejecutar SQL: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_view(view_name):
    """Verifica que una vista existe y es accesible"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        cur.execute(f"SELECT COUNT(*) FROM {view_name} LIMIT 1")
        count = cur.fetchone()[0]
        
        cur.close()
        conn.close()
        
        print(f"[OK] Vista '{view_name}' verificada. Existe y es accesible. (Filas: {count})")
        return True
        
    except Exception as e:
        print(f"[WARN] Advertencia al verificar vista: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Uso: python execute_sql_simple.py <archivo_sql> [verificar_vista]")
        print("\nEjemplo:")
        print("  python execute_sql_simple.py sql/ops/v_cabinet_financial_14d.sql ops.v_cabinet_financial_14d")
        sys.exit(1)
    
    sql_file = sys.argv[1]
    view_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Si es una ruta relativa, buscar desde el directorio del script
    if not Path(sql_file).is_absolute():
        script_dir = Path(__file__).parent
        sql_file = script_dir.parent / sql_file
    
    print("=" * 70)
    print("Ejecutando archivo SQL")
    print("=" * 70)
    
    success = execute_sql_file(sql_file)
    
    if success and view_name:
        print("\nVerificando vista...")
        verify_view(view_name)
    
    print("\n" + "=" * 70)
    if success:
        print("[OK] Proceso completado exitosamente!")
    else:
        print("[ERROR] Proceso falló. Revisa los errores arriba.")
    print("=" * 70)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

