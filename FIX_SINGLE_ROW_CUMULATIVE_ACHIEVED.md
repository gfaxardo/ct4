# Fix: Achieved Flags Cumulativos con Grano 1 Fila por Driver

## Problema Identificado

En la UI Driver Matrix y Resumen por Conductor había filas donde:
- M5 aparecía como ✅ Alcanzado (UNPAID/PAID/etc.)
- pero M1 aparecía como "—"

**Causa raíz**: La vista `ops.v_payments_driver_matrix_cabinet` agregaba los achieved flags por `driver_id`, pero si M1 fue alcanzado en una semana y M5 en otra, el join por semana dejaba M1 como `null/false` cuando no había claim asociado a la semana de M5.

**Requerimiento crítico**: La vista DEBE tener EXACTAMENTE 1 fila por `driver_id`. No puede haber múltiples filas por driver.

## Solución Implementada

### Mantener Grano 1 Fila por Driver

**ANTES:**
- Grano: `driver_id` (1 fila por driver) ✅
- Flags achieved agregados con `BOOL_OR` por `driver_id` ✅
- Pero el problema era que si M1 y M5 estaban en semanas diferentes, el join podía perder M1

**DESPUÉS:**
- Grano: `driver_id` (1 fila por driver) ✅ **MANTIENE EL GRANO**
- Flags achieved son **CUMULATIVOS**: si un driver alguna vez alcanzó un milestone por trips, el flag será `true` independientemente de la semana o del estado de pago
- `achieved_date` es la primera fecha real (`MIN achieved_date`) en que se alcanzó el milestone

### Cambios en la Vista

1. **CTE `deterministic_milestones_events`**: Milestones como eventos puros (sin agregación por semana)

2. **CTE `deterministic_milestones_agg` modificado**:
   - Agrega por `driver_id` solamente
   - Flags achieved con `BOOL_OR`: si alguna vez alcanzó, siempre `true`
   - `achieved_date` con `MIN`: primera fecha real en que se alcanzó

3. **CTE `claims_agg`**: Mantiene agregación por `driver_id` para payment info

4. **CTE `driver_milestones`**:
   - Agrupa por `driver_id` solamente (1 fila por driver)
   - Flags achieved vienen de `deterministic_milestones_agg` (cumulativos)
   - Payment info viene de `claims_agg`
   - `week_start` calculado como última semana relevante (máxima entre claims y milestones achieved)

### Lógica de Flags Achieved Cumulativos

Para cada driver:

```sql
-- Agregación por driver_id
deterministic_milestones_agg AS (
    SELECT 
        dm.driver_id,
        -- Si alguna vez alcanzó M1, siempre true
        BOOL_OR(dm.milestone_value = 1 AND dm.achieved_flag = true) AS m1_achieved_flag,
        -- Primera fecha real (MIN) en que se alcanzó
        MIN(CASE WHEN dm.milestone_value = 1 AND dm.achieved_flag = true THEN dm.achieved_date END) AS m1_achieved_date,
        -- Idem para M5 y M25
        ...
    FROM deterministic_milestones_events dm
    GROUP BY dm.driver_id
)
```

Esto significa:
- Si M1 fue alcanzado en semana 1 (2025-01-06), el flag será `true` en la única fila del driver
- Si M5 fue alcanzado en semana 2 (2025-01-13), el flag será `true` en la misma fila
- En la única fila del driver, tanto M1 como M5 aparecerán como `achieved=true` si ambos fueron alcanzados

## Archivos Modificados

1. **`backend/sql/ops/v_payments_driver_matrix_cabinet.sql`**
   - Mantiene grano de 1 fila por `driver_id`
   - Flags achieved cumulativos usando `BOOL_OR` y `MIN` por `driver_id`
   - Actualización de comentarios para reflejar comportamiento cumulativo

2. **`backend/scripts/sql/debug_m1_m5_single_row_evidence.sql`** (nuevo)
   - Script de debug para evidenciar el problema

3. **`backend/scripts/sql/verify_single_row_cumulative_achieved.sql`** (nuevo)
   - Script de verificación con 5 queries:
     - Verificación 1: Duplicados por `driver_id` (debe ser 0 filas)
     - Verificación 2: Coherencia cumulativa (no debe haber M5 sin M1)
     - Verificación 3: Spot check de un driver específico
     - Verificación 4: Verificar que `achieved_date` es MIN
     - Verificación 5: Resumen de grano

## Diferencias Clave

### ANTES (con problema)
```sql
-- Agregación por driver_id
deterministic_milestones_agg AS (
    SELECT 
        dm.driver_id,
        BOOL_OR(dm.milestone_value = 1 AND dm.achieved_flag = true) AS m1_achieved_flag,
        MAX(CASE WHEN dm.milestone_value = 1 THEN dm.achieved_date END) AS m1_achieved_date,
        -- ...
    FROM deterministic_milestones dm
    GROUP BY dm.driver_id
),
-- ...
driver_milestones AS (
    SELECT 
        -- ...
        COALESCE(dma.m1_achieved_flag, false) AS m1_achieved_flag,
        -- ...
    FROM deterministic_milestones_agg dma
    -- ...
    GROUP BY bc.driver_id  -- Solo por driver_id
)
```

**Problema**: Si M1 y M5 estaban en semanas diferentes y solo había claim para M5, el join podía perder M1.

### DESPUÉS (fix)
```sql
-- Milestones como eventos puros
deterministic_milestones_events AS (
    SELECT 
        m.driver_id,
        m.milestone_value,
        m.achieved_flag,
        m.achieved_date
    FROM ops.v_cabinet_milestones_achieved_from_trips m
    WHERE m.milestone_value IN (1, 5, 25)
),
-- Agregación por driver_id (CUMULATIVO)
deterministic_milestones_agg AS (
    SELECT 
        dm.driver_id,
        -- Si alguna vez alcanzó, siempre true
        BOOL_OR(dm.milestone_value = 1 AND dm.achieved_flag = true) AS m1_achieved_flag,
        -- Primera fecha real (MIN)
        MIN(CASE WHEN dm.milestone_value = 1 AND dm.achieved_flag = true THEN dm.achieved_date END) AS m1_achieved_date,
        -- ...
    FROM deterministic_milestones_events dm
    GROUP BY dm.driver_id
),
-- ...
driver_milestones AS (
    SELECT 
        -- ...
        COALESCE(dma.m1_achieved_flag, false) AS m1_achieved_flag,
        -- ...
    FROM deterministic_milestones_agg dma
    -- ...
    GROUP BY bc.driver_id  -- Solo por driver_id (1 fila por driver)
)
```

**Solución**: Los flags achieved se calculan directamente desde `deterministic_milestones_events` agregando por `driver_id`, sin depender de joins con claims por semana.

## Comandos para Aplicar el Fix

### 1. Debug/Evidencia (Opcional)

```bash
# Ejecutar script de debug para encontrar drivers con el problema
psql $DATABASE_URL -f backend/scripts/sql/debug_m1_m5_single_row_evidence.sql
```

**Resultado esperado**: Lista de drivers donde M5 está achieved pero M1 no.

### 2. Aplicar la Vista Modificada

```bash
# Desde el directorio del proyecto
psql $DATABASE_URL -f backend/sql/ops/v_payments_driver_matrix_cabinet.sql
```

### 3. Verificar el Fix

```bash
# Ejecutar script de verificación
psql $DATABASE_URL -f backend/scripts/sql/verify_single_row_cumulative_achieved.sql
```

**Resultado esperado:**
- Verificación 1: **0 filas** (no hay duplicados por `driver_id`)
- Verificación 2: **0 filas** (no hay inconsistencias M5 sin M1)
- Verificación 3: Spot check debe mostrar que matrix y determinístico coinciden
- Verificación 4: Debe mostrar "OK" para todas las comparaciones de fechas
- Verificación 5: Debe mostrar "OK: 1 fila por driver"

## Ejemplo de Comportamiento

### Antes (con problema)
```
Driver    | M1 Achieved | M5 Achieved | M1 Date    | M5 Date
----------|-------------|-------------|------------|----------
Driver A  | false       | true        | NULL       | 2025-01-13
          | (M1 fue en  | (M5 fue en  | (perdido   | (solo M5
          | semana 1,   | semana 2,   | porque no  | tiene
          | pero solo   | y solo hay  | hay claim  | claim)
          | muestra     | claim para  | para M1)   |
          | semana 2)   | M5)         |            |
```

### Después (fix)
```
Driver    | M1 Achieved | M5 Achieved | M1 Date    | M5 Date
----------|-------------|-------------|------------|----------
Driver A  | true        | true        | 2025-01-06 | 2025-01-13
          | (cumulativo)| (cumulativo)| (primera   | (primera
          | si alguna   | si alguna   | fecha real) | fecha real)
          | vez alcanzó| vez alcanzó|            |
```

## Notas Importantes

1. **Grano NO cambió**: La vista sigue teniendo EXACTAMENTE 1 fila por `driver_id`

2. **Flags achieved son cumulativos**: Si un driver alguna vez alcanzó un milestone por trips, el flag será `true` independientemente de:
   - La semana en que se alcanzó
   - El estado de pago
   - Si hay claim asociado o no

3. **`achieved_date` es la primera fecha real**: Se usa `MIN(achieved_date)` para obtener la primera fecha en que se alcanzó el milestone

4. **Payment info sigue igual**: Los campos de payment (`expected_amount`, `payment_status`, `window_status`, `overdue_days`) siguen viniendo de claims y se agregan por `driver_id`

5. **No se modificaron**:
   - `ops.v_payment_calculation` (sigue siendo canónica para pagos)
   - `ops.v_claims_payment_status_cabinet` (sigue siendo canónica para claims)
   - `ops.v_cabinet_milestones_achieved_from_trips` (sigue siendo la fuente determinística)

## Por Qué Era un Problema de Join por Semana

El problema ocurría porque:
1. La vista agregaba por `driver_id` solamente (correcto)
2. Pero los flags achieved se calculaban desde `deterministic_milestones_agg` que también agregaba por `driver_id` (correcto)
3. Sin embargo, si M1 y M5 estaban en semanas diferentes y solo había claim para M5, el join con claims podía afectar la visibilidad de M1

**Solución**: Los flags achieved se calculan directamente desde `deterministic_milestones_events` agregando por `driver_id` con `BOOL_OR` y `MIN`, sin depender de joins con claims por semana. Esto garantiza que si un driver alguna vez alcanzó un milestone por trips, el flag será `true` en la única fila del driver.





