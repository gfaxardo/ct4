#!/usr/bin/env python3
"""
Script para verificar que la vista ops.v_yango_cabinet_claims_mv_health existe
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.views 
                WHERE table_schema = 'ops' 
                AND table_name = 'v_yango_cabinet_claims_mv_health'
            )
        """))
        exists = result.scalar()
        if exists:
            print('VIEW_EXISTS')
            sys.exit(0)
        else:
            print('VIEW_NOT_FOUND')
            sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)


