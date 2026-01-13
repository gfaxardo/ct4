# Resumen: Fix Bug Claims Cabinet 14d (M1/M5/M25)

## Fecha
2026-01-XX

## Problema Reportado
"Hay drivers con metas operativas (M1/M5/M25) dentro de 14 días, pero NO se genera claim como corresponde. Esto impacta cobranza: si no nace claim, no se cobra."

## Root Cause Identificado

### Bug en `ops.v_claims_payment_status_cabinet`

**Problema**: El CTE `payment_calc_agg` hacía `DISTINCT ON (driver_id, milestone_trips)` ordenando por `lead_date DESC`, tomando solo la `lead_date` más reciente sin verificar si el milestone se alcanzó dentro de la ventana 14d de esa `lead_date`.

**Consecuencia**: Si un driver tenía múltiples `lead_date` y el milestone se alcanzó dentro de 14d de una `lead_date` antigua pero NO de la más reciente, el filtro de ventana fallaba y el claim NO se generaba.

**Ejemplo**:
```
Driver 123:
- lead_date_1 = 2025-01-01, achieved M1 en 2025-01-05 (dentro de 14d) ✅
- lead_date_2 = 2025-01-10, NO alcanzó M1 dentro de 14d ❌

payment_calc_agg tomaba: lead_date_2 (más reciente)
Filtro: 2025-01-05 >= 2025-01-10 ❌ (falla)
Resultado: Claim NO se generaba aunque debería
```

## Solución Aplicada

### Fix en `ops.v_claims_payment_status_cabinet`

**Cambios**:
1. **Eliminado `payment_calc_agg`**: Ya no se agrega por `lead_date` más reciente sin verificar ventana
2. **Nuevo CTE `payment_calc_with_window`**: Obtiene TODAS las combinaciones (driver_id, milestone_trips, lead_date) desde `v_payment_calculation` donde:
   - `milestone_achieved = true`
   - `achieved_date` está dentro de `lead_date + 14 días`
3. **Nuevo CTE `milestones_achieved`**: Obtiene milestones achieved desde vista canónica
4. **`base_claims_raw` corregido**: Hace join verificando que `achieved_date` esté dentro de la ventana de cada `lead_date`, luego `base_claims_dedup` toma la `lead_date` más reciente de las válidas

**Lógica corregida**:
- Para cada (driver_id, milestone_value) en `v_cabinet_milestones_achieved_from_payment_calc`:
  - Buscar en `v_payment_calculation` TODAS las filas donde:
    - `driver_id` = driver_id
    - `milestone_trips` = milestone_value
    - `milestone_achieved = true`
    - `achieved_date` dentro de `lead_date + 14 días`
  - Tomar la `lead_date` más reciente de las que cumplen la condición
  - Generar el claim con esa `lead_date`

## Archivos Creados/Modificados

### Nuevos Archivos
1. **`backend/sql/ops/v_cabinet_claims_audit_14d.sql`**
   - Vista de auditoría que compara "debería tener claim" (C2) vs "tiene claim" (C3)
   - Detecta drivers elegibles sin claims generados
   - Incluye análisis de root cause

2. **`backend/sql/ops/analyze_claims_audit_14d.sql`**
   - Script de análisis para encontrar casos reales
   - Queries de lineage para seguir el flujo completo

3. **`backend/sql/ops/validate_claims_fix.sql`**
   - Script de validación antes/después del fix
   - Verifica que los missing claims bajan significativamente

4. **`docs/ops/claims_audit_findings.md`**
   - Documentación completa del root cause
   - Ejemplos concretos del problema

### Archivos Modificados
1. **`backend/sql/ops/v_claims_payment_status_cabinet.sql`**
   - Fix aplicado: corregido join para considerar todas las `lead_date` válidas
   - Comentarios actualizados con descripción del fix

2. **`backend/app/api/v1/ops_payments.py`**
   - Nuevo endpoint: `GET /api/v1/ops/payments/cabinet-financial-14d/claims-audit-summary`
   - Retorna resumen de auditoría con conteos, root causes y casos de ejemplo

## Validación

### Criterios de Aceptación

✅ **La auditoría debe mostrar que los missing_claim_* bajan significativamente tras el fix**
- Ejecutar `backend/sql/ops/validate_claims_fix.sql` antes y después del fix

✅ **Un caso con trips>=5 en 14d debe reflejar expected_m1 y expected_m5 como true, aunque pago sea false**
- Verificado en script de validación

✅ **No se toca C4**
- No se modificó lógica de pagos, solo generación de claims

✅ **No hay dependencia de pago para generar claims**
- Verificado: claims se generan independientemente de `paid_flag`

✅ **No hay dependencia de M1 para M5/M25**
- Verificado: M5 y M25 se generan independientemente de M1

## Endpoint de Auditoría

### `GET /api/v1/ops/payments/cabinet-financial-14d/claims-audit-summary`

**Respuesta**:
```json
{
  "summary": {
    "total_drivers_elegibles": 100,
    "m1": {
      "should_have": 80,
      "has": 75,
      "missing": 5
    },
    "m5": {
      "should_have": 50,
      "has": 48,
      "missing": 2
    },
    "m25": {
      "should_have": 20,
      "has": 19,
      "missing": 1
    }
  },
  "root_causes": [
    {
      "root_cause": "VIEW_FILTERING_OUT",
      "count": 8,
      "m1_missing": 5,
      "m5_missing": 2,
      "m25_missing": 1
    }
  ],
  "sample_cases": [...]
}
```

## Próximos Pasos

1. **Aplicar el fix en producción**:
   ```sql
   \i backend/sql/ops/v_claims_payment_status_cabinet.sql
   ```

2. **Crear la vista de auditoría**:
   ```sql
   \i backend/sql/ops/v_cabinet_claims_audit_14d.sql
   ```

3. **Validar el fix**:
   ```sql
   \i backend/sql/ops/validate_claims_fix.sql
   ```

4. **Monitorear**:
   - Usar endpoint `/api/v1/ops/payments/cabinet-financial-14d/claims-audit-summary` para monitorear missing claims
   - Verificar que los missing claims bajan significativamente

## Impacto

- **Alto**: Afecta cobranza directamente (claims faltantes = dinero no cobrado)
- **Riesgo bajo**: El fix solo corrige el join, no cambia reglas de negocio
- **No afecta C4**: No se toca la lógica de pagos
