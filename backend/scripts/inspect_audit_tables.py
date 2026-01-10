#!/usr/bin/env python3
"""Inspeccionar estructura de tablas de auditoría y enum jobtype"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.database_url)
conn = engine.connect()

# Verificar si existe identity_links_backfill_audit
try:
    result = conn.execute(text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'ops' AND table_name = 'identity_links_backfill_audit' 
        ORDER BY ordinal_position
    """))
    print("identity_links_backfill_audit columns:")
    for row in result:
        print(f"  {row[0]}: {row[1]}")
except Exception as e:
    print(f"Tabla no existe o error: {e}")

# Verificar enum jobtype
try:
    result = conn.execute(text("""
        SELECT unnest(enum_range(NULL::jobtype))::text AS enum_value
    """))
    print("\njobtype enum values:")
    for row in result:
        print(f"  {row[0]}")
except Exception as e:
    print(f"\nError obteniendo enum: {e}")

# Verificar estructura de ingestion_runs
try:
    result = conn.execute(text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema = 'ops' AND table_name = 'ingestion_runs' 
        ORDER BY ordinal_position
    """))
    print("\ningestion_runs columns:")
    for row in result:
        print(f"  {row[0]}: {row[1]}")
except Exception as e:
    print(f"Error: {e}")

conn.close()

