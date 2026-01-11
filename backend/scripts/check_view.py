#!/usr/bin/env python3
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.database_url)

with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT EXISTS(
            SELECT 1 FROM pg_views 
            WHERE schemaname = 'ops' 
            AND viewname = 'v_cabinet_financial_14d'
        ) AS exists
    """))
    exists = result.scalar()
    print(f"v_cabinet_financial_14d existe: {exists}")
