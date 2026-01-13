# Hallazgos: Auditoría Semanal Cobranza 14d - Leads Post-05/01/2026

**Fecha de auditoría:** [FECHA]  
**Vista de auditoría:** `ops.v_cabinet_14d_funnel_audit_weekly`  
**Objetivo:** Identificar el punto exacto de ruptura en el flujo de leads post-05/01/2026

---

## Resumen Ejecutivo

[RESUMEN DE HALLAZGOS PRINCIPALES]

---

## FASE A: Identificación del Universo Base

### A1) Endpoint y Vista Base

- **Endpoint:** `GET /api/v1/ops/payments/cabinet-financial-14d`
- **Vista base:** `ops.v_cabinet_financial_14d`
- **Fuente de lead_date:** `observational.v_conversion_metrics` (derivado de `observational.lead_events`)

### A2) Tabla Base de Leads Cabinet

- **Tabla RAW:** `public.module_ct_cabinet_leads`
- **Columna anchor:** `lead_created_at::date` (mapeado a `event_date` en `lead_events`)
- **source_pk:** `COALESCE(external_id::text, id::text)`

---

## FASE B: Resultados de Auditoría Semanal

### Query de Prueba

```sql
SELECT *
FROM ops.v_cabinet_14d_funnel_audit_weekly
ORDER BY week_start DESC
LIMIT 8;
```

### Resultados por Semana

| Semana | Leads Total | Con Identity | Con Driver | Con Trips 14d | M1 | M5 | M25 | Claims M1 (exp/pres) | Claims M5 (exp/pres) | Claims M25 (exp/pres) | Deuda Esperada |
|--------|-------------|--------------|------------|---------------|----|----|-----|---------------------|---------------------|----------------------|----------------|
| [SEMANA] | [N] | [N] | [N] | [N] | [N] | [N] | [N] | [N]/[N] | [N]/[N] | [N]/[N] | [MONTO] |

### Análisis de Tendencias

[ANÁLISIS DE TENDENCIAS POR SEMANA]

---

## FASE C: Root Cause Analysis

### C1) Leads Total Post-05 = 0?

**Hallazgo:** [SÍ/NO - Explicar]

**Análisis:**
- Si `leads_total post-05 = 0`: La vista base está filtrando por fecha o el join excluye leads nuevos.
- **Acción:** Revisar filtros en `v_cabinet_financial_14d` y `v_conversion_metrics`.

### C2) Leads Total Post-05 > 0 pero Leads With Identity ~ 0?

**Hallazgo:** [SÍ/NO - Explicar]

**Análisis:**
- Si `leads_with_identity post-05 ~ 0`: Los leads no están pasando por matching o el `source_pk` no coincide.
- **Acción:** 
  - Verificar que `populate_events_from_cabinet` se ejecutó para fechas post-05
  - Verificar que `source_pk` en `identity_links` coincide con `COALESCE(external_id::text, id::text)`
  - Verificar que el job incremental de matching procesa nuevos leads

### C3) Identity OK pero Driver OK = 0?

**Hallazgo:** [SÍ/NO - Explicar]

**Análisis:**
- Si `leads_with_driver post-05 = 0`: No hay `identity_link` desde `person_key` a `drivers`.
- **Acción:**
  - Verificar join `person_key → driver_id` en `v_conversion_metrics`
  - Verificar que existen `identity_links` con `source_table='drivers'` para estos `person_key`

### C4) Driver OK pero Milestones 14d = 0?

**Hallazgo:** [SÍ/NO - Explicar]

**Análisis:**
- Si `drivers_with_trips_14d post-05 = 0`: No hay viajes en `summary_daily` dentro de ventana 14d desde `lead_date`.
- **Acción:**
  - Verificar que `lead_date` no es NULL
  - Verificar que `summary_daily` tiene datos para estos drivers en la ventana 14d
  - Verificar join a `summary_daily` en `v_cabinet_financial_14d`

### C5) Milestones OK pero Claims Present = 0?

**Hallazgo:** [SÍ/NO - Explicar]

**Análisis:**
- Si `reached_m1_14d > 0` pero `claims_present_m1 = 0`: Bug en generación de claims o filtro indebido.
- **Acción:**
  - Verificar que `v_claims_payment_status_cabinet` no filtra por "solo si pagado"
  - Verificar que claims se generan independientemente de M1/M5/M25
  - Verificar dependencias en `v_payment_calculation`

---

## FASE D: Fix Aplicado

### D1) Cambio Mínimo Aplicado

[DESCRIPCIÓN DEL FIX APLICADO]

**Archivos modificados:**
- [ARCHIVO 1]: [DESCRIPCIÓN]
- [ARCHIVO 2]: [DESCRIPCIÓN]

**SQL ejecutado:**
```sql
[SQL DEL FIX]
```

### D2) Test/Guardrail Añadido

[DESCRIPCIÓN DEL TEST/GUARDRAIL]

**Query de validación:**
```sql
[QUERY DE VALIDACIÓN]
```

---

## FASE E: UI Orden Semanal

### E1) Cambios Aplicados

- **Endpoint:** `GET /api/v1/ops/payments/cabinet-financial-14d`
- **Orden anterior:** `ORDER BY lead_date DESC NULLS LAST, driver_id`
- **Orden nuevo:** `ORDER BY week_start DESC NULLS LAST, lead_date DESC NULLS LAST, driver_id`
- **Vista actualizada:** `ops.v_cabinet_financial_14d` ahora incluye columna `week_start`

**Archivos modificados:**
- `backend/sql/ops/v_cabinet_financial_14d.sql`: Agregada columna `week_start`
- `backend/app/api/v1/ops_payments.py`: Actualizado `ORDER BY` en queries

---

## Validación Post-Fix

### Query de Validación

```sql
-- Verificar que semanas post-05 aparecen en auditoría
SELECT 
    week_start,
    leads_total,
    leads_with_identity,
    leads_with_driver,
    drivers_with_trips_14d,
    reached_m1_14d,
    claims_expected_m1,
    claims_present_m1
FROM ops.v_cabinet_14d_funnel_audit_weekly
WHERE week_start >= '2026-01-05'
ORDER BY week_start DESC;
```

### Resultados Esperados

- [ ] Semanas post-05 aparecen en `leads_total`
- [ ] `leads_with_identity` > 0 para semanas post-05
- [ ] `leads_with_driver` > 0 para semanas post-05
- [ ] `drivers_with_trips_14d` > 0 si hay viajes
- [ ] `claims_expected_m1` = `claims_present_m1` (sin gaps)

---

## Próximos Pasos

1. [ ] Ejecutar script de prueba: `python backend/scripts/test_cabinet_14d_audit_weekly.py`
2. [ ] Revisar resultados y completar este documento
3. [ ] Aplicar fix según root cause identificado
4. [ ] Validar fix con query de validación
5. [ ] Monitorear semanas siguientes para confirmar que el problema está resuelto

---

## Referencias

- Vista de auditoría: `backend/sql/ops/v_cabinet_14d_funnel_audit_weekly.sql`
- Vista base: `backend/sql/ops/v_cabinet_financial_14d.sql`
- Endpoint: `backend/app/api/v1/ops_payments.py`
- Script de prueba: `backend/scripts/test_cabinet_14d_audit_weekly.py`
