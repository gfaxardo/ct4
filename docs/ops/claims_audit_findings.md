# Findings: Bug en Generación de Claims Cabinet 14d (M1/M5/M25)

## Fecha de Análisis
2026-01-XX

## Problema Reportado
"Hay drivers con metas operativas (M1/M5/M25) dentro de 14 días, pero NO se genera claim como corresponde. Esto impacta cobranza: si no nace claim, no se cobra."

## Análisis de Root Cause

### Vista Actual: `ops.v_claims_payment_status_cabinet`

**Líneas 45-85**: La vista usa la siguiente lógica:

1. **`payment_calc_agg`** (líneas 45-62):
   - Hace `DISTINCT ON (driver_id, milestone_trips)` 
   - Ordena por `lead_date DESC, achieved_date ASC`
   - **PROBLEMA**: Si un driver tiene múltiples `lead_date` para el mismo milestone, solo toma la **más reciente** (`lead_date DESC`)

2. **`base_claims_raw`** (líneas 63-86):
   - Hace `INNER JOIN` entre:
     - `ops.v_cabinet_milestones_achieved_from_payment_calc` (agregado por driver_id + milestone_value, sin considerar lead_date)
     - `payment_calc_agg` (solo la lead_date más reciente)
   - Filtra por ventana 14d: `m.achieved_date <= (pc_agg.lead_date + 14 days)`

### Root Cause Identificado

**BUG**: El join está perdiendo claims cuando:
- Un driver tiene múltiples `lead_date` (ej: registros en diferentes fechas)
- El milestone se alcanzó dentro de 14d de una `lead_date` **antigua**
- Pero `payment_calc_agg` solo toma la `lead_date` **más reciente**
- Si el milestone NO se alcanzó dentro de 14d de la `lead_date` más reciente, el filtro de ventana falla y el claim NO se genera

**Ejemplo Concreto**:
```
Driver 123:
- lead_date_1 = 2025-01-01, achieved M1 en 2025-01-05 (dentro de 14d) ✅
- lead_date_2 = 2025-01-10, NO alcanzó M1 dentro de 14d ❌

payment_calc_agg toma: lead_date_2 (más reciente)
v_cabinet_milestones_achieved_from_payment_calc tiene: achieved_date = 2025-01-05
Filtro: 2025-01-05 <= (2025-01-10 + 14d) = 2025-01-24 ✅ (pasa)
PERO: 2025-01-05 >= 2025-01-10 ❌ (falla el segundo filtro)

Resultado: Claim NO se genera aunque debería
```

### Reglas Canónicas Violadas

1. **C2 define elegibilidad**: ✅ Correcto - `v_payment_calculation` calcula correctamente
2. **C3 Claims solo nace desde C2**: ❌ **VIOLADO** - El join está filtrando claims válidos
3. **NO se permite que "pago" determine claim**: ✅ Correcto - No hay dependencia de pago
4. **El claim debe existir aunque aún no esté pagado**: ✅ Correcto - No hay dependencia de pago

## Solución Propuesta

### Fix Mínimo

**Cambio en `ops.v_claims_payment_status_cabinet`**:

1. **Eliminar `payment_calc_agg`**: No necesitamos agregar por lead_date más reciente
2. **Usar directamente `v_payment_calculation`**: Para obtener TODAS las combinaciones (driver_id, milestone_trips, lead_date) donde `milestone_achieved = true` dentro de ventana 14d
3. **Simplificar el join**: Unir directamente `v_cabinet_milestones_achieved_from_payment_calc` con `v_payment_calculation` filtrando por ventana 14d

**Lógica corregida**:
- Para cada (driver_id, milestone_value) en `v_cabinet_milestones_achieved_from_payment_calc`:
  - Buscar en `v_payment_calculation` TODAS las filas donde:
    - `driver_id` = driver_id
    - `milestone_trips` = milestone_value
    - `milestone_achieved = true`
    - `achieved_date` dentro de `lead_date + 14 días`
  - Tomar la `lead_date` más reciente de las que cumplen la condición
  - Generar el claim con esa `lead_date`

## Validación

### Queries de Validación

1. **Antes del fix**: Contar missing claims desde `ops.v_cabinet_claims_audit_14d`
2. **Después del fix**: Verificar que los missing claims bajan significativamente
3. **Caso específico**: Un driver con trips>=5 en 14d debe reflejar `expected_m1=true` y `expected_m5=true`, aunque `paid_flag=false`

## Impacto

- **Alto**: Afecta cobranza directamente (claims faltantes = dinero no cobrado)
- **Riesgo bajo**: El fix solo corrige el join, no cambia reglas de negocio
- **No afecta C4**: No se toca la lógica de pagos
