# Fix: Achieved Flags Cumulativos por Semana

## Problema Identificado

En la UI Driver Matrix y Resumen por Conductor había filas donde:
- M5 aparecía como ✅ Alcanzado (UNPAID/PAID/etc.)
- pero M1 aparecía como "—"

**Causa raíz**: La vista `ops.v_payments_driver_matrix_cabinet` tenía grano por `driver_id` solamente (1 fila por driver), sin considerar `week_start`. Si M1 fue alcanzado en semana 1 y M5 en semana 2, la vista solo mostraba 1 fila (con `week_start` de la semana más reciente), y M1 no aparecía si no había claim asociado a esa semana.

## Solución Implementada

### Cambio de Grano

**ANTES:**
- Grano: `driver_id` (1 fila por driver)
- `week_start` calculado desde `lead_date` o `achieved_date` más reciente
- No había carry-forward de milestones a semanas posteriores

**DESPUÉS:**
- Grano: `(driver_id, week_start, origin_tag)` (múltiples filas por driver, una por semana)
- `week_start` viene del set base de filas (desde claims y milestones achieved)
- Flags achieved son **CUMULATIVOS**: si un milestone fue alcanzado en semana anterior, aparecerá como `achieved=true` en todas las semanas posteriores

### Cambios en la Vista

1. **Nuevo CTE `deterministic_milestones_events`**: Milestones como eventos puros (sin agregación por semana)

2. **Nuevo CTE `driver_weeks`**: Set base de filas con todas las combinaciones únicas de `(driver_id, week_start, origin_tag)` desde:
   - Claims (desde `base_claims` con `lead_date` convertido a `week_start`)
   - Milestones achieved (desde `deterministic_milestones_events` con `achieved_date` convertido a `week_start`)
   - Origin data (desde `origin_and_connected_data`)

3. **Nuevo CTE `claims_by_week`**: Agrega claims por `(driver_id, week_start)` para payment info

4. **CTE `driver_milestones` modificado**:
   - Ahora agrupa por `(driver_id, week_start, origin_tag)`
   - Flags achieved calculados con `EXISTS` y subqueries que buscan milestones hasta el final de la semana (`week_start + INTERVAL '6 days'`)
   - `achieved_date` es la primera fecha real (mínima) hasta el final de esa semana

### Lógica de Flags Achieved Cumulativos

Para cada fila `(driver_id, week_start)`:

```sql
m1_achieved_flag = EXISTS (
    SELECT 1 
    FROM deterministic_milestones_events e
    WHERE e.driver_id = dw.driver_id
        AND e.milestone_value = 1
        AND e.achieved_flag = true
        AND e.achieved_date <= (dw.week_start + INTERVAL '6 days')
)
m1_achieved_date = MIN(e.achieved_date) con mismo filtro
```

Esto significa:
- Si M1 fue alcanzado en semana 1 (2025-01-06), aparecerá como `achieved=true` en semana 1 y en todas las semanas posteriores
- Si M5 fue alcanzado en semana 2 (2025-01-13), aparecerá como `achieved=true` en semana 2 y posteriores
- En semana 2, tanto M1 como M5 aparecerán como `achieved=true`

## Archivos Modificados

1. **`backend/sql/ops/v_payments_driver_matrix_cabinet.sql`**
   - Cambio de grano de `driver_id` a `(driver_id, week_start, origin_tag)`
   - Implementación de flags achieved cumulativos usando `EXISTS` y subqueries
   - Actualización de comentarios para reflejar el nuevo grano y comportamiento cumulativo

2. **`backend/scripts/sql/verify_cumulative_achieved_flags.sql`** (nuevo)
   - Script de verificación con 5 queries:
     - Query 1: Verificar que no hay inconsistencias M5 sin M1 en la misma semana
     - Query 2: Verificar que no hay duplicados por grano
     - Query 3: Verificar carry-forward de M1 a semanas posteriores
     - Query 4: Verificar que hay múltiples filas por driver cuando hay múltiples semanas
     - Query 5: Verificar que `achieved_date` es la primera fecha real (mínima)

## Diferencias Clave

### ANTES
```sql
-- Agregación por driver_id solamente
deterministic_milestones_agg AS (
    SELECT 
        dm.driver_id,
        BOOL_OR(dm.milestone_value = 1 AND dm.achieved_flag = true) AS m1_achieved_flag,
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

### DESPUÉS
```sql
-- Milestones como eventos puros (sin agregación)
deterministic_milestones_events AS (
    SELECT 
        m.driver_id,
        m.milestone_value,
        m.achieved_flag,
        m.achieved_date
    FROM ops.v_cabinet_milestones_achieved_from_trips m
    WHERE m.milestone_value IN (1, 5, 25)
),
-- Set base de filas por (driver_id, week_start, origin_tag)
driver_weeks AS (
    -- Semanas desde claims, milestones, origin data
    -- ...
),
-- ...
driver_milestones AS (
    SELECT 
        -- ...
        -- Flags achieved cumulativos
        EXISTS (
            SELECT 1 
            FROM deterministic_milestones_events e
            WHERE e.driver_id = dw.driver_id
                AND e.milestone_value = 1
                AND e.achieved_flag = true
                AND e.achieved_date <= (dw.week_start + INTERVAL '6 days')
        ) AS m1_achieved_flag,
        -- ...
    FROM driver_weeks dw
    -- ...
    GROUP BY dw.driver_id, dw.week_start, dw.origin_tag  -- Por grano completo
)
```

## Comandos para Aplicar el Fix

### 1. Aplicar la Vista Modificada

```bash
# Desde el directorio del proyecto
psql $DATABASE_URL -f backend/sql/ops/v_payments_driver_matrix_cabinet.sql
```

### 2. Verificar el Fix

```bash
# Ejecutar script de verificación
psql $DATABASE_URL -f backend/scripts/sql/verify_cumulative_achieved_flags.sql
```

**Resultado esperado:**
- Query 1: Debe retornar **0 filas** (no hay inconsistencias M5 sin M1 en la misma semana)
- Query 2: Debe retornar **0 filas** (no hay duplicados por grano)
- Query 3: Debe mostrar "OK: M1 carry-forward correcto" para todos los casos
- Query 4: Debe mostrar drivers con múltiples semanas distintas
- Query 5: Debe mostrar "OK" para todas las comparaciones de fechas

## Ejemplo de Comportamiento

### Antes (1 fila por driver)
```
Driver    | Week Start | M1 Achieved | M5 Achieved
----------|------------|-------------|------------
Driver A  | 2025-01-13 | false       | true
          |            | (M1 fue en  | (M5 fue en
          |            | semana 1,   | semana 2)
          |            | pero solo  |
          |            | muestra     |
          |            | semana 2)   |
```

### Después (múltiples filas por driver, flags cumulativos)
```
Driver    | Week Start | M1 Achieved | M5 Achieved
----------|------------|-------------|------------
Driver A  | 2025-01-06 | true        | false
          |            | (M1 alcanzado| (M5 aún no)
          |            | en semana 1)|
Driver A  | 2025-01-13 | true        | true
          |            | (M1 carry-  | (M5 alcanzado
          |            | forward)    | en semana 2)
```

## Notas Importantes

1. **No se modificaron**:
   - `ops.v_payment_calculation` (sigue siendo canónica para pagos)
   - `ops.v_claims_payment_status_cabinet` (sigue siendo canónica para claims)
   - `ops.v_cabinet_milestones_achieved_from_trips` (sigue siendo la fuente determinística)

2. **Payment info sigue igual**: Los campos de payment (`expected_amount`, `payment_status`, `window_status`, `overdue_days`) siguen viniendo de claims y se agregan por semana.

3. **Performance**: La vista ahora puede tener más filas (múltiples por driver), pero los flags achieved se calculan eficientemente con `EXISTS` y subqueries indexadas.

4. **Compatibilidad**: El cambio de grano puede afectar queries que asumían 1 fila por driver. Verificar endpoints y frontend que usen esta vista.

## Por Qué Era un Problema de Grano Semanal

El problema ocurría porque:
1. La vista agregaba por `driver_id` solamente, produciendo 1 fila por driver
2. El `week_start` se calculaba desde `lead_date` o `achieved_date` más reciente
3. Si M1 fue alcanzado en semana 1 pero solo había claim para M5 en semana 2, el `week_start` era de semana 2
4. M1 no aparecía porque no había claim asociado a semana 2, aunque el milestone fue alcanzado en semana 1

**Solución**: Cambiar el grano a `(driver_id, week_start, origin_tag)` y hacer flags achieved cumulativos usando `EXISTS` con filtro de fecha hasta el final de cada semana. Esto permite que milestones alcanzados en semanas anteriores aparezcan como `achieved=true` en todas las semanas posteriores.

