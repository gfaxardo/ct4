# Fix: Claims sin Milestone Achieved (Violación Canónica)

## Problema Identificado

**Bug Crítico**: Existen drivers donde:
- `m5_yango_payment_status = 'UNPAID'` (claim existe)
- pero `m5_achieved_flag = false/null` (no hay milestone determinístico)

**Ejemplos visibles en UI**:
- Alvarez Mantilla Jose
- Aranda Perez Rafael Cristobal

**Violación de regla canónica**:
```
claim(milestone=N) ⇒ achieved(milestone=N) debe existir
```

## Causa Raíz

### Origen del Bug

1. **`ops.v_payment_calculation`** calcula `milestone_achieved` basándose en:
   - Viajes acumulados desde `lead_date`
   - Dentro de una **ventana de tiempo** (`window_days`)
   - Si el milestone se alcanza dentro de la ventana → `milestone_achieved = true`

2. **`ops.v_claims_payment_status_cabinet`** filtra por:
   - `pc.milestone_achieved = true` desde `v_payment_calculation`
   - Pero **NO verifica** si existe milestone determinístico en `v_cabinet_milestones_achieved_from_trips`

3. **`ops.v_cabinet_milestones_achieved_from_trips`** calcula milestones:
   - Basándose en viajes reales desde `summary_daily`
   - **SIN restricción de ventana**
   - Si un driver alcanzó el milestone FUERA de la ventana, puede no aparecer aquí

**Resultado**: Se generan claims basados en ventanas de tiempo, pero el milestone determinístico puede no existir si fue alcanzado fuera de la ventana o si hay diferencias en el cálculo.

## Solución Implementada

### PASO C — Fix Canónico en Generación de Claims

**Archivo**: `backend/sql/ops/v_claims_payment_status_cabinet.sql`

**Cambio**: Agregar `INNER JOIN` con `ops.v_cabinet_milestones_achieved_from_trips` para exigir milestone determinístico:

```sql
FROM ops.v_payment_calculation pc
INNER JOIN ops.v_cabinet_milestones_achieved_from_trips m
    ON m.driver_id = pc.driver_id
    AND m.milestone_value = pc.milestone_trips
    AND m.achieved_flag = true
WHERE pc.origin_tag = 'cabinet'
    AND pc.rule_scope = 'partner'
    AND pc.milestone_trips IN (1, 5, 25)
    AND pc.milestone_achieved = true  -- Dentro de ventana
    AND pc.driver_id IS NOT NULL
```

**Resultado**: Solo se generan claims si:
1. El milestone fue alcanzado dentro de la ventana (`pc.milestone_achieved = true`)
2. **Y** existe milestone determinístico (`m.achieved_flag = true`)

### PASO D — Protección en Driver Matrix

**Archivo**: `backend/sql/ops/v_payments_driver_matrix_cabinet.sql`

**Cambio**: No mostrar payment info si `achieved_flag = false`:

```sql
-- PROTECCIÓN: Solo mostrar payment info si achieved_flag = true
CASE WHEN COALESCE(dma.m5_achieved_flag, false) = true 
     THEN ca.m5_expected_amount_yango 
     ELSE NULL 
END AS m5_expected_amount_yango,
CASE WHEN COALESCE(dma.m5_achieved_flag, false) = true 
     THEN MAX(CASE WHEN ys.milestone_value = 5 THEN ys.yango_payment_status END) 
     ELSE NULL 
END AS m5_yango_payment_status,
-- ... idem para m1 y m25
```

**Resultado**: Si `achieved_flag = false`, todos los campos de payment (`expected_amount`, `yango_payment_status`, `window_status`, `overdue_days`) serán `NULL`, evitando mostrar "UNPAID" o "PAID" sin milestone.

## Archivos Modificados

1. **`backend/sql/ops/v_claims_payment_status_cabinet.sql`**
   - Agregado `INNER JOIN` con `v_cabinet_milestones_achieved_from_trips`
   - Solo genera claims si existe milestone determinístico

2. **`backend/sql/ops/v_payments_driver_matrix_cabinet.sql`**
   - Agregada protección: payment info solo si `achieved_flag = true`
   - Aplicado a M1, M5 y M25

3. **`backend/scripts/sql/debug_claims_without_achieved.sql`** (nuevo)
   - Script de debug para identificar drivers con violaciones

4. **`backend/scripts/sql/verify_no_claims_without_achieved.sql`** (nuevo)
   - Script de verificación con 5 queries para confirmar que no hay violaciones

## Comandos para Aplicar

### 1. Debug/Evidencia (Opcional)

```bash
# Ejecutar script de debug para encontrar drivers con violaciones
psql $DATABASE_URL -f backend/scripts/sql/debug_claims_without_achieved.sql
```

**Resultado esperado**: Lista de drivers con claims M5 pero sin milestone M5 achieved.

### 2. Aplicar Fixes SQL

```bash
# 1. Aplicar fix en v_claims_payment_status_cabinet
psql $DATABASE_URL -f backend/sql/ops/v_claims_payment_status_cabinet.sql

# 2. Aplicar fix en v_payments_driver_matrix_cabinet
psql $DATABASE_URL -f backend/sql/ops/v_payments_driver_matrix_cabinet.sql
```

### 3. Verificar el Fix

```bash
# Ejecutar script de verificación
psql $DATABASE_URL -f backend/scripts/sql/verify_no_claims_without_achieved.sql
```

**Resultado esperado:**
- Verificación 1: **0 filas** (no hay claims M5 sin milestone M5 achieved)
- Verificación 2: **0 filas** (no hay claims M1 sin milestone M1 achieved)
- Verificación 3: **0 filas** (no hay claims M25 sin milestone M25 achieved)
- Verificación 4: **0 filas** (resumen de violaciones por milestone)
- Verificación 5: **0 filas** (no hay payment_status sin achieved_flag en Driver Matrix)

## Verificación Esperada

### ANTES del Fix

```sql
-- Ejemplo: Driver con claim M5 pero sin milestone M5 achieved
SELECT 
    c.driver_id,
    c.milestone_value,
    c.payment_status,
    m.achieved_flag
FROM ops.v_claims_payment_status_cabinet c
LEFT JOIN ops.v_cabinet_milestones_achieved_from_trips m
    ON m.driver_id = c.driver_id
    AND m.milestone_value = c.milestone_value
WHERE c.milestone_value = 5
    AND m.achieved_flag IS NULL;
-- Resultado: Varios drivers con violación
```

### DESPUÉS del Fix

```sql
-- Misma query
-- Resultado: 0 filas (no hay violaciones)
```

### Driver Matrix

**ANTES**:
```
Driver | M5 Achieved | M5 Payment Status
-------|-------------|------------------
Driver A | false | UNPAID  ❌ (violación)
```

**DESPUÉS**:
```
Driver | M5 Achieved | M5 Payment Status
-------|-------------|------------------
Driver A | false | NULL  ✅ (correcto)
Driver B | true  | UNPAID ✅ (correcto)
```

## Notas Importantes

1. **Regla Canónica Restaurada**: `claim(milestone=N) ⇒ achieved(milestone=N)` ahora se cumple estrictamente

2. **No se rompe historia**: Los claims existentes que tenían milestone determinístico siguen funcionando. Solo se eliminan los claims "fantasma" que no tenían milestone real.

3. **Doble protección**:
   - **Nivel 1**: `v_claims_payment_status_cabinet` no genera claims sin milestone determinístico
   - **Nivel 2**: `v_payments_driver_matrix_cabinet` no muestra payment info si `achieved_flag = false`

4. **Performance**: El `INNER JOIN` con `v_cabinet_milestones_achieved_from_trips` puede tener impacto en performance. Si es necesario, considerar agregar índices en `(driver_id, milestone_value, achieved_flag)`.

## Explicación de la Causa Raíz

El problema ocurría porque:

1. **`v_payment_calculation`** calcula `milestone_achieved` basándose en **ventanas de tiempo** (`window_days`). Si un driver alcanza el milestone dentro de la ventana, marca `milestone_achieved = true`.

2. **`v_cabinet_milestones_achieved_from_trips`** calcula milestones basándose en **viajes reales sin restricción de ventana**. Si un driver alcanzó el milestone fuera de la ventana, puede no aparecer aquí.

3. **`v_claims_payment_status_cabinet`** solo verificaba `milestone_achieved = true` desde `v_payment_calculation`, pero no verificaba si existía milestone determinístico.

**Solución**: Agregar `INNER JOIN` con `v_cabinet_milestones_achieved_from_trips` para exigir milestone determinístico antes de generar claim. Esto garantiza que solo se generen claims cuando existe evidencia real de viajes, independientemente de las ventanas de tiempo.


