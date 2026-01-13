#!/usr/bin/env python3
"""Validación de baseline post-05 después de correcciones."""

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
    print("=" * 80)
    print("VALIDACION BASELINE POST-05")
    print("=" * 80)
    
    # 1. Baseline: COUNT leads post-05 según LEAD_DATE_CANONICO
    print("\n1. Baseline: COUNT leads post-05 según LEAD_DATE_CANONICO (lead_created_at::date):")
    result = session.execute(text("""
        SELECT COUNT(*) 
        FROM public.module_ct_cabinet_leads
        WHERE lead_created_at::date > '2026-01-05'
    """))
    baseline = result.scalar()
    print(f"  Resultado: {baseline} leads")
    
    # 2. COUNT en vista limbo post-05
    print("\n2. COUNT en vista limbo post-05:")
    result = session.execute(text("""
        SELECT COUNT(*) 
        FROM ops.v_cabinet_leads_limbo
        WHERE lead_date > '2026-01-05'
    """))
    limbo_count = result.scalar()
    print(f"  Resultado: {limbo_count} leads")
    
    if baseline == limbo_count:
        print("  [OK] PASS: Todos los leads post-05 aparecen en vista limbo")
    else:
        print(f"  [FAIL] Diferencia de {abs(baseline - limbo_count)} leads")
    
    # 3. Distribución por limbo_stage post-05
    print("\n3. Distribución por limbo_stage post-05:")
    result = session.execute(text("""
        SELECT 
            limbo_stage,
            COUNT(*) AS count
        FROM ops.v_cabinet_leads_limbo
        WHERE lead_date > '2026-01-05'
        GROUP BY limbo_stage
        ORDER BY count DESC
    """))
    rows = result.fetchall()
    for row in rows:
        print(f"  {row.limbo_stage}: {row.count}")
    
    # 4. Últimas 8 semanas en audit_weekly
    print("\n4. Últimas 8 semanas en audit_weekly:")
    result = session.execute(text("""
        SELECT 
            week_start,
            leads_total,
            limbo_no_identity,
            limbo_no_driver,
            limbo_no_trips_14d,
            limbo_trips_no_claim,
            limbo_ok
        FROM ops.v_cabinet_14d_funnel_audit_weekly
        ORDER BY week_start DESC
        LIMIT 8
    """))
    rows = result.fetchall()
    print("  Semana       | Leads | NO_ID | NO_DRV | NO_TRP | NO_CLM | OK")
    print("  " + "-" * 70)
    for row in rows:
        print(f"  {row.week_start} | {row.leads_total:5d} | {row.limbo_no_identity:5d} | {row.limbo_no_driver:5d} | {row.limbo_no_trips_14d:5d} | {row.limbo_trips_no_claim:5d} | {row.limbo_ok:3d}")
    
    # 5. Verificar semanas post-05
    print("\n5. Semanas post-05 en audit_weekly:")
    result = session.execute(text("""
        SELECT 
            week_start,
            leads_total
        FROM ops.v_cabinet_14d_funnel_audit_weekly
        WHERE week_start >= '2026-01-05'
        ORDER BY week_start DESC
    """))
    rows = result.fetchall()
    if rows:
        print("  [OK] PASS: Semanas post-05 aparecen en auditoría")
        for row in rows:
            print(f"    {row.week_start}: {row.leads_total} leads")
    else:
        print("  [FAIL] No hay semanas post-05 en auditoría")
    
    print("\n" + "=" * 80)
    print("VALIDACION COMPLETA")
    print("=" * 80)
    
finally:
    session.close()
