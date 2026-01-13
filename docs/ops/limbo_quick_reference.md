# Quick Reference: Limbo Cabinet Leads

## Comandos Rápidos

### Ver Limbo Actual

```sql
SELECT 
    limbo_stage,
    COUNT(*) AS count
FROM ops.v_cabinet_leads_limbo
GROUP BY limbo_stage
ORDER BY count DESC;
```

### Ver Auditoría Semanal

```sql
SELECT 
    week_start,
    leads_total,
    limbo_no_identity,
    limbo_trips_no_claim
FROM ops.v_cabinet_14d_funnel_audit_weekly
ORDER BY week_start DESC
LIMIT 8;
```

### Ejecutar Job de Reconciliación

```bash
cd backend
python -m jobs.reconcile_cabinet_leads_pipeline --days-back 30 --limit 2000
```

### Verificar Alertas

```bash
cd backend
python scripts/check_limbo_alerts.py
```

### Ver Leads Post-05

```sql
SELECT 
    week_start,
    COUNT(*) AS count
FROM ops.v_cabinet_leads_limbo
WHERE lead_date > '2026-01-05'
GROUP BY week_start
ORDER BY week_start DESC;
```

---

## Endpoints API

### GET Limbo

```
GET /api/v1/ops/payments/cabinet-financial-14d/limbo?limbo_stage=NO_IDENTITY&week_start=2026-01-06&limit=100&offset=0
```

### Export Limbo CSV

```
GET /api/v1/ops/payments/cabinet-financial-14d/limbo/export?limbo_stage=NO_IDENTITY&limit=10000
```

---

## Archivos Clave

- Vista limbo: `backend/sql/ops/v_cabinet_leads_limbo.sql`
- Auditoría semanal: `backend/sql/ops/v_cabinet_14d_funnel_audit_weekly.sql`
- Job: `backend/jobs/reconcile_cabinet_leads_pipeline.py`
- Script alertas: `backend/scripts/check_limbo_alerts.py`
- UI: `frontend/components/CabinetLimboSection.tsx`

---

## Documentación Completa

- Entrega: `docs/ops/LIMBO_END_TO_END_DELIVERY.md`
- Scheduling: `docs/runbooks/scheduling_reconcile_cabinet_leads_pipeline.md`
- Alertas: `docs/ops/limbo_alerts.md`
- Monitoreo: `docs/ops/limbo_monitoring_guide.md`
- Evidencia: `docs/ops/limbo_fix_evidence.md`
