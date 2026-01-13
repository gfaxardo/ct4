# Alertas: Claims Gap

**Propósito:** Disparar alertas cuando hay drivers con milestones pero sin claims.

---

## Alertas Mínimas

### 1. Gaps aumentan semana a semana

**Query:**
```sql
WITH weekly_gaps AS (
    SELECT 
        week_start,
        COUNT(*) AS gaps_count
    FROM ops.v_cabinet_claims_gap_14d
    WHERE gap_reason = 'MILESTONE_ACHIEVED_NO_CLAIM'
        AND week_start >= CURRENT_DATE - INTERVAL '4 weeks'
    GROUP BY week_start
    ORDER BY week_start DESC
    LIMIT 2
)
SELECT 
    w1.week_start,
    w1.gaps_count,
    w2.gaps_count AS prev_week_count,
    w1.gaps_count - COALESCE(w2.gaps_count, 0) AS increase
FROM weekly_gaps w1
LEFT JOIN weekly_gaps w2 ON w2.week_start < w1.week_start
ORDER BY w1.week_start DESC
LIMIT 1;
```

**Umbral:** Aumento > 20% semana a semana

---

### 2. Total gaps > umbral

**Query:**
```sql
SELECT 
    COUNT(*) AS total_gaps,
    SUM(expected_amount) AS total_amount
FROM ops.v_cabinet_claims_gap_14d
WHERE gap_reason = 'MILESTONE_ACHIEVED_NO_CLAIM'
    AND lead_date >= CURRENT_DATE - INTERVAL '21 days'
```

**Umbral:**
- `total_gaps > 50` (alerta warning)
- `total_gaps > 100` (alerta critical)
- `total_amount > 5000` (alerta critical por monto)

---

### 3. % drivers con trips sin claim

**Query:**
```sql
WITH drivers_with_trips AS (
    SELECT COUNT(DISTINCT driver_id) AS total
    FROM ops.v_cabinet_financial_14d
    WHERE total_trips_14d > 0
        AND lead_date >= CURRENT_DATE - INTERVAL '21 days'
),
drivers_without_claims AS (
    SELECT COUNT(DISTINCT driver_id) AS gaps
    FROM ops.v_cabinet_claims_gap_14d
    WHERE gap_reason = 'MILESTONE_ACHIEVED_NO_CLAIM'
        AND lead_date >= CURRENT_DATE - INTERVAL '21 days'
)
SELECT 
    dwt.total,
    dwc.gaps,
    CASE 
        WHEN dwt.total > 0 
        THEN ROUND(100.0 * dwc.gaps / dwt.total, 2)
        ELSE 0
    END AS pct_without_claims
FROM drivers_with_trips dwt
CROSS JOIN drivers_without_claims dwc;
```

**Umbral:** `pct_without_claims > 10%`

---

### 4. Lag promedio de claim

**Query:**
```sql
SELECT 
    AVG(CURRENT_DATE - lead_date) AS avg_lag_days
FROM ops.v_cabinet_claims_gap_14d
WHERE gap_reason = 'MILESTONE_ACHIEVED_NO_CLAIM'
    AND lead_date >= CURRENT_DATE - INTERVAL '21 days'
```

**Umbral:** `avg_lag_days > 7` días

---

## Script de Alerta

```python
#!/usr/bin/env python3
"""Script para verificar alertas de claims gap."""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
import sys

DATABASE_URL = os.getenv("DATABASE_URL", "...")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

try:
    # Alerta 1: Total gaps > umbral
    result = session.execute(text("""
        SELECT 
            COUNT(*) AS total_gaps,
            SUM(expected_amount) AS total_amount
        FROM ops.v_cabinet_claims_gap_14d
        WHERE gap_reason = 'MILESTONE_ACHIEVED_NO_CLAIM'
            AND lead_date >= CURRENT_DATE - INTERVAL '21 days'
    """))
    
    row = result.fetchone()
    total_gaps = row.total_gaps or 0
    total_amount = float(row.total_amount or 0)
    
    if total_gaps > 100:
        print(f"ALERTA CRITICAL: total_gaps = {total_gaps} > 100")
        sys.exit(2)
    elif total_gaps > 50:
        print(f"ALERTA WARNING: total_gaps = {total_gaps} > 50")
        sys.exit(1)
    
    if total_amount > 5000:
        print(f"ALERTA CRITICAL: total_amount = {total_amount} > 5000")
        sys.exit(2)
    
    print("OK: No hay alertas")
    sys.exit(0)
    
finally:
    session.close()
```
