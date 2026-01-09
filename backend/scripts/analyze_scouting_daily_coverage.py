#!/usr/bin/env python3
"""Analizar cobertura de scout en scouting_daily"""

import sys
from pathlib import Path

backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))

from app.config import settings
from sqlalchemy import create_engine, text

engine = create_engine(settings.database_url)

sql_file = Path(__file__).parent / "sql" / "analyze_scouting_daily_scout_coverage.sql"

print("="*70)
print("ANALISIS: COBERTURA DE SCOUT EN SCOUTING_DAILY")
print("="*70)

with open(sql_file, 'r', encoding='utf-8') as f:
    sql_content = f.read()

# Dividir en queries (separadas por -- =)
queries = []
current_query = ""

for line in sql_content.split('\n'):
    if line.strip().startswith('-- =') and len(line.strip()) > 10:
        if current_query.strip():
            queries.append(current_query.strip())
        current_query = ""
    else:
        current_query += line + '\n'

if current_query.strip():
    queries.append(current_query.strip())

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
                
                # Mostrar título si es un resumen ejecutivo
                if 'RESUMEN EJECUTIVO' in str(rows):
                    print(f"\n{'='*70}")
                    print("RESUMEN EJECUTIVO")
                    print(f"{'='*70}")
                
                # Mostrar resultados
                if len(rows) > 0:
                    # Si es resumen ejecutivo, mostrar como tabla
                    if 'summary' in columns or len(columns) > 5:
                        import pandas as pd
                        df = pd.DataFrame(rows, columns=columns)
                        print("\n" + df.to_string(index=False))
                    else:
                        # Formato simple para métricas
                        for row in rows:
                            if len(columns) == 2:
                                print(f"  {row[0]}: {row[1]}")
                            else:
                                print("  " + " | ".join([f"{col}: {val}" for col, val in zip(columns, row)]))
                        
        except Exception as e:
            error_msg = str(e)
            if 'does not exist' not in error_msg.lower() and 'relation' not in error_msg.lower():
                print(f"\n[ERROR] Query {i}: {error_msg[:200]}")

print("\n" + "="*70)
print("ANALISIS COMPLETADO")
print("="*70)

