# Scheduling: Reconcile Cabinet Claims 14d

**Job:** `backend/jobs/reconcile_cabinet_claims_14d.py`

---

## Opción A: Cron Linux

### Cada hora

```bash
0 * * * * cd /ruta/al/proyecto/backend && python -m jobs.reconcile_cabinet_claims_14d --days-back 21 --limit 1000 >> /var/log/reconcile_claims.log 2>&1
```

### Cada 15 minutos (si hay alto volumen)

```bash
*/15 * * * * cd /ruta/al/proyecto/backend && python -m jobs.reconcile_cabinet_claims_14d --days-back 21 --limit 500 >> /var/log/reconcile_claims.log 2>&1
```

---

## Opción B: Windows Task Scheduler

```powershell
$action = New-ScheduledTaskAction -Execute "python" -Argument "-m jobs.reconcile_cabinet_claims_14d --days-back 21 --limit 1000" -WorkingDirectory "C:\ruta\al\proyecto\backend"
$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 60) -RepetitionDuration (New-TimeSpan -Days 365) -Once -At (Get-Date)
Register-ScheduledTask -TaskName "Reconcile Cabinet Claims 14d" -Action $action -Trigger $trigger
```

---

## Parámetros Recomendados

### Producción (cada hora)
```bash
python -m jobs.reconcile_cabinet_claims_14d --days-back 21 --limit 1000
```

### Desarrollo/Testing
```bash
python -m jobs.reconcile_cabinet_claims_14d --days-back 7 --limit 500 --dry-run
```

---

## Verificación Post-Run

```sql
-- Verificar gaps después del job
SELECT 
    gap_reason,
    COUNT(*) AS count,
    SUM(expected_amount) AS total_amount
FROM ops.v_cabinet_claims_gap_14d
WHERE lead_date >= CURRENT_DATE - INTERVAL '21 days'
GROUP BY gap_reason
ORDER BY count DESC;
```
