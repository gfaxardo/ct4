# Validación: Ledger con driver_id NULL y Matching Fallback

Este documento explica cómo validar el estado del ledger y el matching fallback implementado.

## Archivo SQL

Ejecutar todas las queries del archivo: `backend/sql/ops/validation_ledger_missing_driver.sql`

## Contexto

El problema identificado:
- `ops.v_yango_payments_ledger_latest` tiene registros pagados (`is_paid = true`)
- Muchos de estos registros tienen `driver_id IS NULL`
- El matching original solo usaba `driver_id + milestone_value`
- Resultado: Total Paid = 0 aunque hay pagos reales en el ledger

## Solución Implementada

### Matching en `v_yango_payments_claims_cabinet_14d`

La vista ahora implementa matching con fallback:

1. **Match #1 (Prioridad)**: `driver_id + milestone_value`
   - Usado cuando ambos (claims y ledger) tienen `driver_id` no NULL
   - `match_method = 'driver_id'`

2. **Match #2 (Fallback)**: `person_key + milestone_value`
   - Usado cuando `driver_id IS NULL` en ambos (claims y ledger)
   - Requiere que `person_key` no sea NULL en ambos
   - `match_method = 'person_key'`

3. **Sin Match**: `match_method = 'none'`
   - Cuando no existe match por ninguno de los métodos anteriores

## Interpretación de Queries

### Query 1: Ledger rows con driver_id NULL

**Resultado esperado:**
- `count_rows`: Total de registros en ledger con `driver_id IS NULL`
- `count_is_paid_true`: Cuántos de estos están pagados
- `count_with_person_key`: Cuántos tienen `person_key` (potencialmente matchables)
- `count_is_paid_true_with_person_key`: Pagos sin driver_id pero con person_key (matchables por fallback)

### Query 2: Ledger paid rows con driver_id NULL

**Resultado esperado:**
- Lista detallada de los primeros 20 pagos sin driver_id
- Permite ver si tienen `person_key` para matching fallback
- Útil para auditoría manual

### Query 3: Overlap Claims vs Ledger por driver_id

**Resultado esperado:**
- `count_matches`: Número de claims matcheados por `driver_id`
- `total_matched_amount`: Monto total matcheado por este método
- Debe ser > 0 si hay pagos con driver_id

### Query 4: Overlap Claims vs Ledger por person_key (Fallback)

**Resultado esperado:**
- `count_matches`: Número de claims matcheados por `person_key` (fallback)
- `total_matched_amount`: Monto total matcheado por este método
- Debe ser > 0 si el fallback está funcionando

**Si es 0:**
- Puede significar que no hay claims sin driver_id, O
- Los claims sin driver_id tampoco tienen person_key, O
- El ledger sin driver_id tampoco tiene person_key

### Query 5: Top 20 Ledger Paid Rows que NO matchean ningún Claim

**Resultado esperado:**
- Lista de pagos en el ledger que NO tienen match en claims
- `unmatched_reason` indica por qué:
  - `driver_id_null`: No tiene driver_id
  - `no_match_by_driver_id`: Tiene driver_id pero no hay claim correspondiente
  - `no_match_by_person_key`: Tiene person_key pero no hay claim correspondiente
  - `unknown`: Caso no esperado

**Si hay muchos registros aquí:**
- Indica pagos que no se pueden atribuir a ningún claim
- Puede ser esperado (pagos sin expected asociado)
- O puede indicar problema en el proceso de atribución

### Query 6: Distribución de match_method en Claims

**Resultado esperado:**
- `match_method = 'driver_id'`: Matches por método principal
- `match_method = 'person_key'`: Matches por fallback
- `match_method = 'none'`: Sin match

**Validación:**
- Si `count_paid` > 0 para `match_method = 'person_key'` → El fallback está funcionando
- Si `count_paid` = 0 para todos → No hay pagos reconciliados (revisar Query 5)

### Query 7: Claims sin driver_id que pueden matchear por person_key

**Resultado esperado:**
- Cuántos claims sin driver_id tienen `person_key` (potencialmente matchables)
- `count_matched_by_person_key`: Cuántos de estos fueron matcheados exitosamente

**Si `count_matched_by_person_key` < `count_rows`:**
- Indica que algunos claims con person_key no tienen match en ledger
- Puede ser porque el ledger también tiene `person_key IS NULL`

### Query 8: Resumen Ejecutivo

**Resultado esperado:**
- Vista general del estado del matching
- Compara:
  - Pagos en ledger sin driver_id
  - Matches exitosos por driver_id
  - Matches exitosos por person_key (fallback)
  - Claims pagados sin match (debería ser 0 si todo funciona)
  - Claims sin driver_id pero con person_key

## Validación en Frontend

1. Abrir `/pagos` → Tab Yango
2. Verificar el card "Ledger SIN Conductor":
   - Debe mostrar el conteo de `ledger_rows_is_paid_true_and_driver_id_null`
   - Si es > 0, hay pagos sin conductor
3. Click en "Ver Ledger sin match":
   - Abre modal con lista de registros pagados que no matchean
   - Verificar que muestra payment_key, pay_date, milestone, etc.
4. Verificar Panel Debug (🐛):
   - `paidStatusDistribution`: Muestra distribución de paid/pending_active/pending_expired
   - `ledger_total_rows`: Total de registros en ledger
   - `Validation (Backend)`: Muestra métricas extendidas del ledger

## Escenarios Típicos

### Escenario 1: Fallback funcionando correctamente
- `ledger_rows_is_paid_true_and_driver_id_null` > 0
- `claims_matched_by_person_key` > 0
- `claims_paid_without_match` = 0 (o muy bajo)
- **Conclusión**: ✅ El fallback está funcionando, pagos sin driver_id están siendo reconciliados por person_key

### Escenario 2: Fallback no disponible (person_key NULL)
- `ledger_rows_is_paid_true_and_driver_id_null` > 0
- `count_with_person_key` = 0 (en Query 1)
- `claims_matched_by_person_key` = 0
- **Conclusión**: ⚠️ Hay pagos sin driver_id pero también sin person_key. No se pueden reconciliar con el método actual.

### Escenario 3: Claims sin person_key
- `claims_without_driver_id_but_with_person_key` = 0
- `claims_matched_by_person_key` = 0
- **Conclusión**: ⚠️ Los claims sin driver_id tampoco tienen person_key, no pueden usar el fallback.

### Escenario 4: Todo funcionando
- `claims_matched_by_driver_id` > 0
- `claims_matched_by_person_key` > 0
- `claims_paid_without_match` = 0
- Total Paid > 0 en el dashboard
- **Conclusión**: ✅ Sistema funcionando correctamente, ambos métodos de matching están activos.

## Recomendaciones

1. Si `ledger_rows_is_paid_true_and_driver_id_null` > 0 pero `claims_matched_by_person_key` = 0:
   - Revisar si los claims sin driver_id tienen `person_key`
   - Revisar si el ledger sin driver_id tiene `person_key`
   - Si ambos tienen person_key pero no matchean, revisar la lógica de la vista

2. Si hay muchos registros en Query 5 (ledger sin match):
   - Puede ser esperado si hay pagos sin expected asociado
   - O puede indicar problema en el proceso de atribución/lead generation
   - Revisar manualmente algunos registros para entender el patrón

3. Monitorear la distribución de `match_method`:
   - Si `match_method = 'none'` tiene muchos registros con `paid_status = 'paid'`, hay un problema
   - Debe haber muy pocos o cero registros con `paid_status = 'paid'` y `match_method = 'none'`





