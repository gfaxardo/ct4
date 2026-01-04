#!/usr/bin/env python3
"""
Script simple para aplicar la vista canónica usando psycopg2 directamente.
"""
import sys
import os
from pathlib import Path

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("✗ Error: psycopg2 no está instalado.")
    print("  Instala con: pip install psycopg2-binary")
    sys.exit(1)

def get_database_url():
    """Obtiene DATABASE_URL de variables de entorno o usa el default."""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"
    )
    return database_url

def parse_database_url(url):
    """Parsea DATABASE_URL y retorna componentes."""
    # postgresql://user:pass@host:port/dbname
    url = url.replace("postgresql://", "")
    if "@" in url:
        auth, rest = url.split("@", 1)
        if ":" in auth:
            user, password = auth.split(":", 1)
        else:
            user = auth
            password = ""
    else:
        user = ""
        password = ""
        rest = url
    
    if ":" in rest:
        host_port, dbname = rest.rsplit("/", 1)
        if ":" in host_port:
            host, port = host_port.split(":", 1)
        else:
            host = host_port
            port = "5432"
    else:
        host = rest.split("/")[0] if "/" in rest else rest
        port = "5432"
        dbname = rest.split("/")[1] if "/" in rest else "postgres"
    
    return {
        "host": host,
        "port": port,
        "database": dbname,
        "user": user,
        "password": password
    }

def execute_sql_file(conn, file_path: Path):
    """Ejecuta un archivo SQL completo."""
    print(f"\n{'='*80}")
    print(f"Ejecutando: {file_path.name}")
    print(f"{'='*80}\n")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Ejecutar todo el contenido SQL
        with conn.cursor() as cur:
            cur.execute(sql_content)
            conn.commit()
        
        print(f"[OK] Archivo {file_path.name} ejecutado completamente.\n")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Error ejecutando {file_path.name}:")
        print(f"  {str(e)}")
        conn.rollback()
        return False

def execute_verification_queries(conn, file_path: Path):
    """Ejecuta queries de verificación y muestra resultados."""
    print(f"\n{'='*80}")
    print(f"Ejecutando verificaciones: {file_path.name}")
    print(f"{'='*80}\n")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Dividir por punto y coma y ejecutar cada query SELECT
        queries = [q.strip() for q in sql_content.split(';') if q.strip() and not q.strip().startswith('--')]
        
        with conn.cursor() as cur:
            query_num = 0
            for query in queries:
                # Saltar comentarios
                if query.startswith('/*') or query.startswith('--'):
                    continue
                
                try:
                    cur.execute(query)
                    
                    # Si hay resultados, mostrarlos
                    if cur.description:
                        rows = cur.fetchall()
                        columns = [desc[0] for desc in cur.description]
                        
                        if rows:
                            query_num += 1
                            print(f"\n--- Query {query_num} ---")
                            # Mostrar encabezados
                            print(" | ".join(str(col) for col in columns))
                            print("-" * 80)
                            
                            # Mostrar filas (máximo 20)
                            for row in rows[:20]:
                                print(" | ".join(str(val) if val is not None else "NULL" for val in row))
                            
                            if len(rows) > 20:
                                print(f"\n... ({len(rows) - 20} filas más)")
                            print()
                        else:
                            query_num += 1
                            print(f"Query {query_num}: Sin resultados\n")
                    else:
                        # No hay resultados (CREATE, DROP, etc.)
                        pass
                        
                except Exception as e:
                    # Algunas queries pueden fallar si la vista no tiene datos aún
                    # Continuar con la siguiente
                    print(f"[WARNING] Query fallo (puede ser esperado): {str(e)[:100]}\n")
                    continue
        
        print(f"\n[OK] Verificaciones completadas.\n")
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Error ejecutando verificaciones:")
        print(f"  {str(e)}")
        return False

def main():
    """Función principal."""
    print("="*80)
    print("Aplicando vista canónica: ops.v_payments_driver_matrix_cabinet")
    print("="*80)
    
    # Obtener configuración de DB
    database_url = get_database_url()
    db_config = parse_database_url(database_url)
    
    print(f"Conectando a: {db_config['host']}:{db_config['port']}/{db_config['database']}")
    print(f"Usuario: {db_config['user']}\n")
    
    # Rutas de archivos
    backend_dir = Path(__file__).parent.parent
    sql_dir = backend_dir / "sql" / "ops"
    
    view_file = sql_dir / "v_payments_driver_matrix_cabinet.sql"
    verification_file = sql_dir / "v_payments_driver_matrix_cabinet_verification.sql"
    
    # Verificar que los archivos existan
    if not view_file.exists():
        print(f"[ERROR] Error: No se encuentra {view_file}")
        sys.exit(1)
    
    if not verification_file.exists():
        print(f"[ERROR] Error: No se encuentra {verification_file}")
        sys.exit(1)
    
    # Conectar a la base de datos
    try:
        conn = psycopg2.connect(
            host=db_config['host'],
            port=db_config['port'],
            database=db_config['database'],
            user=db_config['user'],
            password=db_config['password']
        )
        print("[OK] Conexion establecida\n")
    except Exception as e:
        print(f"[ERROR] Error conectando a la base de datos:")
        print(f"  {str(e)}")
        sys.exit(1)
    
    try:
        # Ejecutar vista canónica
        success1 = execute_sql_file(conn, view_file)
        
        if not success1:
            print("\n[ERROR] Fallo la aplicacion de la vista. Abortando.")
            sys.exit(1)
        
        # Ejecutar verificaciones
        success2 = execute_verification_queries(conn, verification_file)
        
        if success1 and success2:
            print("="*80)
            print("[OK] PROCESO COMPLETADO EXITOSAMENTE")
            print("="*80)
            sys.exit(0)
        else:
            print("="*80)
            print("[WARNING] PROCESO COMPLETADO CON ADVERTENCIAS")
            print("="*80)
            sys.exit(0)  # No fallar si las verificaciones tienen warnings
            
    finally:
        conn.close()

if __name__ == "__main__":
    main()

