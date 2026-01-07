#!/usr/bin/env python3
"""
Script para aplicar la vista canónica ops.v_payments_driver_matrix_cabinet
y ejecutar queries de verificación.
"""
import sys
from pathlib import Path

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.db import engine
from app.config import settings

def execute_sql_file(file_path: Path):
    """Ejecuta un archivo SQL completo."""
    print(f"\n{'='*80}")
    print(f"Ejecutando: {file_path.name}")
    print(f"{'='*80}\n")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Dividir por punto y coma para ejecutar cada statement
        # PostgreSQL permite múltiples statements separados por ;
        statements = [s.strip() for s in sql_content.split(';') if s.strip() and not s.strip().startswith('--')]
        
        with engine.connect() as conn:
            for i, statement in enumerate(statements, 1):
                # Saltar comentarios y queries comentadas
                if statement.startswith('/*') or statement.startswith('--'):
                    continue
                
                # Ejecutar statement
                try:
                    result = conn.execute(text(statement))
                    conn.commit()
                    
                    # Si hay resultados, mostrarlos
                    if result.returns_rows:
                        rows = result.fetchall()
                        if rows:
                            print(f"✓ Statement {i} ejecutado. Filas retornadas: {len(rows)}")
                            # Mostrar primeras 5 filas si hay muchas
                            if len(rows) <= 5:
                                for row in rows:
                                    print(f"  {row}")
                            else:
                                for row in rows[:5]:
                                    print(f"  {row}")
                                print(f"  ... ({len(rows) - 5} filas más)")
                        else:
                            print(f"✓ Statement {i} ejecutado. Sin filas retornadas.")
                    else:
                        print(f"✓ Statement {i} ejecutado exitosamente.")
                        
                except Exception as e:
                    print(f"✗ Error en statement {i}:")
                    print(f"  {str(e)}")
                    print(f"  Statement: {statement[:200]}...")
                    raise
        
        print(f"\n✓ Archivo {file_path.name} ejecutado completamente.\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Error ejecutando {file_path.name}:")
        print(f"  {str(e)}")
        return False

def execute_verification_queries(file_path: Path):
    """Ejecuta queries de verificación y muestra resultados."""
    print(f"\n{'='*80}")
    print(f"Ejecutando verificaciones: {file_path.name}")
    print(f"{'='*80}\n")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Dividir por líneas y ejecutar queries SELECT
        lines = sql_content.split('\n')
        current_query = []
        query_num = 0
        
        with engine.connect() as conn:
            for line in lines:
                # Saltar comentarios y líneas vacías
                stripped = line.strip()
                if not stripped or stripped.startswith('--') or stripped.startswith('/*'):
                    continue
                
                current_query.append(line)
                
                # Si la línea termina con ;, ejecutar la query
                if stripped.endswith(';'):
                    query = '\n'.join(current_query)
                    query_num += 1
                    
                    try:
                        result = conn.execute(text(query))
                        
                        if result.returns_rows:
                            rows = result.fetchall()
                            columns = result.keys()
                            
                            if rows:
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
                                print(f"Query {query_num}: Sin resultados\n")
                        else:
                            print(f"Query {query_num}: Ejecutada (sin resultados)\n")
                            
                    except Exception as e:
                        print(f"✗ Error en query {query_num}:")
                        print(f"  {str(e)}")
                        print(f"  Query: {query[:200]}...")
                        # Continuar con la siguiente query
                    
                    current_query = []
        
        print(f"\n✓ Verificaciones completadas.\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Error ejecutando verificaciones:")
        print(f"  {str(e)}")
        return False

def main():
    """Función principal."""
    print("="*80)
    print("Aplicando vista canónica: ops.v_payments_driver_matrix_cabinet")
    print("="*80)
    print(f"Database URL: {settings.database_url.split('@')[1] if '@' in settings.database_url else 'configurada'}")
    
    # Rutas de archivos
    backend_dir = Path(__file__).parent.parent
    sql_dir = backend_dir / "sql" / "ops"
    
    view_file = sql_dir / "v_payments_driver_matrix_cabinet.sql"
    verification_file = sql_dir / "v_payments_driver_matrix_cabinet_verification.sql"
    
    # Verificar que los archivos existan
    if not view_file.exists():
        print(f"✗ Error: No se encuentra {view_file}")
        sys.exit(1)
    
    if not verification_file.exists():
        print(f"✗ Error: No se encuentra {verification_file}")
        sys.exit(1)
    
    # Ejecutar vista canónica
    success1 = execute_sql_file(view_file)
    
    if not success1:
        print("\n✗ Falló la aplicación de la vista. Abortando.")
        sys.exit(1)
    
    # Ejecutar verificaciones
    success2 = execute_verification_queries(verification_file)
    
    if success1 and success2:
        print("="*80)
        print("✓ PROCESO COMPLETADO EXITOSAMENTE")
        print("="*80)
        sys.exit(0)
    else:
        print("="*80)
        print("✗ PROCESO COMPLETADO CON ERRORES")
        print("="*80)
        sys.exit(1)

if __name__ == "__main__":
    main()







