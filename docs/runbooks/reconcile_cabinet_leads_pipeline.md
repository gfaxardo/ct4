# Runbook: Reconcile Cabinet Leads Pipeline

**Job:** `backend/jobs/reconcile_cabinet_leads_pipeline.py`  
**Propósito:** Reconciliar leads de cabinet en limbo (procesar leads nuevos y rezagados)

---

## Descripción

Este job procesa leads de cabinet que están en limbo para intentar crear/actualizar `identity_links` y avanzar en el embudo. Procesa:

1. **Leads recientes:** Últimos 30 días (configurable)
2. **Leads rezagados:** Leads en limbo (`NO_IDENTITY`, `NO_DRIVER`, `TRIPS_NO_CLAIM`)

---

## Ejecución Manual

### Opción 1: Script Python Directo

```bash
cd backend
python jobs/reconcile_cabinet_leads_pipeline.py
```

### Opción 2: Desde Código Python

```python
from backend.jobs.reconcile_cabinet_leads_pipeline import ReconcileCabinetLeadsPipeline
from app.db import SessionLocal

db = SessionLocal()
try:
    pipeline = ReconcileCabinetLeadsPipeline(db)
    stats = pipeline.run_reconcile(
        process_recent=True,
        recent_days=30,
        process_limbo=True,
        limbo_stages=['NO_IDENTITY', 'NO_DRIVER', 'TRIPS_NO_CLAIM']
    )
    print(stats)
finally:
    db.close()
```

---

## Programación Automática

### Windows Task Scheduler

1. Crear tarea programada:
   - **Nombre:** `Reconcile Cabinet Leads Pipeline`
   - **Programa:** `python`
   - **Argumentos:** `C:\ruta\al\proyecto\backend\jobs\reconcile_cabinet_leads_pipeline.py`
   - **Directorio de inicio:** `C:\ruta\al\proyecto\backend`
   - **Frecuencia:** Cada 15 minutos o cada hora

### Linux Cron

```bash
# Cada 15 minutos
*/15 * * * * cd /ruta/al/proyecto/backend && python jobs/reconcile_cabinet_leads_pipeline.py >> /var/log/reconcile_cabinet.log 2>&1

# Cada hora
0 * * * * cd /ruta/al/proyecto/backend && python jobs/reconcile_cabinet_leads_pipeline.py >> /var/log/reconcile_cabinet.log 2>&1
```

### Docker/Cron Container

```dockerfile
# Agregar a docker-compose.yml
services:
  reconcile-cron:
    build: ./backend
    command: >
      sh -c "while true; do
        python jobs/reconcile_cabinet_leads_pipeline.py;
        sleep 900;
      done"
    environment:
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - db
```

---

## Frecuencia Recomendada

- **Desarrollo/Testing:** Cada 15 minutos
- **Producción:** Cada hora (o cada 15 minutos si hay alto volumen de leads)

**Razón:** 
- Leads nuevos deben procesarse rápidamente (dentro de 15-60 minutos)
- Leads rezagados pueden procesarse con menor frecuencia (cada hora es suficiente)

---

## Validación de Resultados

### 1. Verificar Métricas del Job

El job loggea métricas:
- `processed`: Leads procesados
- `newly_linked`: Nuevos identity_links creados
- `newly_driver_mapped`: Nuevos driver_id mapeados
- `still_no_candidates`: Leads que aún no se pueden matchear
- `conflicts`: Leads con conflictos (AMBIGUOUS)
- `errors`: Errores encontrados

### 2. Consultar Vista Limbo

```sql
-- Verificar distribución de limbo después del job
SELECT 
    limbo_stage,
    COUNT(*) AS count,
    COUNT(*) FILTER (WHERE lead_date > CURRENT_DATE - INTERVAL '30 days') AS recent
FROM ops.v_cabinet_leads_limbo
GROUP BY limbo_stage
ORDER BY count DESC;
```

**Resultado esperado:**
- `limbo_no_identity` debería reducirse si hay leads nuevos con datos suficientes
- `limbo_no_driver` puede aumentar si hay nuevos person_key sin driver_id aún

### 3. Consultar Auditoría Semanal

```sql
-- Verificar últimas semanas
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
LIMIT 4;
```

**Resultado esperado:**
- `limbo_no_identity` debería reducirse en semanas recientes
- `limbo_ok` debería aumentar si hay leads que avanzaron

### 4. Verificar Leads Post-05

```sql
-- Debe retornar 62 (baseline)
SELECT COUNT(*) 
FROM ops.v_cabinet_leads_limbo
WHERE lead_date > '2026-01-05';

-- Verificar distribución
SELECT 
    limbo_stage,
    COUNT(*)
FROM ops.v_cabinet_leads_limbo
WHERE lead_date > '2026-01-05'
GROUP BY limbo_stage;
```

---

## Troubleshooting

### Job No Reduce limbo_no_identity

**Causa:** Leads no tienen datos suficientes para matching (NO_CANDIDATES).

**Verificación:**
```sql
SELECT reason_code, COUNT(*)
FROM canon.identity_unmatched
WHERE source_table = 'module_ct_cabinet_leads'
    AND snapshot_date > CURRENT_DATE - INTERVAL '7 days'
GROUP BY reason_code;
```

**Solución:** Estos leads requieren resolución manual o datos adicionales. No es un bug del job.

### Job Tarda Mucho

**Causa:** Muchos leads a procesar.

**Solución:** 
- Reducir `recent_days` (ej: 7 días en lugar de 30)
- Limitar `get_limbo_leads` (ya está limitado a 500)
- Ejecutar en horarios de bajo tráfico

### Errores de Concurrencia

**Causa:** Múltiples instancias del job ejecutándose simultáneamente.

**Solución:**
- Usar lock file o semáforo
- Verificar si hay otra instancia corriendo antes de iniciar
- Usar `pg_advisory_lock` en PostgreSQL

---

## Monitoreo

### Alertas Recomendadas

1. **limbo_no_identity aumenta:** Más de X leads sin identity en última semana
2. **limbo_trips_no_claim aumenta:** Más de X leads con milestones pero sin claims
3. **Job falla:** Error en ejecución del job
4. **Job no corre:** No se ejecutó en las últimas 2 horas

### Dashboard Recomendado

- Distribución de limbo por semana (gráfico de barras)
- Tendencias de limbo_no_identity, limbo_no_driver, limbo_trips_no_claim
- Métricas del job (processed, newly_linked, errors)

---

## Notas

- El job **NO rompe C0** (reglas canónicas de identidad)
- Si hay conflicto (AMBIGUOUS), marca y deja evidencia en `identity_unmatched`
- El job es **idempotente**: puede ejecutarse múltiples veces sin efectos secundarios
- El job es **incremental**: solo procesa leads que necesitan procesamiento
