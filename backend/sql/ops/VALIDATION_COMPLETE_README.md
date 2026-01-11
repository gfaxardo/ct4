# Guía Completa de Validación - Pagos Yango con Matching Fallback

Esta guía explica cómo validar todo el sistema de pagos Yango después de implementar el matching fallback.

## Archivos SQL de Validación

1. **`validation_paid_status.sql`**: Validación inicial del problema (Total Paid = 0)
2. **`validation_ledger_missing_driver.sql`**: Validación del matching fallback y ledger sin driver_id

## Pasos de Validación en pgAdmin

### Paso 1: Validar Estado Inicial

Ejecutar `validation_paid_status.sql`:
- Query 1: Verificar distribución de `paid_status`
- Query 2: Verificar si hay registros con `paid_status='paid'`
- Query 3: Contar registros en ledger
- Query 4: Verificar matches reales

**Resultado esperado si el problema existe:**
- `count_paid = 0` (no hay pagos reconciliados)
- `total_ledger_rows > 0` (hay registros en ledger)
- `count_matches = 0` (no hay matches por driver_id)

### Paso 2: Validar Matching Fallback

Ejecutar `validation_ledger_missing_driver.sql`:
- Query 1: Verificar ledger rows con driver_id NULL
- Query 2: Ver lista de pagos sin driver_id
- Query 3: Verificar matches por driver_id
- Query 4: Verificar matches por person_key (FALBACK)
- Query 5: Ver ledger sin match
- Query 6: Distribución de match_method
- Query 7: Claims sin driver_id con person_key
- Query 8: Resumen ejecutivo

**Resultado esperado después del fix:**
- Query 4: `count_matches > 0` (matches por person_key funcionando)
- Query 6: `match_method = 'person_key'` tiene `count_paid > 0`
- Query 8: `claims_matched_by_person_key > 0`

### Paso 3: Verificar Vista Actualizada

```sql
-- Verificar que la vista tiene match_method correcto
SELECT 
    match_method,
    COUNT(*) AS count,
    COUNT(*) FILTER (WHERE paid_status = 'paid') AS count_paid,
    SUM(expected_amount) FILTER (WHERE paid_status = 'paid') AS amount_paid
FROM ops.v_yango_payments_claims_cabinet_14d
GROUP BY match_method
ORDER BY match_method;
```

**Resultado esperado:**
- `match_method = 'driver_id'`: Algunos registros con `count_paid > 0`
- `match_method = 'person_key'`: Algunos registros con `count_paid > 0` (nuevo)
- `match_method = 'none'`: Muy pocos o cero con `paid_status = 'paid'`

### Paso 4: Verificar Endpoint de Unmatched

```sql
-- Simular lo que hace el endpoint /ledger/unmatched
SELECT COUNT(*) 
FROM ops.v_yango_payments_ledger_latest l
WHERE l.is_paid = true
    AND (
        l.driver_id IS NULL
        OR NOT EXISTS (
            SELECT 1 FROM ops.v_yango_payments_claims_cabinet_14d c
            WHERE c.driver_id = l.driver_id 
                AND c.milestone_value = l.milestone_value
        )
    )
    AND (
        l.person_key IS NULL
        OR NOT EXISTS (
            SELECT 1 FROM ops.v_yango_payments_claims_cabinet_14d c
            WHERE c.person_key = l.person_key 
                AND c.milestone_value = l.milestone_value
        )
    );
```

Este conteo debe coincidir con lo que retorna el endpoint `/api/v1/yango/payments/reconciliation/ledger/unmatched?is_paid=true`

## Validación en Frontend (UI)

### Paso 1: Dashboard Principal

1. Ir a `/pagos` → Tab Yango
2. Verificar KPIs Cards:
   - **Total Expected**: > 0
   - **Total Paid**: Debe ser > 0 si hay matches (antes era 0)
   - **Total Diff**: Debe cambiar según el modo (Real/Estimado)
   - **Total Anomalías**: `pending_expired` count
   - **Ledger SIN Conductor**: Nuevo card que muestra `ledger_rows_is_paid_true_and_driver_id_null`

3. Verificar Tooltips:
   - Hover sobre "Total Paid": Debe mostrar el tooltip explicativo
   - Hover sobre "Pagos Estimados": Debe mostrar tooltip de proyección

### Paso 2: Modal "Ver Ledger sin match"

1. Click en botón "Ver Ledger sin match" en el card "Ledger SIN Conductor"
2. Verificar que el modal abre correctamente
3. Verificar columnas en la tabla:
   - Payment Key
   - Pay Date
   - Milestone
   - Driver ID (debe mostrar "NULL" en rojo si es NULL)
   - Person Key
   - Driver Name
   - Match Rule
   - Match Confidence
   - Is Paid (chip verde si es true)

4. Verificar que los datos coinciden con Query 5 de `validation_ledger_missing_driver.sql`

### Paso 3: Panel Debug

1. Click en botón "🐛 Debug" (esquina inferior derecha, solo en desarrollo)
2. Verificar que muestra:
   - **Mode**: real o assumed
   - **Filtros Enviados**: Parámetros enviados al backend
   - **Filtros Recibidos**: Respuesta del backend (incluye `_validation`)
   - **Paid Status Distribution**: paid, pending_active, pending_expired counts
   - **Ledger Count**: Total de registros en ledger
   - **Validation (Backend)**: Métricas extendidas:
     - `paid_total`: Monto total pagado
     - `count_paid`: Conteo de registros pagados
     - `ledger_total_rows`: Total de registros en ledger
     - `ledger_rows_is_paid_true`: Registros pagados en ledger
     - `ledger_rows_driver_id_null`: Registros sin driver_id
     - `ledger_rows_is_paid_true_and_driver_id_null`: Pagos sin driver_id
     - `ledger_distinct_payment_keys`: Payment keys únicos

3. Verificar advertencias:
   - Si `ledger_count > 0` pero `count_paid = 0`: Muestra advertencia sobre posible problema de matching

### Paso 4: Drilldown de Items

1. Click en "Ver Detalle" en una semana de la tabla
2. Verificar tabs:
   - Pagados
   - Pendientes Activos
   - Vencidos (default)
   - Todos

3. Verificar que los items pagados muestran:
   - `paid_status = 'paid'` (chip verde)
   - `match_method`: 'driver_id' o 'person_key'
   - `paid_payment_key`: Debe tener valor si está pagado
   - `paid_date`: Debe tener valor si está pagado

4. Verificar que los items sin conductor muestran "SIN CONDUCTOR" en rojo

## Checklist de Validación Final

### Backend

- [ ] Vista `v_yango_payments_claims_cabinet_14d` se crea sin errores
- [ ] Query de validación en `/summary` retorna métricas extendidas
- [ ] Endpoint `/ledger/unmatched` retorna datos correctamente
- [ ] Los logs muestran información de validación

### Frontend

- [ ] Card "Ledger SIN Conductor" aparece y muestra conteo correcto
- [ ] Botón "Ver Ledger sin match" abre modal
- [ ] Modal muestra tabla con datos del ledger
- [ ] Tooltips aparecen en KPIs
- [ ] Panel Debug muestra información de validación
- [ ] Drilldown muestra `match_method` correcto

### Datos

- [ ] Total Paid > 0 si hay matches (antes era 0)
- [ ] `match_method = 'person_key'` tiene registros con `paid_status = 'paid'`
- [ ] Conteo de "Ledger SIN Conductor" coincide con query SQL
- [ ] Modal "Ver Ledger sin match" muestra registros que realmente no tienen match

## Solución de Problemas

### Problema: Total Paid sigue siendo 0

**Verificar:**
1. Ejecutar Query 4 de `validation_ledger_missing_driver.sql`
2. Si `count_matches = 0` para person_key:
   - Verificar Query 1: ¿Los registros del ledger tienen `person_key`?
   - Verificar Query 7: ¿Los claims sin driver_id tienen `person_key`?
   - Si ambos tienen person_key pero no matchean, revisar la lógica de la vista

### Problema: Modal "Ver Ledger sin match" está vacío

**Verificar:**
1. Verificar que `ledger_rows_is_paid_true_and_driver_id_null > 0` en el card
2. Verificar en pgAdmin que Query 5 de `validation_ledger_missing_driver.sql` retorna datos
3. Verificar logs del backend para errores en el endpoint `/ledger/unmatched`

### Problema: match_method siempre es 'none'

**Verificar:**
1. Revisar la vista `v_yango_payments_claims_cabinet_14d` en pgAdmin
2. Verificar que los JOINs están correctos
3. Verificar que las condiciones de matching están bien escritas
4. Ejecutar manualmente partes de la vista para debug

## Resultado Esperado Final

Después de implementar el matching fallback:

1. **Total Paid > 0**: Si hay pagos en el ledger (con o sin driver_id)
2. **match_method incluye 'person_key'**: Indica que el fallback está funcionando
3. **Card "Ledger SIN Conductor" muestra conteo**: Indica transparencia sobre pagos no atribuibles
4. **Modal muestra registros sin match**: Permite auditoría manual
5. **Panel Debug tiene información completa**: Facilita troubleshooting

El sistema ahora puede reconciliar pagos reales aunque el ledger venga sin driver_id, siempre que tengan person_key en común.







