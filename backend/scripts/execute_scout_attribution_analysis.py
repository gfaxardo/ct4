#!/usr/bin/env python3
"""
Script de Ejecución: Análisis de Atribución de Scouts
Ejecuta los scripts SQL de diagnóstico y creación de vistas
"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Agregar el directorio backend al path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.config import settings
try:
    from app.db import get_db_url
except ImportError:
    # Fallback si get_db_url no existe
    def get_db_url():
        return settings.database_url

def execute_sql_file(engine, sql_file_path: Path, description: str, database_url: str) -> bool:
    """Ejecuta un archivo SQL y muestra el progreso"""
    print(f"\n{'='*50}")
    print(f"Ejecutando: {description}")
    print(f"Archivo: {sql_file_path.name}")
    print(f"{'='*50}\n")
    
    try:
        if not sql_file_path.exists():
            print(f"[ERROR] No se encuentra el archivo {sql_file_path}")
            return False
        
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Ejecutar el SQL completo usando psycopg2 directamente (más confiable para scripts complejos)
        try:
            import psycopg2
            from urllib.parse import urlparse
            
            # Parsear DATABASE_URL
            parsed = urlparse(database_url)
            conn_params = {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': parsed.path[1:] if parsed.path else None,
                'user': parsed.username,
                'password': parsed.password
            }
            
            with psycopg2.connect(**conn_params) as pg_conn:
                pg_conn.autocommit = True
                with pg_conn.cursor() as cursor:
                    # Ejecutar el script completo
                    cursor.execute(sql_content)
                    
                    # Intentar obtener resultados si hay
                    try:
                        if cursor.description:
                            rows = cursor.fetchall()
                            if rows:
                                print(f"  Resultados: {len(rows)} filas")
                                # Mostrar primeras 5 filas
                                for i, row in enumerate(rows[:5], 1):
                                    print(f"    {i}. {row}")
                                if len(rows) > 5:
                                    print(f"    ... y {len(rows) - 5} filas más")
                    except psycopg2.ProgrammingError:
                        # No hay resultados (CREATE VIEW, etc.)
                        pass
                    
                    print(f"  [OK] Script ejecutado correctamente")
                    return True
                    
        except ImportError:
            # Si psycopg2 no está disponible, usar SQLAlchemy (menos confiable para scripts complejos)
            print("  [WARN] psycopg2 no disponible, usando SQLAlchemy (puede tener limitaciones)")
            with engine.connect() as conn:
                # Ejecutar el contenido completo
                conn.execute(text(sql_content))
                conn.commit()
                print(f"  [OK] Script ejecutado correctamente")
                return True
        
        print(f"\n[OK] {description} completado ({executed} statements ejecutados)")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Error al ejecutar {description}: {str(e)[:200]}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    print("\n" + "="*50)
    print("ANÁLISIS DE ATRIBUCIÓN DE SCOUTS")
    print("="*50)
    
    # Obtener configuración de base de datos
    database_url = get_db_url()
    print(f"\nConectando a: {database_url.split('@')[1] if '@' in database_url else 'base de datos'}")
    
    try:
        engine = create_engine(database_url, echo=False)
        
        # Verificar conexión
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"[OK] Conectado a PostgreSQL: {version.split(',')[0]}")
    except Exception as e:
        print(f"[ERROR] No se pudo conectar a la base de datos: {str(e)}")
        return 1
    
    # Rutas de archivos SQL
    script_dir = Path(__file__).parent
    sql_dir = script_dir / "sql"
    
    diagnose_file = sql_dir / "diagnose_scout_attribution.sql"
    recommendations_file = sql_dir / "scout_attribution_recommendations.sql"
    verify_file = sql_dir / "verify_scout_attribution_views.sql"
    
    success = True
    
    # Paso 1: Ejecutar diagnóstico
    print("\n" + "="*50)
    print("PASO 1: DIAGNOSTICO")
    print("="*50)
    result = execute_sql_file(engine, diagnose_file, "Diagnostico de Atribucion de Scouts", database_url)
    if not result:
        success = False
        print("\n[WARN] El diagnostico tuvo errores. Continuando con la creacion de vistas...")
    
    # Paso 2: Crear vistas
    print("\n" + "="*50)
    print("PASO 2: CREACION DE VISTAS")
    print("="*50)
    result = execute_sql_file(engine, recommendations_file, "Creacion de Vistas de Atribucion de Scouts", database_url)
    if not result:
        success = False
    
    # Paso 3: Verificar vistas (si se crearon exitosamente)
    if verify_file.exists():
        print("\n" + "="*50)
        print("PASO 3: VERIFICACION")
        print("="*50)
        execute_sql_file(engine, verify_file, "Verificacion de Vistas Creadas", database_url)
    
    # Resumen final
    print("\n" + "="*50)
    if success:
        print("[OK] PROCESO COMPLETADO")
        print("\nProximos pasos:")
        print("1. Revisa los resultados del diagnostico")
        print("2. Valida las vistas creadas:")
        print("   SELECT * FROM ops.v_scout_attribution LIMIT 10;")
        print("   SELECT * FROM ops.v_scout_attribution_conflicts LIMIT 10;")
        print("3. Verifica cobertura y conflictos")
    else:
        print("[WARN] PROCESO COMPLETADO CON ERRORES")
        print("   Revisa los mensajes de error arriba")
    print("="*50 + "\n")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

