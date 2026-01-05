# Auditoría: Fuentes de Achieved en Driver Matrix

**Fecha:** 2025-01-XX  
**Objetivo:** Identificar exactamente de dónde sale el "achieved" que muestra Driver Matrix y por qué puede existir M5=true y M1=false, mientras que la vista determinística `ops.v_ct4_milestones_achieved_from_trips_eligible` ya garantiza consistencia.

---

## Resumen Ejecutivo

**Conclusión:** Driver Matrix **NO usa achieved determinístico por viajes**. Usa `ops.v_payment_calculation` que calcula achieved basado en **reglas de pago con ventanas** y **lead_date**, lo que permite inconsistencias como M5 achieved sin M1 achieved.

---

## Cadena de Dependencias

### 1. Vista UI: `ops.v_payments_driver_matrix_cabinet`

**Archivo:** `backend/sql/ops/v_payments_driver_matrix_cabinet.sql`

**Propósito:** Vista de PRESENTACIÓN que muestra 1 fila por driver con columnas por milestones M1/M5/M25.

**Fuente de achieved:**
```sql
-- Líneas 115-116, 122-123, 129-130
BOOL_OR(bc.milestone_value = 1) AS m1_achieved_flag,
BOOL_OR(bc.milestone_value = 5) AS m5_achieved_flag,
BOOL_OR(bc.milestone_value = 25) AS m25_achieved_flag,
```

**Base de datos:** `base_claims` CTE que viene de `ops.v_claims_payment_status_cabinet`.

---

### 2. Vista de Claims: `ops.v_claims_payment_status_cabinet`

**Archivo:** `backend/sql/ops/v_claims_payment_status_cabinet.sql`

**Propósito:** Vista orientada a cobranza que responde "¿nos pagaron o no?".

**Fuente de achieved:**
```sql
-- Líneas 33-54
SELECT 
    pc.driver_id,
    pc.milestone_trips AS milestone_value,
    ...
FROM ops.v_payment_calculation pc
WHERE pc.origin_tag = 'cabinet'
    AND pc.rule_scope = 'partner'
    AND pc.milestone_trips IN (1, 5, 25)
    AND pc.milestone_achieved = true  -- ← FILTRA POR milestone_achieved
```

**Base de datos:** `ops.v_payment_calculation` con filtro `milestone_achieved = true`.

---

### 3. Vista Canónica: `ops.v_payment_calculation`

**Archivo:** `backend/sql/ops/v_payment_calculation.sql`

**Propósito:** Calcula elegibilidad y montos de pago basándose en métricas de conversión y reglas de pago configurables.

**Fuente de achieved:**
```sql
-- Líneas 137-262 (milestone_achievement CTE)
-- Calcula achieved basado en:
-- 1. lead_date desde observational.v_conversion_metrics
-- 2. Reglas de pago (window_days, milestone_trips)
-- 3. Viajes acumulados desde summary_daily DENTRO de la ventana
-- 4. milestone_achieved = true si cumulative_trips >= milestone_trips DENTRO de window_days
```

**Problema clave:** 
- **NO es determinístico puro** desde summary_daily
- Depende de **ventanas de tiempo** (`window_days`) desde `lead_date`
- Depende de **reglas de pago** (`ops.partner_payment_rules`, `ops.scout_payment_rules`)
- **Permite M5 achieved sin M1** porque:
  - Cada milestone se calcula **independientemente** por regla
  - Diferentes `lead_date` pueden generar diferentes ventanas
  - Si M5 se alcanza en una ventana pero M1 no (por lead_date diferente o ventana expirada), aparece M5 sin M1

---

### 4. Vista Canónica Antigua: `ops.v_cabinet_milestones_achieved`

**Archivo:** `backend/sql/ops/v_cabinet_milestones_achieved.sql`

**Propósito:** Vista canónica C2 que expone SOLO milestones ACHIEVED.

**Fuente de achieved:**
```sql
-- Líneas 26-49
SELECT 
    pc.milestone_trips AS milestone_value,
    pc.milestone_achieved,
    ...
FROM ops.v_payment_calculation pc
WHERE pc.origin_tag = 'cabinet'
    AND pc.rule_scope = 'partner'
    AND pc.milestone_trips IN (1, 5, 25)
    AND pc.milestone_achieved = true
```

**Base de datos:** También `ops.v_payment_calculation` (misma fuente que Driver Matrix).

---

## Por Qué Existe M5=true y M1=false

### Razón 1: Cálculo Independiente por Milestone

`ops.v_payment_calculation` calcula cada milestone **independientemente**:

```sql
-- Cada milestone tiene su propia regla y ventana
milestone_achievement AS (
    SELECT DISTINCT ON (person_key, origin_tag, rule_id)
        ...
        milestone_trips,  -- 1, 5, o 25
        window_days,      -- Ventana específica para esta regla
        ...
    WHERE cumulative_trips >= milestone_trips
        AND prod_date < lead_date + (window_days || ' days')::INTERVAL
)
```

**Problema:** Si M5 se alcanza en una ventana pero M1 no (por lead_date diferente o ventana expirada), aparece M5 sin M1.

### Razón 2: Dependencia de lead_date y Ventanas

- Cada milestone puede tener un `lead_date` diferente
- Cada milestone puede tener una `window_days` diferente según la regla
- Si M1 tiene `lead_date = '2025-01-01'` y `window_days = 14`, pero M5 tiene `lead_date = '2025-01-10'` y `window_days = 14`, pueden alcanzarse en momentos diferentes

### Razón 3: Eventos Históricos vs Cálculo Determinístico

- `v_payment_calculation` usa **eventos históricos** (lead_date, reglas vigentes en ese momento)
- `v_ct4_milestones_achieved_from_trips_eligible` usa **cálculo determinístico** (acumulación pura desde primer viaje)

---

## Comparación: Driver Matrix vs Vista Determinística

| Aspecto | Driver Matrix | Vista Determinística |
|---------|---------------|---------------------|
| **Fuente** | `ops.v_payment_calculation` | `public.summary_daily` |
| **Cálculo** | Reglas + ventanas + lead_date | Acumulación pura desde primer viaje |
| **Consistencia** | ❌ Permite M5 sin M1 | ✅ Garantiza M5 → M1 |
| **Determinístico** | ❌ Depende de eventos históricos | ✅ Solo viajes reales |
| **Ventanas** | ✅ Usa window_days de reglas | ❌ No usa ventanas |
| **lead_date** | ✅ Depende de lead_date | ❌ No depende de lead_date |

---

## Extracción de SQL Real desde Base de Datos

Para obtener las definiciones reales de las vistas desde PostgreSQL, ejecutar:

```sql
-- 1. Definición de ops.v_payments_driver_matrix_cabinet
SELECT pg_get_viewdef('ops.v_payments_driver_matrix_cabinet'::regclass, true);

-- 2. Definición de ops.v_claims_payment_status_cabinet
SELECT pg_get_viewdef('ops.v_claims_payment_status_cabinet'::regclass, true);

-- 3. Definición de ops.v_payment_calculation
SELECT pg_get_viewdef('ops.v_payment_calculation'::regclass, true);

-- 4. Definición de ops.v_cabinet_milestones_achieved
SELECT pg_get_viewdef('ops.v_cabinet_milestones_achieved'::regclass, true);

-- 5. Definición de ops.v_yango_payments_ledger_latest_enriched (si está involucrada)
SELECT pg_get_viewdef('ops.v_yango_payments_ledger_latest_enriched'::regclass, true);
```

**Nota:** Estas queries deben ejecutarse en la base de datos PostgreSQL para obtener las definiciones reales (pueden diferir del código fuente si hay cambios no versionados).

**Archivo con queries:** `backend/sql/ops/audit_driver_matrix_achieved_queries.sql`

---

## Queries de Validación

**Archivo:** `backend/sql/ops/audit_driver_matrix_achieved_queries.sql`

Queries reproducibles que demuestran:

### Q1: Drivers donde Driver Matrix reporta M5=1 y M1=0

Muestra `driver_id` y flags de achieved para drivers con inconsistencia M5 sin M1.

```sql
SELECT 
    dm.driver_id,
    dm.m1_achieved_flag AS driver_matrix_m1_achieved,
    dm.m5_achieved_flag AS driver_matrix_m5_achieved,
    ...
FROM ops.v_payments_driver_matrix_cabinet dm
WHERE dm.m5_achieved_flag = true
    AND COALESCE(dm.m1_achieved_flag, false) = false;
```

### Q2: Esos mismos drivers cruzados con vista determinística

Muestra que en la vista determinística M1 sí existe para esos drivers.

```sql
-- Ver archivo completo para query detallado
-- Demuestra: trips_has_m1 = true para drivers con driver_matrix_m5=1 y driver_matrix_m1=0
```

### Q3: Sample 50 drivers comparando ambas fuentes

Comparación lado a lado de achieved desde Driver Matrix vs vista determinística.

```sql
-- Compara:
-- - driver_matrix_has_m1 vs trips_has_m1
-- - driver_matrix_has_m5 vs trips_has_m5
-- - driver_matrix_has_m25 vs trips_has_m25
-- - Identifica diferencias con comparison_status
```

---

## Conclusión

**Driver Matrix NO usa achieved determinístico por viajes.** Usa `ops.v_payment_calculation` que:

1. ✅ Calcula achieved basado en reglas de pago con ventanas
2. ✅ Depende de lead_date y eventos históricos
3. ❌ **NO garantiza consistencia** (permite M5 sin M1)
4. ❌ **NO es determinístico puro** desde summary_daily

**Recomendación:** Para garantizar consistencia, usar `ops.v_ct4_milestones_achieved_from_trips_eligible` que:
- ✅ Calcula achieved determinísticamente desde summary_daily
- ✅ Garantiza consistencia (M5 → M1, M25 → M5 y M1)
- ✅ No depende de reglas ni ventanas históricas

---

## Referencias

- **Driver Matrix:** `backend/sql/ops/v_payments_driver_matrix_cabinet.sql`
- **Claims:** `backend/sql/ops/v_claims_payment_status_cabinet.sql`
- **Payment Calculation:** `backend/sql/ops/v_payment_calculation.sql`
- **Achieved Canónico:** `backend/sql/ops/v_cabinet_milestones_achieved.sql`
- **Achieved Determinístico:** `backend/sql/ops/v_ct4_milestones_achieved_from_trips_eligible.sql`

