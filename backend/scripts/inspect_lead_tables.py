#!/usr/bin/env python3
"""Inspecciona estructura de lead_ledger y lead_events"""
import sys
from pathlib import Path
backend_root = Path(__file__).parent.parent
sys.path.insert(0, str(backend_root))
from app.config import settings
from sqlalchemy import create_engine, inspect

engine = create_engine(settings.database_url)
inspector = inspect(engine)

print('=== lead_ledger columns ===')
cols = inspector.get_columns('lead_ledger', schema='observational')
for c in cols:
    print(f"{c['name']}: {c['type']}")

print('\n=== lead_events columns ===')
cols = inspector.get_columns('lead_events', schema='observational')
for c in cols:
    print(f"{c['name']}: {c['type']}")

