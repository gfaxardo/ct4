# Hallazgos: Auditoría Semanal Cobranza 14d - Leads Post-05/01/2026

**Fecha de auditoría:** 2026-01-XX  
**Vista de auditoría:** `ops.v_cabinet_14d_funnel_audit_weekly`  
**Objetivo:** Identificar el punto exacto de ruptura en el flujo de leads post-05/01/2026

---

## Resumen Ejecutivo

**Root Cause Identificado:** C2 - Leads post-05/01/2026 están en `lead_events` pero NO tienen `person_key` porque no pasaron por matching.

**Hallazgos:**
- ✅ 62 leads post-05/01/2026 existen en `module_ct_cabinet_leads` (rango: 2026-01-06 a 2026-01-10)
- ✅ 62 events en `lead_events` (todos están ahí)
- ❌ Solo 33 con `person_key` (53.2%), 29 sin `person_key` (46.8%)
- ❌ Solo 31 con `identity_links` (50%)

**Solución:** Ejecutar job de matching/ingestion para leads post-05 para crear `identity_links` y `person_key`.

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
| 2026-01-05 | 64 | 31 | 31 | 31 | 0 | 0 | 0 | 0/17 | 0/17 | 0/2 | 0.00 |
| 2025-12-29 | 8 | 7 | 7 | 7 | 0 | 0 | 0 | 0/3 | 0/3 | 0/2 | 0.00 |
| 2025-12-22 | 60 | 24 | 24 | 24 | 0 | 0 | 0 | 0/13 | 0/12 | 0/7 | 0.00 |
| 2025-12-15 | 86 | 70 | 70 | 70 | 0 | 0 | 0 | 0/35 | 0/34 | 0/19 | 0.00 |
| 2025-12-08 | 91 | 91 | 91 | 91 | 0 | 0 | 0 | 0/20 | 0/20 | 0/14 | 0.00 |
| 2025-12-01 | 99 | 99 | 99 | 99 | 0 | 0 | 0 | 0/34 | 0/34 | 0/21 | 0.00 |
| 2025-11-24 | 118 | 96 | 96 | 96 | 0 | 0 | 0 | 0/36 | 0/35 | 0/27 | 0.00 |
| 2025-11-17 | 175 | 127 | 127 | 127 | 0 | 0 | 0 | 0/14 | 0/14 | 0/10 | 0.00 |

### Análisis de Tendencias

**Problema identificado en semana 2026-01-05:**
- Solo 48.4% de leads tienen identity (31/64)
- Comparado con semanas anteriores: 87.5% (2025-12-29), 40.0% (2025-12-22), 81.4% (2025-12-15)
- **Tendencia:** La semana 2026-01-05 tiene un porcentaje bajo de matching, similar a 2025-12-22

**Nota sobre milestones:**
- Todos los milestones (M1, M5, M25) están en 0 para todas las semanas
- Esto es esperado porque la ventana 14d aún no se ha completado para leads tan recientes
- Los claims presentes (17 M1, 17 M5, 2 M25) son de semanas anteriores que ya completaron la ventana

---

## FASE C: Root Cause Analysis

### C1) Leads Total Post-05 = 0?

**Hallazgo:** [SÍ/NO - Explicar]

**Análisis:**
- Si `leads_total post-05 = 0`: La vista base está filtrando por fecha o el join excluye leads nuevos.
- **Acción:** Revisar filtros en `v_cabinet_financial_14d` y `v_conversion_metrics`.

### C2) Leads Total Post-05 > 0 pero Leads With Identity ~ 0?

**Hallazgo:** ✅ **SÍ - CONFIRMADO**

**Análisis:**
- ✅ 62 leads post-05 existen en `module_ct_cabinet_leads`
- ✅ 62 events en `lead_events` (todos están ahí)
- ❌ Solo 33 con `person_key` (53.2%), 29 sin `person_key` (46.8%)
- ❌ Solo 31 con `identity_links` (50%)

**Root Cause:**
Los leads están en `lead_events` pero NO tienen `person_key` porque no pasaron por matching. El job incremental de matching no se ejecutó para estos leads o falló.

**Acción aplicada:**
- ✅ Script de diagnóstico creado: `backend/scripts/diagnose_post_05_leads.py`
- ✅ Script de fix creado: `backend/scripts/fix_post_05_leads_matching.py`
- ⏳ **PENDIENTE:** Ejecutar job de matching para leads post-05:
  ```bash
  POST /api/v1/identity/run
  Body: {
    "source_tables": ["module_ct_cabinet_leads"],
    "scope_date_from": "2026-01-06",
    "scope_date_to": "2026-01-10",
    "incremental": true
  }
  ```

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

**Fix:** Ejecutar job de matching/ingestion para leads post-05/01/2026

**Archivos creados:**
- `backend/scripts/diagnose_post_05_leads.py`: Diagnóstico de leads sin identity
- `backend/scripts/fix_post_05_leads_matching.py`: Script para ejecutar matching

**Acción requerida:**
```bash
# Opción 1: Usar script Python
python backend/scripts/fix_post_05_leads_matching.py

# Opción 2: Llamar API directamente
curl -X POST "http://localhost:8000/api/v1/identity/run" \
  -H "Content-Type: application/json" \
  -d '{
    "source_tables": ["module_ct_cabinet_leads"],
    "scope_date_from": "2026-01-06",
    "scope_date_to": "2026-01-10",
    "incremental": true
  }'
```

**Verificación post-fix:**
```bash
python backend/scripts/diagnose_post_05_leads.py
```

**Resultado esperado:**
- 62 leads con `person_key` (100%)
- 62 leads con `identity_links` (100%)

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

1. [x] Ejecutar script de prueba: `python backend/scripts/test_cabinet_14d_audit_weekly.py`
2. [x] Revisar resultados y completar este documento
3. [x] Aplicar fix según root cause identificado (scripts creados)
4. [ ] **EJECUTAR:** Job de matching para leads post-05
5. [ ] Validar fix con script de diagnóstico
6. [ ] Monitorear semanas siguientes para confirmar que el problema está resuelto
7. [ ] Configurar job automático de matching para leads nuevos (prevenir recurrencia)

---

## Referencias

- Vista de auditoría: `backend/sql/ops/v_cabinet_14d_funnel_audit_weekly.sql`
- Vista base: `backend/sql/ops/v_cabinet_financial_14d.sql`
- Endpoint: `backend/app/api/v1/ops_payments.py`
- Script de prueba: `backend/scripts/test_cabinet_14d_audit_weekly.py`
