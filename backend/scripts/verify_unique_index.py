#!/usr/bin/env python3
"""
Script para verificar que el índice único existe
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT 1 
            FROM pg_indexes 
            WHERE schemaname='ops' 
              AND tablename='mv_yango_cabinet_claims_for_collection' 
              AND indexname='ux_mv_yango_cabinet_claims_for_collection_grain' 
            LIMIT 1
        """))
        exists = result.scalar()
        if exists:
            print('INDEX_EXISTS')
            sys.exit(0)
        else:
            print('INDEX_NOT_FOUND')
            sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)







