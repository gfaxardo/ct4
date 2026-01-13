#!/usr/bin/env python3
"""
Script de validación: verifica que no hay duplicados de claims.
"""

import sys
import os
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"
)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

def verify_no_duplicates():
    """Verifica que no hay duplicados por unique key."""
    query = text("""
        SELECT 
            person_key,
            lead_date,
            milestone,
            COUNT(*) AS count
        FROM canon.claims_yango_cabinet_14d
        GROUP BY person_key, lead_date, milestone
        HAVING COUNT(*) > 1
    """)
    
    result = session.execute(query)
    duplicates = result.fetchall()
    
    if duplicates:
        print("ERROR: Se encontraron duplicados:")
        for dup in duplicates:
            print(f"  person_key={dup.person_key}, lead_date={dup.lead_date}, milestone={dup.milestone}, count={dup.count}")
        return False
    else:
        print("OK: No hay duplicados en canon.claims_yango_cabinet_14d")
        return True

if __name__ == "__main__":
    success = verify_no_duplicates()
    session.close()
    sys.exit(0 if success else 1)
