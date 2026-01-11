# Validación: Total Paid = 0 en Pagos Yango

Este documento contiene las queries SQL para validar por qué Total Paid = 0 y entender la realidad de los datos.

## Archivo SQL

Ejecutar todas las queries del archivo: `backend/sql/ops/validation_paid_status.sql`

## Interpretación de Resultados

### Query 1: Conteos por paid_status

**Resultado esperado:**
- Si `count_paid_rows = 0` → No hay registros con `paid_status='paid'` → **Total Paid = 0 es CORRECTO**
- Si `count_paid_rows > 0` pero `total_paid_amount = 0` → Hay registros marcados como 'paid' pero con expected_amount NULL → **Revisar lógica**

### Query 2: Conteo específico de paid_status='paid'

**Resultado esperado:**
- Si `count_paid_rows = 0` → Confirmación de que no hay pagos reales
- Si `count_paid_rows > 0` → Hay pagos pero no se están mostrando correctamente

### Query 3: Registros en ops.v_yango_payments_ledger_latest

**Resultado esperado:**
- Si `total_ledger_rows = 0` → No hay pagos registrados en el ledger → **Total Paid = 0 es CORRECTO**
- Si `total_ledger_rows > 0` pero `count_paid = 0` → Hay pagos en el ledger pero NO matchean con claims → **Problema de matching**

### Query 4: Matches reales (driver_id + milestone_value)

**Resultado esperado:**
- Si `count_matches = 0` → No hay matches entre claims y ledger → **Problema de matching**
- Si `count_matches > 0` → Hay matches pero la lógica de `paid_status` no los está capturando correctamente

### Query 5: Registros con driver_id NULL

**Resultado esperado:**
- Si `count_without_driver_id > 0` → Hay claims sin driver_id (no matchables por driver_id)
- Estos registros NUNCA podrán matchear con el ledger si el matching es solo por driver_id

### Query 6: is_paid_effective

**Resultado esperado:**
- Si `count_is_paid_effective_true > 0` pero `count_paid = 0` → Hay registros con indicadores de pago pero `paid_status != 'paid'` → **Revisar lógica de paid_status**

### Query 7: Indicadores de pago

**Resultado esperado:**
- Comparar `count_with_any_paid_indicator` vs `count_paid`
- Si hay diferencia → Hay registros con indicadores de pago pero no marcados como 'paid'

### Query 8: Comparación Claims vs Ledger

**Resultado esperado:**
- Revisar manualmente si hay driver_id + milestone_value que coincidan entre ambas vistas
- Si hay coincidencias pero no matchean → Revisar la lógica del JOIN en `v_yango_payments_claims_cabinet_14d`

## Conclusiones Típicas

### Escenario 1: No hay pagos reales
- `total_ledger_rows = 0`
- `count_paid = 0`
- **Conclusión**: Total Paid = 0 es correcto. No hay pagos registrados aún.

### Escenario 2: Hay pagos pero no matchean
- `total_ledger_rows > 0`
- `count_matches = 0`
- `count_paid = 0`
- **Conclusión**: Hay pagos en el ledger pero no matchean con claims. Posibles causas:
  - driver_id diferente entre ledger y claims
  - milestone_value diferente
  - Claims sin driver_id (NULL)

### Escenario 3: Matches existen pero paid_status incorrecto
- `count_matches > 0`
- `count_with_any_paid_indicator > 0`
- `count_paid = 0`
- **Conclusión**: Hay matches pero la lógica de `paid_status` no los está marcando como 'paid'. Revisar la lógica en `v_yango_payments_claims_cabinet_14d`.

## Recomendaciones

1. Si `count_paid = 0` y `total_ledger_rows = 0`: ✅ Sistema funcionando correctamente, solo que no hay pagos aún.

2. Si `count_paid = 0` pero `total_ledger_rows > 0` y `count_matches = 0`: 
   - Revisar el matching en `v_yango_payments_claims_cabinet_14d`
   - Considerar agregar fallback por person_key si driver_id es NULL

3. Si `count_paid = 0` pero `count_with_any_paid_indicator > 0`:
   - Revisar la lógica de `paid_status` en `v_yango_payments_claims_cabinet_14d`
   - Asegurar que todos los indicadores de pago están siendo considerados

4. Siempre documentar los resultados en el panel Debug del frontend para transparencia.







