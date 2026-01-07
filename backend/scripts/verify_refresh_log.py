#!/usr/bin/env python3
"""
Script para verificar el último refresh log de la MV
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT status, rows_after_refresh
            FROM ops.mv_refresh_log
            WHERE schema_name = 'ops'
              AND mv_name = 'mv_yango_cabinet_claims_for_collection'
            ORDER BY refresh_started_at DESC, refreshed_at DESC
            LIMIT 1
        """))
        row = result.fetchone()
        if row and row[0] in ('OK', 'SUCCESS'):
            print(f'STATUS_OK: {row[0]}, ROWS: {row[1]}')
            sys.exit(0)
        else:
            print(f'STATUS_NOT_OK: {row[0] if row else "NO_RECORD"}')
            sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)








