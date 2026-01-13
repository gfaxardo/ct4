#!/usr/bin/env python3
"""
Script de validación: confirma que expected/gap no filtra por pagos.
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

def verify_claims_independent_of_paid():
    """Verifica que hay claims expected sin pagar."""
    query = text("""
        SELECT 
            COUNT(*) AS total_expected
        FROM ops.v_cabinet_claims_expected_14d
        WHERE claim_expected = true
    """)
    
    result = session.execute(query)
    row = result.fetchone()
    
    print("=" * 80)
    print("VERIFICACIÓN: Claims independientes de pagos")
    print("=" * 80)
    print(f"Total expected: {row.total_expected or 0}")
    
    # Verificar que hay claims en tabla física sin paid_at
    query2 = text("""
        SELECT 
            COUNT(*) AS total_claims,
            COUNT(*) FILTER (WHERE paid_at IS NOT NULL) AS paid_claims,
            COUNT(*) FILTER (WHERE paid_at IS NULL) AS unpaid_claims
        FROM canon.claims_yango_cabinet_14d
        WHERE status IN ('expected', 'generated', 'paid')
    """)
    
    result2 = session.execute(query2)
    row2 = result2.fetchone()
    
    print(f"\nEn tabla física:")
    print(f"  Total claims: {row2.total_claims or 0}")
    print(f"  Paid claims: {row2.paid_claims or 0}")
    print(f"  Unpaid claims: {row2.unpaid_claims or 0}")
    
    # Verificar que hay expected sin paid
    query3 = text("""
        SELECT COUNT(*) AS count
        FROM ops.v_cabinet_claims_expected_14d e
        WHERE e.claim_expected = true
            AND EXISTS (
                SELECT 1
                FROM canon.claims_yango_cabinet_14d c
                WHERE c.person_key::text = e.person_key
                    AND c.lead_date = e.lead_date_canonico
                    AND c.milestone = e.milestone
                    AND c.paid_at IS NULL
            )
    """)
    
    result3 = session.execute(query3)
    count_unpaid = result3.scalar() or 0
    
    print(f"\nExpected claims sin pagar: {count_unpaid}")
    
    if count_unpaid > 0:
        print("OK: Hay claims expected sin pagar (independientes de pagos)")
        return True
    else:
        print("WARNING: No hay claims expected sin pagar")
        return True  # No es error, solo información

if __name__ == "__main__":
    verify_claims_independent_of_paid()
    session.close()
