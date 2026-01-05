# DEBUG REPORT: M1 Achieved Flag - Análisis de Fuente y Diff Lógico

**Fecha:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")  
**Problema:** M1 no aparece como "Alcanzado" en UI (Driver Matrix / Resumen por Conductor) aunque sí se alcanzó por trips, mientras M5 sí aparece.

---

## 1. ENDPOINTS Y ARCHIVOS FRONTEND

### `/pagos/driver-matrix`
- **Archivo:** `frontend/app/pagos/driver-matrix/page.tsx`
- **Función API:** `getOpsDriverMatrix` (línea 11)
- **Endpoint:** `GET /api/v1/ops/payments/driver-matrix`
- **Parámetros:** `origin_tag`, `only_pending`, `order`, `limit`, `offset`
- **Fetch exacto:**
  ```typescript
  const response = await getOpsDriverMatrix({
    origin_tag: filters.origin_tag || undefined,
    only_pending: filters.only_pending || undefined,
    order: filters.order,
    limit,
    offset,
  });
  ```
- **URL API:** `/api/v1/ops/payments/driver-matrix?origin_tag=cabinet&only_pending=false&order=week_start_desc&limit=200&offset=0`

### `/pagos/resumen-conductor`
- **Archivo:** `frontend/app/pagos/resumen-conductor/page.tsx`
- **Función API:** `getDriverMatrix` (línea 11)
- **Endpoint:** `GET /api/v1/payments/driver-matrix`
- **Parámetros:** `week_from`, `week_to`, `search`, `only_pending`, `page`, `limit`
- **Fetch exacto:**
  ```typescript
  const response = await getDriverMatrix({
    week_from: filters.week_from || undefined,
    week_to: filters.week_to || undefined,
    search: filters.search || undefined,
    only_pending: filters.only_pending || undefined,
    page,
    limit,
  });
  ```
- **URL API:** `/api/v1/payments/driver-matrix?week_from=&week_to=&search=&only_pending=false&page=1&limit=50`

---

## 2. ENDPOINTS BACKEND Y SQL

### Endpoint: `GET /api/v1/ops/payments/driver-matrix`
- **Archivo:** `backend/app/api/v1/ops_payments.py`
- **Función:** `get_driver_matrix` (línea 31)
- **Query SQL:**
  ```sql
  SELECT *
  FROM ops.v_payments_driver_matrix_cabinet
  WHERE ... (filtros dinámicos)
  ORDER BY week_start DESC NULLS LAST, driver_name ASC NULLS LAST
  LIMIT :limit OFFSET :offset
  ```
- **Vista SQL usada:** `ops.v_payments_driver_matrix_cabinet`

### Endpoint: `GET /api/v1/payments/driver-matrix`
- **Archivo:** `backend/app/api/v1/payments.py`
- **Función:** `get_driver_matrix` (línea 195)
- **Query SQL:**
  ```sql
  SELECT *
  FROM ops.v_payments_driver_matrix_cabinet
  WHERE ... (filtros dinámicos)
  ORDER BY week_start DESC NULLS LAST, driver_name ASC NULLS LAST
  LIMIT :limit OFFSET :offset
  ```
- **Vista SQL usada:** `ops.v_payments_driver_matrix_cabinet` (misma vista)

---

## 3. VISTAS SQL - ANÁLISIS DE DEPENDENCIAS

### Vista: `ops.v_payments_driver_matrix_cabinet`
- **Archivo:** `backend/sql/ops/v_payments_driver_matrix_cabinet.sql`
- **Propósito:** Vista de PRESENTACIÓN (1 fila por driver_id) con columnas M1/M5/M25
- **Fuente base:** `ops.v_claims_payment_status_cabinet` (línea 46)
- **Cálculo de `m1_achieved_flag`:** 
  ```sql
  BOOL_OR(bc.milestone_value = 1) AS m1_achieved_flag,
  ```
  Donde `bc` viene del CTE `base_claims` que es:
  ```sql
  SELECT ... FROM ops.v_claims_payment_status_cabinet c
  WHERE c.milestone_value IN (1, 5, 25)
  ```

### Vista: `ops.v_claims_payment_status_cabinet`
- **Archivo:** `backend/sql/ops/v_claims_payment_status_cabinet.sql`
- **Propósito:** Vista orientada a cobranza (1 fila por claim = driver_id + milestone_value)
- **Fuente base:** `ops.v_payment_calculation` (línea 49)
- **Filtro crítico:** 
  ```sql
  WHERE pc.origin_tag = 'cabinet'
      AND pc.rule_scope = 'partner'
      AND pc.milestone_trips IN (1, 5, 25)
      AND pc.milestone_achieved = true  -- ⚠️ FILTRO CRÍTICO
      AND pc.driver_id IS NOT NULL
  ```
- **Problema identificado:** Solo incluye milestones donde `milestone_achieved = true` desde `v_payment_calculation`

### Vista: `ops.v_payment_calculation`
- **Archivo:** `backend/sql/ops/v_payment_calculation.sql`
- **Propósito:** Vista canónica C2 que calcula elegibilidad de pagos
- **Cálculo de `milestone_achieved`:**
  ```sql
  -- milestone_achieved: Si se alcanzó el milestone dentro de la ventana
  (arc.achieved_date IS NOT NULL) AS milestone_achieved,
  ```
  Donde `arc.achieved_date` viene de un CTE que calcula cuándo se alcanzó el milestone basándose en:
  - `cumulative_trips_from_lead >= milestone_trips`
  - Dentro de una ventana de tiempo (`window_days`)
  - **PERO:** Solo para leads que están en `ops.v_payment_calculation` (que viene de `module_ct_cabinet_leads`)

### Vista determinística: `ops.v_cabinet_milestones_achieved_from_trips`
- **Archivo:** `backend/sql/ops/v_cabinet_milestones_achieved_from_trips.sql`
- **Propósito:** Vista determinística que calcula milestones ACHIEVED basándose únicamente en viajes reales desde `summary_daily`
- **Fuente:** `public.summary_daily` (viajes reales)
- **Cálculo:** Acumulación de trips desde el primer viaje, sin depender de leads ni claims
- **Regla:** Si M5 está achieved, M1 también debe estar achieved (expansión de milestones menores)

---

## 4. PUNTO EXACTO DONDE SE PIERDE M1

### Cadena de dependencias:
```
UI (Driver Matrix)
  ↓
GET /api/v1/ops/payments/driver-matrix
  ↓
ops.v_payments_driver_matrix_cabinet
  ↓ (base_claims CTE, línea 33-47)
ops.v_claims_payment_status_cabinet
  ↓ (base_claims_raw CTE, línea 33-55)
ops.v_payment_calculation
  ↓ (filtro línea 53)
AND pc.milestone_achieved = true
```

### Problema identificado:

**En `ops.v_claims_payment_status_cabinet` (línea 53):**
```sql
AND pc.milestone_achieved = true  -- Solo milestones alcanzados
```

Este filtro hace que **solo se incluyan milestones que están en `v_payment_calculation` con `milestone_achieved = true`**.

**¿Por qué M1 puede no estar en `v_payment_calculation`?**
1. `v_payment_calculation` depende de `module_ct_cabinet_leads` (leads que entraron por cabinet)
2. Si un driver alcanzó M1 por viajes reales (`summary_daily`) pero:
   - No tiene un lead en `module_ct_cabinet_leads` para M1, O
   - El lead existe pero el milestone no se alcanzó dentro de la ventana (`window_days`), O
   - El milestone se alcanzó fuera de la ventana de la regla de pago
3. Entonces `milestone_achieved = false` o el registro no existe en `v_payment_calculation`
4. Por lo tanto, M1 no aparece en `v_claims_payment_status_cabinet`
5. Por lo tanto, `m1_achieved_flag = false` en `v_payments_driver_matrix_cabinet`

**¿Por qué M5 sí aparece?**
- M5 puede tener un lead en `module_ct_cabinet_leads` que sí pasó por el proceso de claims
- O M5 se alcanzó dentro de la ventana de la regla de pago
- Por lo tanto, M5 está en `v_payment_calculation` con `milestone_achieved = true`
- Por lo tanto, M5 aparece en `v_claims_payment_status_cabinet`
- Por lo tanto, `m5_achieved_flag = true` en `v_payments_driver_matrix_cabinet`

---

## 5. QUERIES DE REPRODUCCIÓN

### Query 1: Milestone determinístico (debería decir M1 achieved)
```sql
-- Usar vista determinística basada en viajes reales
SELECT 
    driver_id,
    milestone_value,
    achieved_flag,
    achieved_date,
    trips_at_achieved
FROM ops.v_cabinet_milestones_achieved_from_trips
WHERE driver_id = '0405aa...'  -- Reemplazar con driver_id del screenshot
ORDER BY milestone_value;
```

**Resultado esperado:**
- M1: `achieved_flag = true`, `achieved_date = <fecha>`, `trips_at_achieved >= 1`
- M5: `achieved_flag = true`, `achieved_date = <fecha>`, `trips_at_achieved >= 5`

### Query 2: Driver matrix (está diciendo M1 false)
```sql
-- Vista actual que alimenta la UI
SELECT 
    driver_id,
    person_key,
    driver_name,
    m1_achieved_flag,
    m1_achieved_date,
    m5_achieved_flag,
    m5_achieved_date,
    m25_achieved_flag,
    m25_achieved_date
FROM ops.v_payments_driver_matrix_cabinet
WHERE driver_id = '0405aa...'  -- Reemplazar con driver_id del screenshot
   OR person_key::text LIKE '0405aa%';
```

**Resultado actual (problemático):**
- M1: `m1_achieved_flag = false` o `NULL`
- M5: `m5_achieved_flag = true`, `m5_achieved_date = <fecha>`

### Query 3: Claims base (fuente intermedia)
```sql
-- Ver qué claims existen en la vista base
SELECT 
    driver_id,
    milestone_value,
    lead_date,
    expected_amount,
    paid_flag,
    payment_status,
    reason_code
FROM ops.v_claims_payment_status_cabinet
WHERE driver_id = '0405aa...'  -- Reemplazar con driver_id del screenshot
ORDER BY milestone_value;
```

**Resultado esperado:**
- M1: **NO existe** (porque `milestone_achieved = false` en `v_payment_calculation`)
- M5: Existe con `paid_flag = false`, `payment_status = 'not_paid'`

### Query 4: Payment calculation (fuente raíz)
```sql
-- Ver qué milestones están en v_payment_calculation
SELECT 
    driver_id,
    person_key,
    milestone_trips AS milestone_value,
    milestone_achieved,
    achieved_date,
    is_payable,
    lead_date,
    origin_tag,
    rule_scope
FROM ops.v_payment_calculation
WHERE driver_id = '0405aa...'  -- Reemplazar con driver_id del screenshot
  AND origin_tag = 'cabinet'
  AND rule_scope = 'partner'
  AND milestone_trips IN (1, 5, 25)
ORDER BY milestone_trips;
```

**Resultado esperado:**
- M1: **NO existe** o `milestone_achieved = false`
- M5: Existe con `milestone_achieved = true`, `achieved_date = <fecha>`

---

## 6. DIFF LÓGICO

### Estado actual (incorrecto):
```
summary_daily (viajes reales)
  → M1: trips >= 1 ✅ (determinístico)
  → M5: trips >= 5 ✅ (determinístico)

v_payment_calculation
  → M1: milestone_achieved = false (o no existe) ❌
  → M5: milestone_achieved = true ✅

v_claims_payment_status_cabinet
  → M1: NO existe (filtrado por milestone_achieved = true) ❌
  → M5: Existe ✅

v_payments_driver_matrix_cabinet
  → m1_achieved_flag = false (porque M1 no está en base_claims) ❌
  → m5_achieved_flag = true ✅
```

### Estado esperado (correcto):
```
summary_daily (viajes reales)
  → M1: trips >= 1 ✅ (determinístico)
  → M5: trips >= 5 ✅ (determinístico)

v_cabinet_milestones_achieved_from_trips (determinístico)
  → M1: achieved_flag = true ✅
  → M5: achieved_flag = true ✅

v_payments_driver_matrix_cabinet (debería usar fuente determinística)
  → m1_achieved_flag = true ✅
  → m5_achieved_flag = true ✅
```

---

## 7. CONCLUSIÓN

### Problema raíz:
**`ops.v_payments_driver_matrix_cabinet` está usando `ops.v_claims_payment_status_cabinet` como fuente para los flags `achieved`, pero esta vista filtra por `milestone_achieved = true` desde `ops.v_payment_calculation`, que depende de leads y ventanas de reglas de pago, NO de viajes determinísticos.**

### Solución propuesta (NO implementada aún):
**Cambiar `ops.v_payments_driver_matrix_cabinet` para que use `ops.v_cabinet_milestones_achieved_from_trips` (o `ops.v_cabinet_milestones_achieved`) como fuente determinística de los flags `achieved`, en lugar de depender de `ops.v_claims_payment_status_cabinet`.**

### Archivos involucrados:
1. `backend/sql/ops/v_payments_driver_matrix_cabinet.sql` - Vista que necesita cambio
2. `backend/sql/ops/v_cabinet_milestones_achieved_from_trips.sql` - Vista determinística (ya existe)
3. `backend/sql/ops/v_cabinet_milestones_achieved.sql` - Vista determinística alternativa (ya existe)

### Queries de verificación:
Ejecutar las queries 1-4 arriba con un `driver_id` real del screenshot para confirmar el diff lógico.

---

## 8. PRÓXIMOS PASOS (NO IMPLEMENTAR AÚN)

1. **Confirmar con driver real:** Ejecutar queries 1-4 con un `driver_id` del screenshot
2. **Decidir fuente determinística:** ¿Usar `v_cabinet_milestones_achieved_from_trips` o `v_cabinet_milestones_achieved`?
3. **Modificar `v_payments_driver_matrix_cabinet`:** Cambiar el CTE `base_claims` para usar la vista determinística en lugar de `v_claims_payment_status_cabinet` para los flags `achieved`
4. **Mantener información de pagos:** Los campos `yango_payment_status`, `window_status`, `overdue_days` deben seguir viniendo de `v_claims_payment_status_cabinet` o `v_yango_cabinet_claims_for_collection`
5. **Testing:** Verificar que M1 aparece como achieved cuando se alcanzó por trips, independientemente de pagos

