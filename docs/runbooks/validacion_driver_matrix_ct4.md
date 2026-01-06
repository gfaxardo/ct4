# Validación: Driver Matrix CT4 (Achieved Determinístico)

**Fecha:** 2025-01-XX  
**Vista:** `ops.v_payments_driver_matrix_ct4`

---

## Propósito

La vista `ops.v_payments_driver_matrix_ct4` es una versión mejorada de `ops.v_payments_driver_matrix_cabinet` que usa **achieved determinístico** basado en viajes (`summary_daily`) en lugar de achieved legacy basado en reglas/ventanas/lead_date.

**Diferencia clave:** Garantiza consistencia de milestones (si M5=true, entonces M1=true).

---

## Queries de Validación

### 1. Conteo de Drivers CT4

```sql
SELECT COUNT(*) AS total_drivers_ct4
FROM ops.v_payments_driver_matrix_ct4;
```

**Resultado esperado:** Número total de drivers elegibles CT4 (cabinet + fleet_migration) con achieved determinístico.

---

### 2. Chequeo de Consistencia: M5 true implica M1 true

```sql
-- Esta query DEBE devolver 0 filas (garantía de consistencia)
SELECT 
    driver_id,
    person_key,
    origin_tag,
    m1_achieved_flag,
    m5_achieved_flag,
    m25_achieved_flag
FROM ops.v_payments_driver_matrix_ct4
WHERE m5_achieved_flag = true
    AND COALESCE(m1_achieved_flag, false) = false;
```

**Resultado esperado:** 0 filas (garantía de consistencia)

**Validación:** Si devuelve > 0 filas, hay un bug en la vista.

---

### 3. Chequeo de Consistencia: M25 true implica M5 y M1 true

```sql
-- Esta query DEBE devolver 0 filas (garantía de consistencia)
SELECT 
    driver_id,
    person_key,
    origin_tag,
    m1_achieved_flag,
    m5_achieved_flag,
    m25_achieved_flag
FROM ops.v_payments_driver_matrix_ct4
WHERE m25_achieved_flag = true
    AND (COALESCE(m5_achieved_flag, false) = false 
         OR COALESCE(m1_achieved_flag, false) = false);
```

**Resultado esperado:** 0 filas (garantía de consistencia)

**Validación:** Si devuelve > 0 filas, hay un bug en la vista.

---

### 4. Sample de 50 Drivers Comparando Legacy vs CT4

```sql
WITH legacy_sample AS (
    SELECT 
        driver_id,
        m1_achieved_flag AS legacy_m1,
        m5_achieved_flag AS legacy_m5,
        m25_achieved_flag AS legacy_m25,
        m5_without_m1_flag AS legacy_inconsistency
    FROM ops.v_payments_driver_matrix_cabinet
    WHERE origin_tag IN ('cabinet', 'fleet_migration')
    LIMIT 50
),
ct4_sample AS (
    SELECT 
        driver_id,
        m1_achieved_flag AS ct4_m1,
        m5_achieved_flag AS ct4_m5,
        m25_achieved_flag AS ct4_m25,
        legacy_inconsistency_flag AS ct4_legacy_inconsistency
    FROM ops.v_payments_driver_matrix_ct4
    WHERE driver_id IN (SELECT driver_id FROM legacy_sample)
)
SELECT 
    l.driver_id,
    l.legacy_m1,
    l.legacy_m5,
    l.legacy_m25,
    l.legacy_inconsistency,
    c.ct4_m1,
    c.ct4_m5,
    c.ct4_m25,
    c.ct4_legacy_inconsistency,
    CASE 
        WHEN l.legacy_m1 != COALESCE(c.ct4_m1, false) THEN 'M1_DIFF'
        WHEN l.legacy_m5 != COALESCE(c.ct4_m5, false) THEN 'M5_DIFF'
        WHEN l.legacy_m25 != COALESCE(c.ct4_m25, false) THEN 'M25_DIFF'
        WHEN l.legacy_inconsistency = true AND c.ct4_legacy_inconsistency = true THEN 'BOTH_INCONSISTENT'
        WHEN l.legacy_inconsistency = true AND c.ct4_legacy_inconsistency = false THEN 'LEGACY_FIXED'
        ELSE 'OK'
    END AS comparison_status
FROM legacy_sample l
LEFT JOIN ct4_sample c ON c.driver_id = l.driver_id
ORDER BY 
    CASE comparison_status
        WHEN 'LEGACY_FIXED' THEN 1
        WHEN 'M1_DIFF' THEN 2
        WHEN 'M5_DIFF' THEN 3
        WHEN 'M25_DIFF' THEN 4
        ELSE 5
    END,
    l.driver_id;
```

**Validación:**
- `LEGACY_FIXED`: Drivers que tenían inconsistencias en legacy y ahora están consistentes en CT4
- `M1_DIFF`, `M5_DIFF`, `M25_DIFF`: Diferencias en achieved flags
- `OK`: Sin diferencias

---

### 5. Distribución por Origin Tag

```sql
SELECT 
    origin_tag,
    COUNT(*) AS count_drivers,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true) AS m1_count,
    COUNT(*) FILTER (WHERE m5_achieved_flag = true) AS m5_count,
    COUNT(*) FILTER (WHERE m25_achieved_flag = true) AS m25_count,
    COUNT(*) FILTER (WHERE legacy_inconsistency_flag = true) AS legacy_inconsistency_count,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.v_payments_driver_matrix_ct4), 0), 2) AS pct_total
FROM ops.v_payments_driver_matrix_ct4
GROUP BY origin_tag
ORDER BY count_drivers DESC;
```

**Resultado esperado:**
- `cabinet`: ~70-90% del total
- `fleet_migration`: ~10-30% del total

---

### 6. Tiempos de Ejecución Esperados

```sql
-- Medir tiempo de ejecución de la vista
\timing on

SELECT COUNT(*) 
FROM ops.v_payments_driver_matrix_ct4;

SELECT * 
FROM ops.v_payments_driver_matrix_ct4 
LIMIT 100;

SELECT * 
FROM ops.v_payments_driver_matrix_ct4 
WHERE origin_tag = 'cabinet' 
LIMIT 100;
```

**Resultado esperado:**
- Conteo total: < 5 segundos
- SELECT con LIMIT 100: < 2 segundos
- SELECT con filtro origin_tag: < 2 segundos

**Validación:** Si los tiempos son > 10 segundos, revisar índices.

---

### 7. Validación de achieved_source

```sql
-- Verificar que todos tengan achieved_source = 'TRIPS_CT4'
SELECT 
    achieved_source,
    COUNT(*) AS count_drivers,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM ops.v_payments_driver_matrix_ct4), 0), 2) AS pct_total
FROM ops.v_payments_driver_matrix_ct4
GROUP BY achieved_source;
```

**Resultado esperado:** Todos deben tener `achieved_source = 'TRIPS_CT4'`

---

### 8. Comparación de Totales: Legacy vs CT4

```sql
SELECT 
    'Legacy (v_payments_driver_matrix_cabinet)' AS source,
    COUNT(*) AS total_drivers,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true) AS m1_count,
    COUNT(*) FILTER (WHERE m5_achieved_flag = true) AS m5_count,
    COUNT(*) FILTER (WHERE m25_achieved_flag = true) AS m25_count,
    COUNT(*) FILTER (WHERE m5_without_m1_flag = true) AS m5_without_m1_count
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag IN ('cabinet', 'fleet_migration')
UNION ALL
SELECT 
    'CT4 (v_payments_driver_matrix_ct4)' AS source,
    COUNT(*) AS total_drivers,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true) AS m1_count,
    COUNT(*) FILTER (WHERE m5_achieved_flag = true) AS m5_count,
    COUNT(*) FILTER (WHERE m25_achieved_flag = true) AS m25_count,
    COUNT(*) FILTER (WHERE legacy_inconsistency_flag = true) AS legacy_inconsistency_count
FROM ops.v_payments_driver_matrix_ct4;
```

**Validación:**
- CT4 debe tener `m5_without_m1_count = 0` (garantía de consistencia)
- Legacy puede tener `m5_without_m1_count > 0` (esperado)

---

## Checklist de Validación Pre-Producción

Antes de usar la vista en producción, verificar:

- [ ] ✅ Conteo total > 0
- [ ] ✅ Chequeo M5 → M1: 0 filas (garantía de consistencia)
- [ ] ✅ Chequeo M25 → M5 y M1: 0 filas (garantía de consistencia)
- [ ] ✅ Todos tienen `achieved_source = 'TRIPS_CT4'`
- [ ] ✅ Tiempos de ejecución < 10 segundos
- [ ] ✅ Sample de 50 drivers muestra diferencias esperadas (legacy fixed)

---

## Troubleshooting

### Problema: Vista vacía

**Causa posible:** No hay drivers en `ops.v_ct4_eligible_drivers` o `ops.v_ct4_milestones_achieved_from_trips_eligible`

**Solución:** Verificar vistas base:

```sql
SELECT COUNT(*) FROM ops.v_ct4_eligible_drivers;
SELECT COUNT(*) FROM ops.v_ct4_milestones_achieved_from_trips_eligible;
```

### Problema: Inconsistencias detectadas (M5 sin M1)

**Causa posible:** Bug en `ops.v_ct4_milestones_achieved_from_trips_eligible`

**Solución:** Verificar vista base:

```sql
SELECT driver_id, milestone_value
FROM ops.v_ct4_milestones_achieved_from_trips_eligible
WHERE driver_id IN (
    SELECT driver_id 
    FROM ops.v_payments_driver_matrix_ct4 
    WHERE m5_achieved_flag = true AND COALESCE(m1_achieved_flag, false) = false
);
```

### Problema: Tiempos de ejecución lentos

**Causa posible:** Falta de índices en vistas base

**Solución:** Verificar índices recomendados en `audit_driver_matrix_achieved_queries.sql`

---

## Referencias

- **Vista SQL:** `backend/sql/ops/v_payments_driver_matrix_ct4.sql`
- **Vista Pivot:** `backend/sql/ops/v_ct4_driver_achieved_from_trips.sql`
- **Vista Base:** `backend/sql/ops/v_ct4_milestones_achieved_from_trips_eligible.sql`
- **Vista Legacy:** `backend/sql/ops/v_payments_driver_matrix_cabinet.sql`
- **Auditoría:** `backend/sql/ops/audit_driver_matrix_achieved_queries.sql`




