# Scheduling: Reconcile Cabinet Leads Pipeline

## Propósito

Este documento describe cómo programar el job `reconcile_cabinet_leads_pipeline.py` para que se ejecute automáticamente de forma recurrente.

---

## Frecuencia Recomendada

- **Producción:** Cada 15 minutos (para leads nuevos)
- **Desarrollo/Testing:** Cada hora o manualmente

---

## Opción 1: Windows Task Scheduler

### Pasos

1. Abrir **Task Scheduler** (Programador de tareas)
2. Crear nueva tarea básica
3. Configurar:
   - **Nombre:** `Reconcile Cabinet Leads Pipeline`
   - **Descripción:** `Job recurrente para reconciliar leads de cabinet en limbo`
   - **Trigger:** Repetir cada 15 minutos
   - **Acción:** Iniciar programa
   - **Programa/script:** `python.exe`
   - **Argumentos:** `-m jobs.reconcile_cabinet_leads_pipeline --days-back 30 --limit 2000`
   - **Iniciar en:** `C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend`

### Comando Completo

```powershell
# Desde PowerShell (como administrador)
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "-m jobs.reconcile_cabinet_leads_pipeline --days-back 30 --limit 2000" -WorkingDirectory "C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 15) -RepetitionDuration (New-TimeSpan -Days 365)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive
Register-ScheduledTask -TaskName "Reconcile Cabinet Leads Pipeline" -Action $action -Trigger $trigger -Principal $principal -Description "Job recurrente para reconciliar leads de cabinet en limbo"
```

---

## Opción 2: Cron (Linux/Mac)

### Crontab

```bash
# Editar crontab
crontab -e

# Agregar línea (cada 15 minutos)
*/15 * * * * cd /path/to/ct4/backend && python -m jobs.reconcile_cabinet_leads_pipeline --days-back 30 --limit 2000 >> /var/log/reconcile_cabinet_leads.log 2>&1
```

---

## Opción 3: Script Batch (Windows)

Crear `backend/scripts/run_reconcile_cabinet_leads.bat`:

```batch
@echo off
cd /d "%~dp0\.."
python -m jobs.reconcile_cabinet_leads_pipeline --days-back 30 --limit 2000
```

Luego programar este script en Task Scheduler.

---

## Validación

### Verificar que el job corre

```sql
-- Verificar logs o métricas en BD
SELECT * FROM canon.ingestion_runs 
WHERE source_tables::text LIKE '%module_ct_cabinet_leads%'
ORDER BY created_at DESC
LIMIT 10;
```

### Verificar reducción de limbo

```sql
-- Antes y después del job
SELECT 
    limbo_stage,
    COUNT(*) AS count
FROM ops.v_cabinet_leads_limbo
GROUP BY limbo_stage
ORDER BY count DESC;
```

---

## Monitoreo

- Revisar logs del job (stdout/stderr)
- Monitorear `ops.v_cabinet_leads_limbo` para ver reducción de limbo
- Alertar si `limbo_no_identity` o `limbo_trips_no_claim` aumentan (ver `docs/ops/limbo_alerts.md`)

---

## Troubleshooting

### El job no corre

1. Verificar que Python está en PATH
2. Verificar permisos de ejecución
3. Verificar que la BD es accesible
4. Revisar logs de Task Scheduler

### El job corre pero no reduce limbo

1. Verificar que hay leads nuevos o en limbo
2. Verificar que el matching engine está funcionando
3. Revisar logs del job para errores
4. Ejecutar manualmente con `--dry-run` para debug

---

## Referencias

- Job: `backend/jobs/reconcile_cabinet_leads_pipeline.py`
- Runbook: `docs/runbooks/reconcile_cabinet_leads_pipeline.md`
- Vista limbo: `ops.v_cabinet_leads_limbo`
