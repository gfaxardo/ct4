#!/usr/bin/env python3
"""Script rápido para probar la vista limbo."""

import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"
)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

try:
    # Distribución por limbo_stage
    result = session.execute(text("""
        SELECT limbo_stage, COUNT(*) 
        FROM ops.v_cabinet_leads_limbo 
        GROUP BY limbo_stage 
        ORDER BY COUNT(*) DESC
    """))
    print("Distribución por limbo_stage:")
    for row in result:
        print(f"  {row[0]}: {row[1]}")
    
    # Leads post-05
    result2 = session.execute(text("""
        SELECT COUNT(*) 
        FROM ops.v_cabinet_leads_limbo 
        WHERE lead_date > '2026-01-05'
    """))
    print(f"\nLeads post-05: {result2.scalar()}")
    
    # Ejemplos post-05
    result3 = session.execute(text("""
        SELECT lead_source_pk, lead_date, limbo_stage, limbo_reason_detail
        FROM ops.v_cabinet_leads_limbo 
        WHERE lead_date > '2026-01-05'
        ORDER BY lead_date DESC
        LIMIT 5
    """))
    print("\nEjemplos post-05:")
    for row in result3:
        print(f"  {row[0]}: {row[1]} - {row[2]} - {row[3][:50]}")
        
finally:
    session.close()
