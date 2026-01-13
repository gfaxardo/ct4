#!/usr/bin/env python3
"""Script para auditar fecha cero canónica en module_ct_cabinet_leads."""

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
    print("AUDITORIA FECHA CERO - module_ct_cabinet_leads")
    print("=" * 80)
    
    # 1. Identificar columnas relacionadas a fecha
    print("\n1. COLUMNAS RELACIONADAS A FECHA:")
    result = session.execute(text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_schema='public' 
            AND table_name='module_ct_cabinet_leads' 
            AND (
                column_name LIKE '%date%' 
                OR column_name LIKE '%created%' 
                OR column_name LIKE '%registered%' 
                OR column_name LIKE '%lead%'
            )
        ORDER BY column_name
    """))
    cols = result.fetchall()
    for col in cols:
        print(f"  {col[0]}: {col[1]}")
    
    # 2. Q1: COUNT por lead_created_at::date > '2026-01-05'
    print("\n2. Q1: COUNT por lead_created_at::date > '2026-01-05':")
    result = session.execute(text("""
        SELECT COUNT(*) 
        FROM public.module_ct_cabinet_leads
        WHERE lead_created_at::date > '2026-01-05'
    """))
    count_created = result.scalar()
    print(f"  Resultado: {count_created}")
    
    # 3. Q2: COUNT por lead_date::date > '2026-01-05' (si existe)
    print("\n3. Q2: Verificar si existe columna 'lead_date':")
    result = session.execute(text("""
        SELECT EXISTS (
            SELECT 1 
            FROM information_schema.columns 
            WHERE table_schema='public' 
                AND table_name='module_ct_cabinet_leads' 
                AND column_name='lead_date'
        )
    """))
    has_lead_date = result.scalar()
    print(f"  Existe lead_date: {has_lead_date}")
    
    if has_lead_date:
        result = session.execute(text("""
            SELECT COUNT(*) 
            FROM public.module_ct_cabinet_leads
            WHERE lead_date::date > '2026-01-05'
        """))
        count_lead_date = result.scalar()
        print(f"  COUNT por lead_date::date > '2026-01-05': {count_lead_date}")
    
    # 4. Q3: Rango min/max para ambas
    print("\n4. Q3: Rango min/max para lead_created_at:")
    result = session.execute(text("""
        SELECT 
            MIN(lead_created_at::date) AS min_date,
            MAX(lead_created_at::date) AS max_date,
            COUNT(*) AS total
        FROM public.module_ct_cabinet_leads
        WHERE lead_created_at IS NOT NULL
    """))
    row = result.fetchone()
    print(f"  Min: {row.min_date}, Max: {row.max_date}, Total: {row.total}")
    
    if has_lead_date:
        result = session.execute(text("""
            SELECT 
                MIN(lead_date::date) AS min_date,
                MAX(lead_date::date) AS max_date,
                COUNT(*) AS total
            FROM public.module_ct_cabinet_leads
            WHERE lead_date IS NOT NULL
        """))
        row = result.fetchone()
        print(f"  Min (lead_date): {row.min_date}, Max: {row.max_date}, Total: {row.total}")
    
    # 5. Q4: Top 20 records > '2026-01-05' mostrando ambas fechas
    print("\n5. Q4: Top 20 records > '2026-01-05':")
    if has_lead_date:
        query = text("""
            SELECT 
                id,
                external_id,
                lead_created_at::date AS created_date,
                lead_date::date AS lead_date_col,
                created_at::date AS created_at_col
            FROM public.module_ct_cabinet_leads
            WHERE lead_created_at::date > '2026-01-05'
            ORDER BY lead_created_at DESC
            LIMIT 20
        """)
    else:
        query = text("""
            SELECT 
                id,
                external_id,
                lead_created_at::date AS created_date,
                NULL::date AS lead_date_col,
                created_at::date AS created_at_col
            FROM public.module_ct_cabinet_leads
            WHERE lead_created_at::date > '2026-01-05'
            ORDER BY lead_created_at DESC
            LIMIT 20
        """)
    
    result = session.execute(query)
    rows = result.fetchall()
    print(f"  Encontrados {len(rows)} registros:")
    for i, row in enumerate(rows[:10], 1):
        print(f"    {i}. ID={row.id}, external_id={row.external_id}, lead_created_at={row.created_date}, lead_date={row.lead_date_col}, created_at={row.created_at_col}")
    
    # 6. Comparar lead_created_at vs created_at
    print("\n6. Comparación lead_created_at vs created_at:")
    result = session.execute(text("""
        SELECT 
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE lead_created_at::date != created_at::date) AS different,
            COUNT(*) FILTER (WHERE lead_created_at::date = created_at::date) AS same,
            COUNT(*) FILTER (WHERE lead_created_at IS NULL) AS null_created,
            COUNT(*) FILTER (WHERE created_at IS NULL) AS null_created_at
        FROM public.module_ct_cabinet_leads
    """))
    row = result.fetchone()
    print(f"  Total: {row.total}")
    print(f"  Diferentes: {row.different}")
    print(f"  Iguales: {row.same}")
    print(f"  NULL lead_created_at: {row.null_created}")
    print(f"  NULL created_at: {row.null_created_at}")
    
    print("\n" + "=" * 80)
    print("CONCLUSION:")
    print("=" * 80)
    print(f"  - Leads post-05 por lead_created_at: {count_created}")
    if has_lead_date:
        print(f"  - Leads post-05 por lead_date: {count_lead_date}")
        print(f"  - Diferencia: {abs(count_created - count_lead_date)}")
    print("\n  RECOMENDACION:")
    if has_lead_date:
        print("  - Usar lead_date si existe y es diferente de lead_created_at")
        print("  - Si lead_date es NULL, usar lead_created_at como fallback")
    else:
        print("  - Usar lead_created_at::date como LEAD_DATE_CANONICO")
        print("  - created_at puede ser diferente (timestamp de inserción en BD)")
    
finally:
    session.close()
