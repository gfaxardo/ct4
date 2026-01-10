#!/usr/bin/env python3
"""Verificar métricas finales después de ejecución completa"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)

db = SessionLocal()

print("="*80)
print("VERIFICACION METRICAS FINALES")
print("="*80)

# 1. Scouting daily con identity
query1 = text("""
    SELECT 
        COUNT(*) FILTER (WHERE scout_id IS NOT NULL) AS total_with_scout,
        COUNT(*) FILTER (
            WHERE scout_id IS NOT NULL 
            AND EXISTS (
                SELECT 1 FROM canon.identity_links il
                WHERE il.source_table = 'module_ct_scouting_daily'
                    AND il.source_pk = sd.id::TEXT
            )
        ) AS with_identity
    FROM public.module_ct_scouting_daily sd
""")
result1 = db.execute(query1)
row1 = result1.fetchone()
total_scout = row1[0]
with_identity = row1[1]
pct_identity = (with_identity / total_scout * 100) if total_scout > 0 else 0

print(f"\n1. SCOUTING_DAILY CON IDENTITY:")
print(f"   Total con scout_id: {total_scout:,}")
print(f"   Con identity_links: {with_identity:,}")
print(f"   Porcentaje: {pct_identity:.1f}%")

# 2. Scout satisfactorio global
query2 = text("""
    SELECT COUNT(DISTINCT person_key) AS total_satisfactory
    FROM observational.lead_ledger
    WHERE attributed_scout_id IS NOT NULL
""")
result2 = db.execute(query2)
total_satisfactory = result2.scalar()

print(f"\n2. SCOUT SATISFACTORIO GLOBAL:")
print(f"   Total: {total_satisfactory:,}")

# 3. Categoría D
try:
    query3 = text("""
        SELECT COUNT(*) FROM ops.v_persons_without_scout_categorized
        WHERE category = 'D'
    """)
    result3 = db.execute(query3)
    category_d = result3.scalar()
    print(f"\n3. CATEGORIA D (scout en eventos no propagado):")
    print(f"   Total: {category_d:,}")
except Exception as e:
    db.rollback()
    print(f"\n3. CATEGORIA D (scout en eventos no propagado):")
    print(f"   Vista no disponible aún")

# 4. Conflictos
try:
    query4 = text("""
        SELECT COUNT(*) FROM ops.v_scout_attribution_conflicts
    """)
    result4 = db.execute(query4)
    conflicts = result4.scalar()
    print(f"\n4. CONFLICTOS:")
    print(f"   Total: {conflicts:,}")
except Exception as e:
    db.rollback()
    print(f"\n4. CONFLICTOS:")
    print(f"   Vista no disponible aún")

# 5. Vista de pagos
try:
    query5 = text("""
        SELECT payment_status, COUNT(*) 
        FROM ops.v_scout_payment_base 
        GROUP BY payment_status
        ORDER BY payment_status
    """)
    result5 = db.execute(query5)
    print(f"\n5. VISTA DE PAGOS:")
    for row in result5:
        print(f"   {row[0]}: {row[1]:,}")
except Exception as e:
    db.rollback()
    print(f"\n5. VISTA DE PAGOS:")
    print(f"   Vista no disponible aún")

# 6. Backfill audit
try:
    query6 = text("""
        SELECT COUNT(*) FROM ops.lead_ledger_scout_backfill_audit
        WHERE backfill_timestamp >= CURRENT_DATE - INTERVAL '1 day'
    """)
    result6 = db.execute(query6)
    backfill_count = result6.scalar()
    print(f"\n6. BACKFILL AUDIT (últimas 24h):")
    print(f"   Registros: {backfill_count:,}")
except Exception as e:
    db.rollback()
    print(f"\n6. BACKFILL AUDIT (últimas 24h):")
    print(f"   Tabla no disponible aún")

print("\n" + "="*80)
print("VERIFICACION COMPLETA")
print("="*80)

db.close()

