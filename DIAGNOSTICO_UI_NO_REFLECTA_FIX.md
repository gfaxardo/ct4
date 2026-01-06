# Diagnóstico: UI No Refleja Fix de Claims M1

## Análisis del Flujo de Datos

### Flujo Actual

```
1. ops.v_claims_payment_status_cabinet (FIX APLICADO)
   ↓ Genera claims M1, M5, M25 cuando están achieved
   
2. ops.v_yango_cabinet_claims_for_collection
   ↓ Depende de v_claims_payment_status_cabinet
   ↓ Genera yango_payment_status (PAID/UNPAID/PAID_MISAPPLIED)
   
3. ops.v_payments_driver_matrix_cabinet
   ↓ Consume:
      - v_cabinet_milestones_achieved_from_trips (para flags achieved)
      - v_claims_payment_status_cabinet (para amounts/overdue)
      - v_yango_cabinet_claims_for_collection (para yango_payment_status)
      - v_yango_payments_claims_cabinet_14d (para window_status)
   
4. Backend API: /api/v1/ops/payments/driver-matrix
   ↓ SELECT desde v_payments_driver_matrix_cabinet
   
5. Frontend: Driver Matrix UI
   ↓ Muestra datos desde API
```

## Problemas Identificados

### Problema 1: Vista `v_payments_driver_matrix_cabinet` usa fuente incorrecta para achieved

**Ubicación**: `backend/sql/ops/v_payments_driver_matrix_cabinet.sql` línea 47

```sql
FROM ops.v_cabinet_milestones_achieved_from_trips m
```

**Problema**: 
- Usa `v_cabinet_milestones_achieved_from_trips` para flags achieved
- Debería usar `v_cabinet_milestones_achieved_from_payment_calc` (source-of-truth canónico)

**Impacto**:
- Si `v_cabinet_milestones_achieved_from_trips` no tiene M1 pero `v_cabinet_milestones_achieved_from_payment_calc` sí, el flag será `false`
- Aunque `v_claims_payment_status_cabinet` genere claim M1, el flag achieved será `false`
- UI mostrará "Sin claim" porque el flag achieved es false

### Problema 2: Lógica de protección en `v_payments_driver_matrix_cabinet`

**Ubicación**: `backend/sql/ops/v_payments_driver_matrix_cabinet.sql` línea 199-200

```sql
CASE WHEN COALESCE(dma.m1_achieved_flag, false) = true 
     THEN ca.m1_expected_amount_yango 
     ELSE NULL 
END AS m1_expected_amount_yango,
```

**Problema**:
- Solo muestra payment info si `m1_achieved_flag = true`
- Si el flag viene de `v_cabinet_milestones_achieved_from_trips` y es `false`, no mostrará payment info aunque exista claim

### Problema 3: Vista `v_yango_payments_claims_cabinet_14d` puede no incluir M1

**Necesita verificación**: Esta vista puede tener filtros que excluyan M1

## Solución Propuesta

### Fix 1: Cambiar fuente de achieved en `v_payments_driver_matrix_cabinet`

**Cambio necesario**:
```sql
-- ANTES:
FROM ops.v_cabinet_milestones_achieved_from_trips m

-- DESPUÉS:
FROM ops.v_cabinet_milestones_achieved_from_payment_calc m
```

**Razón**: 
- `v_cabinet_milestones_achieved_from_payment_calc` es el source-of-truth canónico
- Ya está siendo usado por `v_claims_payment_status_cabinet`
- Garantiza consistencia entre achieved y claims

### Fix 2: Verificar que `v_yango_payments_claims_cabinet_14d` incluya M1

**Necesita revisión**: Verificar que esta vista no tenga filtros que excluyan M1

## Verificación Inmediata (Sin Modificar Código)

### Query 1: Verificar claims M1 generados

```sql
SELECT 
    COUNT(*) AS total_claims_m1,
    COUNT(DISTINCT driver_id) AS unique_drivers_m1
FROM ops.v_claims_payment_status_cabinet
WHERE milestone_value = 1;
```

**Esperado**: Debe mostrar claims M1 generados (ej: 116 según verificación anterior)

### Query 2: Verificar achieved flags en driver_matrix

```sql
SELECT 
    COUNT(*) AS total_drivers,
    COUNT(*) FILTER (WHERE m1_achieved_flag = true) AS m1_achieved_count,
    COUNT(*) FILTER (WHERE m1_expected_amount_yango IS NOT NULL) AS m1_with_claim_count
FROM ops.v_payments_driver_matrix_cabinet
WHERE origin_tag = 'cabinet';
```

**Esperado**: 
- `m1_achieved_count` debe ser igual a drivers con M1 achieved
- `m1_with_claim_count` debe ser igual a `m1_achieved_count` (todos los achieved tienen claim)

### Query 3: Comparar achieved desde ambas fuentes

```sql
WITH achieved_from_trips AS (
    SELECT DISTINCT driver_id
    FROM ops.v_cabinet_milestones_achieved_from_trips
    WHERE milestone_value = 1 AND achieved_flag = true
),
achieved_from_payment_calc AS (
    SELECT DISTINCT driver_id
    FROM ops.v_cabinet_milestones_achieved_from_payment_calc
    WHERE milestone_value = 1 AND achieved_flag = true
)
SELECT 
    'M1 en trips pero NO en payment_calc' AS check_name,
    COUNT(*) AS count
FROM achieved_from_trips t
LEFT JOIN achieved_from_payment_calc p ON p.driver_id = t.driver_id
WHERE p.driver_id IS NULL

UNION ALL

SELECT 
    'M1 en payment_calc pero NO en trips' AS check_name,
    COUNT(*) AS count
FROM achieved_from_payment_calc p
LEFT JOIN achieved_from_trips t ON t.driver_id = p.driver_id
WHERE t.driver_id IS NULL;
```

**Esperado**: 
- Si hay discrepancias, explica por qué UI no muestra claims M1
- Si `v_cabinet_milestones_achieved_from_trips` no tiene M1 pero `v_cabinet_milestones_achieved_from_payment_calc` sí, entonces `v_payments_driver_matrix_cabinet` mostrará `m1_achieved_flag = false`

## Conclusión

**Causa raíz probable**: 
`v_payments_driver_matrix_cabinet` usa `v_cabinet_milestones_achieved_from_trips` para flags achieved, que puede no tener M1 aunque `v_cabinet_milestones_achieved_from_payment_calc` (source-of-truth) sí lo tenga.

**Solución**:
1. Cambiar `v_payments_driver_matrix_cabinet` para usar `v_cabinet_milestones_achieved_from_payment_calc` en lugar de `v_cabinet_milestones_achieved_from_trips`
2. Verificar que `v_yango_payments_claims_cabinet_14d` incluya M1
3. Ejecutar queries de verificación para confirmar

