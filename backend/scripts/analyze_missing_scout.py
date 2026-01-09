#!/usr/bin/env python3
"""Analizar registros sin scout y generar reporte"""

import sys
from pathlib import Path
import pandas as pd

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.config import settings
from sqlalchemy import create_engine, text

def main():
    engine = create_engine(settings.database_url)
    
    sql_file = Path(__file__).parent / "sql" / "analyze_missing_scout_attribution.sql"
    
    with open(sql_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()
    
    # Dividir en queries individuales (separadas por --)
    queries = []
    current_query = ""
    
    for line in sql_content.split('\n'):
        if line.strip().startswith('--') and line.strip().startswith('-- ='):
            if current_query.strip():
                queries.append(current_query.strip())
            current_query = ""
        else:
            current_query += line + '\n'
    
    if current_query.strip():
        queries.append(current_query.strip())
    
    results = {}
    
    with engine.connect() as conn:
        for i, query in enumerate(queries, 1):
            query = query.strip()
            if not query or query.startswith('--'):
                continue
            
            try:
                result = conn.execute(text(query))
                
                if result.returns_rows:
                    rows = result.fetchall()
                    columns = result.keys()
                    
                    # Guardar resultados
                    df = pd.DataFrame(rows, columns=columns)
                    results[f"query_{i}"] = df
                    
                    print(f"\n{'='*60}")
                    print(f"Query {i}")
                    print(f"{'='*60}")
                    print(df.to_string(index=False))
                    
            except Exception as e:
                error_msg = str(e)
                if 'does not exist' not in error_msg.lower():
                    print(f"\n[ERROR] Query {i}: {error_msg[:200]}")
    
    # Generar resumen
    print(f"\n{'='*60}")
    print("RESUMEN EJECUTIVO")
    print(f"{'='*60}")
    
    # Buscar el resumen ejecutivo en los resultados
    for key, df in results.items():
        if 'RESUMEN' in df.to_string() or 'summary' in df.columns:
            print(df.to_string(index=False))
            break
    
    return 0

if __name__ == "__main__":
    sys.exit(main())


