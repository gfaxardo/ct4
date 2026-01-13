# Runbook: Reconcile Cabinet Claims 14d

**Job:** `backend/jobs/reconcile_cabinet_claims_14d.py`  
**Propósito:** Reconciliar claims de cabinet 14d faltantes (drivers con milestones pero sin claims)

---

## Descripción

Este job identifica drivers con milestones alcanzados dentro de ventana 14d pero SIN claim correspondiente. Los claims son vistas calculadas dinámicamente, por lo que el job:

1. Identifica gaps desde `ops.v_cabinet_claims_gap_14d`
2. Verifica condiciones canónicas (milestone achieved, driver_id, lead_date)
3. Refresca vistas materializadas relacionadas (si existen)
4. Verifica si los gaps se resolvieron después del refresh

---

## Ejecución Manual

### Opción 1: Script Python Directo

```bash
cd backend
python -m jobs.reconcile_cabinet_claims_14d --days-back 21 --limit 1000
```

### Opción 2: Desde Código Python

```python
from backend.jobs.reconcile_cabinet_claims_14d import ReconcileCabinetClaims14d
from app.db import SessionLocal

db = SessionLocal()
try:
    pipeline = ReconcileCabinetClaims14d(db)
    result = pipeline.run_reconcile(
        days_back=21,
        limit=1000,
        only_gaps=True,
        dry_run=False
    )
    print(result)
finally:
    db.close()
```

---

## Parámetros

- `--days-back`: Días hacia atrás para procesar (default: 21)
- `--limit`: Límite de gaps a procesar (default: 1000)
- `--only-gaps`: Solo procesar gaps (claim_status=MISSING)
- `--dry-run`: Modo dry-run (no ejecuta acciones, solo muestra qué se procesaría)
- `--output-json`: Ruta para guardar resultados en JSON
- `--output-csv`: Ruta para guardar resultados en CSV

---

## Programación Automática

### Linux Cron

```bash
# Cada hora
0 * * * * cd /ruta/al/proyecto/backend && python -m jobs.reconcile_cabinet_claims_14d --days-back 21 --limit 1000 >> /var/log/reconcile_claims.log 2>&1

# Cada 15 minutos (si hay alto volumen)
*/15 * * * * cd /ruta/al/proyecto/backend && python -m jobs.reconcile_cabinet_claims_14d --days-back 21 --limit 500 >> /var/log/reconcile_claims.log 2>&1
```

### Windows Task Scheduler

```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "-m jobs.reconcile_cabinet_claims_14d --days-back 21 --limit 1000" -WorkingDirectory "C:\ruta\al\proyecto\backend"
$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 60) -RepetitionDuration (New-TimeSpan -Days 365) -Once -At (Get-Date)
Register-ScheduledTask -TaskName "Reconcile Cabinet Claims 14d" -Action $action -Trigger $trigger
```

---

## Validación de Resultados

### 1. Verificar Gaps Después del Job

```sql
-- Debe reducirse después del job
SELECT 
    gap_reason,
    COUNT(*) AS count
FROM ops.v_cabinet_claims_gap_14d
WHERE lead_date >= CURRENT_DATE - INTERVAL '21 days'
GROUP BY gap_reason
ORDER BY count DESC;
```

### 2. Verificar Claims Generados

```sql
-- Verificar si los gaps se resolvieron
SELECT 
    cg.driver_id,
    cg.milestone_value,
    cg.lead_date,
    cg.gap_reason,
    CASE WHEN c.driver_id IS NOT NULL THEN 'RESUELTO' ELSE 'PENDIENTE' END AS status
FROM ops.v_cabinet_claims_gap_14d cg
LEFT JOIN ops.v_claims_payment_status_cabinet c
    ON c.driver_id = cg.driver_id
    AND c.milestone_value = cg.milestone_value
    AND c.lead_date = cg.lead_date
WHERE cg.lead_date >= CURRENT_DATE - INTERVAL '21 days'
    AND cg.claim_status = 'MISSING'
ORDER BY cg.lead_date DESC
LIMIT 20;
```

### 3. Métricas del Job

El job loggea métricas:
- `processed`: Gaps procesados
- `gaps_found`: Gaps encontrados
- `claims_should_exist`: Gaps que deben generarse
- `claims_already_exist`: Gaps que ya tienen claim (resueltos)
- `invalid_conditions`: Gaps que no deben generarse (condiciones no cumplidas)
- `refreshed_views`: Vistas materializadas refrescadas

---

## Troubleshooting

### Gaps No Se Resuelven Después del Refresh

**Causa:** Los datos upstream (`v_payment_calculation` o `v_cabinet_milestones_achieved_from_payment_calc`) no reflejan correctamente los milestones.

**Solución:**
1. Verificar que `v_payment_calculation` tiene los datos correctos para el driver/milestone
2. Verificar que `v_cabinet_milestones_achieved_from_payment_calc` refleja el milestone como achieved
3. Verificar que `summary_daily` tiene los viajes en la ventana 14d correcta

### Job Tarda Mucho

**Causa:** Muchos gaps a procesar o vistas materializadas grandes.

**Solución:**
- Reducir `--days-back` (ej: 7 días en lugar de 21)
- Reducir `--limit` (ej: 500 en lugar de 1000)
- Ejecutar en horarios de bajo tráfico

---

## Notas

- Los claims son vistas calculadas dinámicamente, no tablas físicas
- El job no "crea" claims directamente, sino que refresca vistas materializadas y verifica condiciones
- Si un gap persiste después del refresh, puede indicar un problema en los datos upstream
