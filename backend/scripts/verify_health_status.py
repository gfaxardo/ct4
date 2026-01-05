#!/usr/bin/env python3
"""
Script para verificar el status del health check
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT status_bucket, hours_since_ok_refresh, last_status
            FROM ops.v_yango_cabinet_claims_mv_health
        """))
        row = result.fetchone()
        if row:
            status_bucket = row[0]
            hours = row[1]
            last_status = row[2]
            print(f'STATUS_BUCKET: {status_bucket}, HOURS: {hours:.2f}, LAST_STATUS: {last_status}')
            # OK o WARN son aceptables (<48h)
            if status_bucket in ('OK', 'WARN'):
                sys.exit(0)
            else:
                sys.exit(1)
        else:
            print('NO_DATA')
            sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)



