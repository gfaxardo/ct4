# Guía de Monitoreo: Limbo Cabinet Leads

## Propósito

Esta guía describe cómo monitorear el sistema LIMBO de forma continua.

---

## Métricas Clave

### 1. Limbo por Stage (Diario)

**Query:**

```sql
SELECT 
    limbo_stage,
    COUNT(*) AS count
FROM ops.v_cabinet_leads_limbo
GROUP BY limbo_stage
ORDER BY count DESC;
```

**Objetivo:**
- `limbo_no_identity` < 100
- `limbo_trips_no_claim` < 50
- `limbo_ok` debe aumentar con el tiempo

---

### 2. Auditoría Semanal (Cada Lunes)

**Query:**

```sql
SELECT 
    week_start,
    leads_total,
    leads_with_identity,
    leads_with_driver,
    drivers_with_trips_14d,
    limbo_no_identity,
    limbo_no_driver,
    limbo_no_trips_14d,
    limbo_trips_no_claim,
    limbo_ok,
    pct_with_identity,
    pct_with_driver
FROM ops.v_cabinet_14d_funnel_audit_weekly
ORDER BY week_start DESC
LIMIT 8;
```

**Objetivo:**
- `pct_with_identity` > 80%
- `pct_with_driver` > 70%
- `limbo_no_identity` no debe aumentar semana a semana
- `limbo_trips_no_claim` no debe aumentar semana a semana

---

### 3. Leads Post-05 (Validación Continua)

**Query:**

```sql
SELECT 
    COUNT(*) AS total_post_05,
    COUNT(*) FILTER (WHERE limbo_stage = 'NO_IDENTITY') AS no_identity,
    COUNT(*) FILTER (WHERE limbo_stage = 'TRIPS_NO_CLAIM') AS trips_no_claim
FROM ops.v_cabinet_leads_limbo
WHERE lead_date > '2026-01-05';
```

**Objetivo:**
- Todos los leads post-05 deben aparecer en limbo
- `no_identity` debe reducirse con el tiempo
- `trips_no_claim` debe reducirse con el tiempo

---

## Scripts de Monitoreo

### 1. Check Alerts (Automático)

**Ubicación:** `backend/scripts/check_limbo_alerts.py`

**Ejecución:**
```bash
cd backend
python scripts/check_limbo_alerts.py
```

**Scheduling:**
- Windows: Cada hora (Task Scheduler)
- Linux: Cron `0 * * * *`

---

### 2. Reconcile Job (Automático)

**Ubicación:** `backend/jobs/reconcile_cabinet_leads_pipeline.py`

**Ejecución:**
```bash
cd backend
python -m jobs.reconcile_cabinet_leads_pipeline --days-back 30 --limit 2000
```

**Scheduling:**
- Windows: Cada 15 minutos (Task Scheduler)
- Linux: Cron `*/15 * * * *`

---

## Dashboard de Monitoreo

### Métricas en UI

1. Navegar a `/pagos/cobranza-yango`
2. Ver sección "Leads en Limbo"
3. Revisar contadores por stage
4. Verificar que semanas recientes aparecen

---

## Alertas Configuradas

### Umbrales

- `limbo_no_identity` > 100 → ALERTA
- `limbo_trips_no_claim` > 50 → ALERTA
- `limbo_no_identity` aumenta > 10% semana a semana → ALERTA
- `limbo_trips_no_claim` aumenta > 5% semana a semana → ALERTA
- `pct_with_identity` < 80% → ADVERTENCIA
- `pct_with_driver` < 70% → ADVERTENCIA

---

## Acciones Correctivas

### Si `limbo_no_identity` aumenta:

1. Verificar que el job de reconciliación está corriendo
2. Revisar logs del job para errores
3. Ejecutar job manualmente: `python -m jobs.reconcile_cabinet_leads_pipeline --only-limbo`
4. Verificar que hay datos suficientes para matching (phone, license, etc.)

### Si `limbo_trips_no_claim` aumenta:

1. Verificar que el job `reconcile_cabinet_claims_14d` está corriendo
2. Revisar logs del job de claims
3. Ejecutar job manualmente: `python -m jobs.reconcile_cabinet_claims_14d`
4. Verificar que los milestones se están alcanzando correctamente

### Si `pct_with_identity` < 80%:

1. Revisar calidad de datos en `module_ct_cabinet_leads`
2. Verificar que el matching engine está funcionando
3. Revisar `canon.identity_unmatched` para ver razones

---

## Reportes Semanales

### Query de Reporte

```sql
SELECT 
    week_start,
    leads_total,
    leads_with_identity,
    leads_with_driver,
    drivers_with_trips_14d,
    limbo_no_identity,
    limbo_no_driver,
    limbo_no_trips_14d,
    limbo_trips_no_claim,
    limbo_ok,
    pct_with_identity,
    pct_with_driver,
    pct_with_trips_14d
FROM ops.v_cabinet_14d_funnel_audit_weekly
WHERE week_start >= DATE_TRUNC('week', CURRENT_DATE - INTERVAL '4 weeks')::date
ORDER BY week_start DESC;
```

**Generar cada lunes y compartir con el equipo.**

---

## Referencias

- Vista limbo: `ops.v_cabinet_leads_limbo`
- Auditoría semanal: `ops.v_cabinet_14d_funnel_audit_weekly`
- Job de reconciliación: `backend/jobs/reconcile_cabinet_leads_pipeline.py`
- Script de alertas: `backend/scripts/check_limbo_alerts.py`
- Scheduling: `docs/runbooks/scheduling_reconcile_cabinet_leads_pipeline.md`
- Alertas: `docs/ops/limbo_alerts.md`
