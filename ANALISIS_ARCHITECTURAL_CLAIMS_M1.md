# Análisis Arquitectónico: Fix Generación de Claims M1 para Cabinet

## Problema Identificado

**Síntoma**: Para `origin_tag='cabinet'`, existen casos donde drivers tienen claim de M5 pero **NO tienen claim de M1**, aunque M1 fue achieved dentro de la ventana de 14 días.

**Impacto**: 
- UI muestra M1 como achieved (check verde) pero sin status (UNPAID/PAID/etc) porque no existe claim
- Inconsistencia de datos: claim M5 sin claim M1 cuando ambos deberían existir
- Pérdida de cobranza: M1 no se puede cobrar aunque esté achieved

## Análisis del Flujo Actual

### 1. Flujo de Generación de Claims

```
ops.v_payment_calculation
  ↓ (fila por person_key + origin_tag + rule_id)
  ↓ Calcula milestone_achieved y achieved_date basándose en viajes acumulados
  ↓ Puede tener múltiples filas por (driver_id, milestone_trips) si hay múltiples reglas activas
  ↓
ops.v_cabinet_milestones_achieved_from_payment_calc
  ↓ (agregado por driver_id + milestone_trips)
  ↓ bool_or(milestone_achieved) y min(achieved_date)
  ↓ 1 fila por (driver_id, milestone_value)
  ↓
ops.v_claims_payment_status_cabinet
  ↓ (JOIN con v_payment_calculation)
  ↓ PROBLEMA: JOIN puede duplicar filas si hay múltiples reglas
  ↓ PROBLEMA: Validación de ventana puede fallar si lead_date no coincide
```

### 2. Causa Raíz del Bug

**Problema 1: JOIN sin agregado canónico**
- `v_claims_payment_status_cabinet` hacía JOIN directo entre `v_cabinet_milestones_achieved_from_payment_calc` (1 fila por driver+milestone) y `v_payment_calculation` (múltiples filas posibles por driver+milestone si hay múltiples reglas)
- Esto podía crear duplicados o perder filas si el JOIN no encontraba coincidencia exacta

**Problema 2: Validación de ventana dependiente de JOIN**
- La validación de ventana de 14 días se hacía en el JOIN: `m.achieved_date::date <= (pc.lead_date + INTERVAL '14 days')::date`
- Si `v_payment_calculation` tenía múltiples filas con diferentes `lead_date`, el JOIN podía fallar o seleccionar el `lead_date` incorrecto

**Problema 3: Falta de agregado canónico**
- No existía un agregado canónico de `v_payment_calculation` que garantizara 1 fila por (driver_id, milestone_trips) antes del JOIN
- Esto permitía que múltiples reglas activas crearan inconsistencias

### 3. Por Qué M1 No Se Generaba

**Escenario típico del bug:**
1. Driver logra M1 en día 3 (achieved_date = lead_date + 3 días) ✅
2. Driver logra M5 en día 7 (achieved_date = lead_date + 7 días) ✅
3. `v_cabinet_milestones_achieved_from_payment_calc` muestra ambos como achieved ✅
4. `v_claims_payment_status_cabinet` hace JOIN con `v_payment_calculation`:
   - Para M5: encuentra fila con `lead_date` correcto → genera claim ✅
   - Para M1: **NO encuentra fila con `lead_date` que coincida** o encuentra fila con `lead_date` diferente que falla validación de ventana → **NO genera claim** ❌

**Razón técnica:**
- `v_payment_calculation` puede tener múltiples filas por (driver_id, milestone_trips) si hay múltiples reglas activas
- El JOIN sin agregado canónico puede seleccionar una fila con `lead_date` incorrecto para M1
- La validación de ventana falla porque `achieved_date` no está dentro de `lead_date + 14 días` de la fila seleccionada

## Solución Implementada

### 1. Agregado Canónico de `v_payment_calculation`

**Nuevo CTE `payment_calc_agg`:**
```sql
payment_calc_agg AS (
    SELECT DISTINCT ON (driver_id, milestone_trips)
        driver_id,
        person_key,
        lead_date,
        milestone_trips,
        milestone_achieved,
        achieved_date
    FROM ops.v_payment_calculation
    WHERE origin_tag = 'cabinet'
        AND rule_scope = 'partner'
        AND milestone_trips IN (1, 5, 25)
        AND driver_id IS NOT NULL
        AND milestone_achieved = true
    ORDER BY driver_id, milestone_trips, lead_date DESC, achieved_date ASC
)
```

**Beneficios:**
- Garantiza 1 fila por (driver_id, milestone_trips)
- Selecciona `lead_date` más reciente (más conservador)
- Elimina duplicados antes del JOIN
- Asegura que M1, M5 y M25 se traten de forma consistente

### 2. JOIN Simplificado y Seguro

**Antes:**
```sql
FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
INNER JOIN ops.v_payment_calculation pc
    ON pc.driver_id = m.driver_id
    AND pc.milestone_trips = m.milestone_value
    AND pc.origin_tag = 'cabinet'
    AND pc.rule_scope = 'partner'
    AND pc.milestone_achieved = true
```

**Después:**
```sql
FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
INNER JOIN payment_calc_agg pc_agg
    ON pc_agg.driver_id = m.driver_id
    AND pc_agg.milestone_trips = m.milestone_value
```

**Beneficios:**
- JOIN más simple y eficiente
- No depende de múltiples condiciones en el JOIN
- Garantiza 1:1 entre `m` y `pc_agg`

### 3. Validación Explícita de Ventana

**Validación mejorada:**
```sql
WHERE m.achieved_flag = true
    AND m.milestone_value IN (1, 5, 25)
    AND m.driver_id IS NOT NULL
    -- Ventana de 14 días: achieved_date debe estar dentro de lead_date + 14 días
    AND m.achieved_date::date <= (pc_agg.lead_date + INTERVAL '14 days')::date
    AND m.achieved_date::date >= pc_agg.lead_date
```

**Beneficios:**
- Validación explícita y clara
- Usa `lead_date` del agregado canónico (garantizado correcto)
- Aplica a M1, M5 y M25 de forma consistente

### 4. Catálogo Centralizado de Montos

**CTE `milestone_amounts`:**
```sql
milestone_amounts AS (
    SELECT 1 AS milestone_value, 25::numeric(12,2) AS expected_amount
    UNION ALL SELECT 5, 35::numeric(12,2)
    UNION ALL SELECT 25, 100::numeric(12,2)
)
```

**Beneficios:**
- Única fuente de verdad para montos
- Fácil de mantener y actualizar
- Evita repetir lógica CASE en múltiples lugares

## Garantías del Fix

### ✅ Grano Correcto
- **Grano final**: `(driver_id, milestone_value)` - 1 fila por claim
- **Deduplicación**: `DISTINCT ON (driver_id, milestone_value)` con `lead_date DESC`
- **Sin duplicados**: Agregado canónico previene duplicados antes del JOIN

### ✅ Consistencia de Claims
- **M1, M5, M25 independientes**: Cada milestone genera claim si está achieved
- **No asume acumulación**: M5 no asume M1, pero si M1 está achieved, genera claim
- **Ventana consistente**: Misma lógica de 14 días para todos los milestones

### ✅ Compatibilidad con UI
- **No rompe frontend**: Campos existentes (`yango_payment_status`, `expected_amount`, etc.) se mantienen
- **Achieved vs Paid separados**: `achieved_flag` viene de `v_cabinet_milestones_achieved_from_payment_calc`, `paid_flag` viene de `v_yango_payments_ledger_latest_enriched`
- **Status correcto**: Si no hay pago, `yango_payment_status = 'UNPAID'` (no NULL)

### ✅ No Mezcla Achieved con Paid
- **Source-of-truth achieved**: `ops.v_cabinet_milestones_achieved_from_payment_calc`
- **Source-of-truth paid**: `ops.v_yango_payments_ledger_latest_enriched`
- **Lógica separada**: JOINs separados para achieved y paid

## Verificación Implementada

### CHECK 1: M1 achieved en ventana sin claim M1
- **Esperado**: 0
- **Valida**: Todos los drivers con M1 achieved dentro de ventana tienen claim M1

### CHECK 2: Claim M5 sin claim M1 (cuando M1 achieved)
- **Esperado**: 0
- **Valida**: No existen inconsistencias donde M5 tiene claim pero M1 no (cuando M1 está achieved)

### CHECK 3: Duplicados por grano
- **Esperado**: 0
- **Valida**: No hay duplicados por (driver_id + milestone_value)

### CHECK 4: Validación de montos
- **Esperado**: M1=25, M5=35, M25=100
- **Valida**: Montos esperados son correctos para todos los claims

### CHECK 5: Spot-check de 20 drivers
- **Muestra**: driver_id, milestone_value, achieved_flag, achieved_date, expected_amount, yango_payment_status
- **Valida**: Casos reales de M1 achieved vs claims generados

### RESUMEN: Distribución achieved vs claims
- **Muestra**: Total achieved vs total claims por milestone
- **Valida**: Alineación completa entre achieved y claims

## Explicación Breve del Bug y Fix

**Por qué existía el bug:**
El JOIN entre `v_cabinet_milestones_achieved_from_payment_calc` y `v_payment_calculation` podía fallar para M1 cuando había múltiples reglas activas, seleccionando un `lead_date` incorrecto que hacía fallar la validación de ventana de 14 días. M5 funcionaba porque típicamente tenía menos reglas activas o un `lead_date` más reciente.

**Por qué queda resuelto:**
El agregado canónico `payment_calc_agg` garantiza 1 fila por (driver_id, milestone_trips) con el `lead_date` más reciente, eliminando duplicados antes del JOIN. Esto asegura que M1, M5 y M25 se traten de forma consistente y que la validación de ventana siempre use el `lead_date` correcto.

