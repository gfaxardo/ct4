# Alertas: Limbo Cabinet Leads

## Propósito

Este documento define alertas mínimas para monitorear el estado del limbo de leads de cabinet.

---

## Métricas a Monitorear

### 1. Limbo por Stage (Semanal)

**Query:**

```sql
SELECT 
    week_start,
    limbo_no_identity,
    limbo_no_driver,
    limbo_no_trips_14d,
    limbo_trips_no_claim,
    limbo_ok
FROM ops.v_cabinet_14d_funnel_audit_weekly
ORDER BY week_start DESC
LIMIT 8;
```

**Alerta si:**
- `limbo_no_identity` aumenta semana a semana (umbral: +10%)
- `limbo_trips_no_claim` aumenta semana a semana (umbral: +5%)

---

### 2. Total Limbo (Global)

**Query:**

```sql
SELECT 
    limbo_stage,
    COUNT(*) AS count
FROM ops.v_cabinet_leads_limbo
GROUP BY limbo_stage
ORDER BY count DESC;
```

**Alerta si:**
- `limbo_no_identity` > 100 (umbral absoluto)
- `limbo_trips_no_claim` > 50 (umbral absoluto)

---

### 3. Tasa de Conversión (Semanal)

**Query:**

```sql
SELECT 
    week_start,
    leads_total,
    leads_with_identity,
    pct_with_identity,
    leads_with_driver,
    pct_with_driver
FROM ops.v_cabinet_14d_funnel_audit_weekly
ORDER BY week_start DESC
LIMIT 4;
```

**Alerta si:**
- `pct_with_identity` < 80% (tasa de matching baja)
- `pct_with_driver` < 70% (tasa de driver mapping baja)

---

## Script de Alerta (Python)

Crear `backend/scripts/check_limbo_alerts.py`:

```python
#!/usr/bin/env python3
"""
Script para verificar alertas de limbo y enviar notificaciones.
"""

import sys
import os
from pathlib import Path
from datetime import date, timedelta

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"
)

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

alerts = []

try:
    # 1. Verificar limbo semanal (últimas 2 semanas)
    query = text("""
        SELECT 
            week_start,
            limbo_no_identity,
            limbo_trips_no_claim
        FROM ops.v_cabinet_14d_funnel_audit_weekly
        ORDER BY week_start DESC
        LIMIT 2
    """)
    result = session.execute(query)
    weeks = result.fetchall()
    
    if len(weeks) >= 2:
        current = weeks[0]
        previous = weeks[1]
        
        # Alerta si limbo_no_identity aumenta > 10%
        if previous.limbo_no_identity > 0:
            increase_pct = ((current.limbo_no_identity - previous.limbo_no_identity) / previous.limbo_no_identity) * 100
            if increase_pct > 10:
                alerts.append(f"WARN: limbo_no_identity aumentó {increase_pct:.1f}% semana a semana (semana {current.week_start})")
        
        # Alerta si limbo_trips_no_claim aumenta > 5%
        if previous.limbo_trips_no_claim > 0:
            increase_pct = ((current.limbo_trips_no_claim - previous.limbo_trips_no_claim) / previous.limbo_trips_no_claim) * 100
            if increase_pct > 5:
                alerts.append(f"WARN: limbo_trips_no_claim aumentó {increase_pct:.1f}% semana a semana (semana {current.week_start})")
    
    # 2. Verificar totales absolutos
    query = text("""
        SELECT 
            COUNT(*) FILTER (WHERE limbo_stage = 'NO_IDENTITY') AS limbo_no_identity,
            COUNT(*) FILTER (WHERE limbo_stage = 'TRIPS_NO_CLAIM') AS limbo_trips_no_claim
        FROM ops.v_cabinet_leads_limbo
    """)
    result = session.execute(query)
    row = result.fetchone()
    
    if row.limbo_no_identity > 100:
        alerts.append(f"WARN: limbo_no_identity total = {row.limbo_no_identity} (umbral: 100)")
    
    if row.limbo_trips_no_claim > 50:
        alerts.append(f"WARN: limbo_trips_no_claim total = {row.limbo_trips_no_claim} (umbral: 50)")
    
    # 3. Verificar tasa de conversión
    query = text("""
        SELECT 
            week_start,
            pct_with_identity,
            pct_with_driver
        FROM ops.v_cabinet_14d_funnel_audit_weekly
        ORDER BY week_start DESC
        LIMIT 1
    """)
    result = session.execute(query)
    row = result.fetchone()
    
    if row and row.pct_with_identity < 80:
        alerts.append(f"WARN: pct_with_identity = {row.pct_with_identity:.1f}% (umbral: 80%)")
    
    if row and row.pct_with_driver < 70:
        alerts.append(f"WARN: pct_with_driver = {row.pct_with_driver:.1f}% (umbral: 70%)")
    
    # Imprimir alertas
    if alerts:
        print("=" * 80)
        print("ALERTAS DE LIMBO")
        print("=" * 80)
        for alert in alerts:
            print(alert)
        print("=" * 80)
        sys.exit(1)
    else:
        print("OK: No hay alertas de limbo")
        sys.exit(0)
        
finally:
    session.close()
```

---

## Scheduling de Alertas

### Windows Task Scheduler

Programar `check_limbo_alerts.py` para ejecutarse cada hora:

```powershell
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "scripts/check_limbo_alerts.py" -WorkingDirectory "C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 365)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
Register-ScheduledTask -TaskName "Check Limbo Alerts" -Action $action -Trigger $trigger -Principal $principal -Description "Verifica alertas de limbo cada hora"
```

### Cron (Linux)

```bash
# Cada hora
0 * * * * cd /path/to/ct4/backend && python scripts/check_limbo_alerts.py >> /var/log/limbo_alerts.log 2>&1
```

---

## Notificaciones

El script puede extenderse para enviar:
- Email
- Slack
- Teams
- PagerDuty

---

## Referencias

- Vista limbo: `ops.v_cabinet_leads_limbo`
- Auditoría semanal: `ops.v_cabinet_14d_funnel_audit_weekly`
- Job de reconciliación: `backend/jobs/reconcile_cabinet_leads_pipeline.py`
