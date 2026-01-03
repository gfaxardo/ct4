#!/usr/bin/env python3
"""
Script para crear el índice único en ops.mv_yango_cabinet_claims_for_collection
Usa autocommit porque CREATE INDEX CONCURRENTLY no puede ejecutarse en transacción
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import text, create_engine
from app.config import settings

def main():
    # Leer el archivo SQL
    project_root = Path(__file__).parent.parent
    sql_file = project_root / 'sql' / 'ops' / 'mv_yango_cabinet_claims_unique_index.sql'
    
    if not sql_file.exists():
        print(f"Error: No se encontró el archivo {sql_file}")
        sys.exit(1)
    
    print(f"Leyendo archivo SQL: {sql_file}")
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Separar los comandos SQL (dividir por punto y coma, pero respetar comentarios)
    # Extraer solo las líneas que no son comentarios y tienen contenido SQL
    sql_lines = []
    for line in sql_content.split('\n'):
        stripped = line.strip()
        # Ignorar líneas vacías y comentarios
        if stripped and not stripped.startswith('--'):
            sql_lines.append(line)
    
    # Unir las líneas y dividir por punto y coma
    full_sql = '\n'.join(sql_lines)
    statements = [s.strip() for s in full_sql.split(';') if s.strip()]
    
    # Crear engine y ejecutar con autocommit
    print("Creando conexión con autocommit (sin transacción)...")
    # IMPORTANTE: CONCURRENTLY requiere autocommit, no puede estar en transacción
    engine = create_engine(settings.database_url)
    
    # Usar autocommit para CREATE INDEX CONCURRENTLY
    with engine.connect() as conn:
        # Configurar autocommit para esta conexión
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        
        for i, statement in enumerate(statements, 1):
            if not statement:
                continue
                
            # Agregar punto y coma si no termina con uno
            if not statement.rstrip().endswith(';'):
                statement += ';'
            
            print(f"\nEjecutando statement {i}/{len(statements)}...")
            if len(statement) > 150:
                print(f"SQL: {statement[:150]}...")
            else:
                print(f"SQL: {statement}")
            
            try:
                result = conn.execute(text(statement))
                print(f"[OK] Statement {i} ejecutado exitosamente")
            except Exception as e:
                error_msg = str(e).lower()
                # Para CREATE INDEX CONCURRENTLY, algunos errores son esperados
                if "already exists" in error_msg or "duplicate" in error_msg:
                    print(f"[INFO] El índice ya existe (esto es normal), continuando...")
                elif "cannot run inside a transaction" in error_msg:
                    print(f"[ERROR] Aún está en transacción. Esto no debería pasar con autocommit.")
                    raise
                else:
                    print(f"[ERROR] Error en statement {i}: {e}")
                    raise
    
    print("\n[OK] Índice único creado exitosamente")
    print("\nPara verificar, ejecuta:")
    print("  SELECT schemaname, indexname, indexdef")
    print("  FROM pg_indexes")
    print("  WHERE schemaname = 'ops'")
    print("    AND tablename = 'mv_yango_cabinet_claims_for_collection'")
    print("    AND indexname = 'ux_mv_yango_cabinet_claims_for_collection_grain';")

if __name__ == '__main__':
    main()

