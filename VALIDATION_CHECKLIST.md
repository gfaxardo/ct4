# Checklist de Validación - Pagos Yango Dashboard (con Enriquecimiento de Identidad)

## Pre-requisitos

1. Backend corriendo en `http://localhost:8000`
2. Frontend corriendo en `http://localhost:3000`
3. Base de datos accesible con vistas ejecutadas:
   - `ops.v_yango_payments_claims_cabinet_14d`
   - `ops.v_yango_payments_ledger_latest`
   - `ops.v_yango_payments_ledger_latest_enriched` (NUEVA - debe ejecutarse primero)
4. Ejecutar en pgAdmin (en orden):
   - `backend/sql/ops/v_yango_payments_ledger_latest_enriched.sql`
   - `backend/sql/ops/v_yango_payments_claims_cabinet_14d.sql` (actualizada para usar enriquecida)

## PASO 1: Validar Backend - Endpoints

### 1.1 Summary Endpoint
- [ ] Abrir navegador → Network tab
- [ ] Ir a `/pagos` → Tab Yango
- [ ] Verificar que se llama: `GET /api/v1/yango/payments/reconciliation/summary`
- [ ] Verificar respuesta 200 OK
- [ ] Verificar que `filters._validation` existe y contiene:
  - `ledger_total_rows`
  - `ledger_rows_is_paid_true`
  - `ledger_rows_driver_id_null`
  - `ledger_rows_person_key_null` (NUEVO)
  - `ledger_rows_both_identity_null` (NUEVO)
  - `ledger_rows_identity_enriched` (NUEVO)
  - `ledger_rows_is_paid_true_and_driver_id_null`
  - `matched_paid_rows` (NUEVO)
  - `ledger_distinct_payment_keys`

### 1.2 Ledger Unmatched Endpoint
- [ ] En Network tab, verificar llamada (si se abre modal):
  - `GET /api/v1/yango/payments/reconciliation/ledger/unmatched?is_paid=true&limit=1000`
- [ ] Verificar respuesta 200 OK
- [ ] Verificar que `total` y `count` son números válidos

### 1.3 Ledger Matched Endpoint (NUEVO)
- [ ] Click en "Con match" en card "Ledger SIN Conductor"
- [ ] En Network tab, verificar llamada:
  - `GET /api/v1/yango/payments/reconciliation/ledger/matched?limit=1000`
- [ ] Verificar respuesta 200 OK
- [ ] Verificar que retorna array de rows (puede estar vacío si no hay matches)

### 1.4 Driver Detail Endpoint (NUEVO)
- [ ] En drilldown de items, click en un `driver_id`
- [ ] En Network tab, verificar llamada:
  - `GET /api/v1/yango/payments/reconciliation/driver/{driver_id}`
- [ ] Verificar respuesta 200 OK
- [ ] Verificar que retorna `claims` array y `summary` object

## PASO 2: Validar Frontend - Banner Warning y Card Identidad

### 2.1 Banner Aparece Correctamente
- [ ] Ir a `/pagos` → Tab Yango
- [ ] Si `Total Paid = 0` Y `ledger_rows_is_paid_true > 0`:
  - [ ] Banner amarillo aparece DESPUÉS de los KPIs
  - [ ] Mensaje dice: "Hay pagos marcados como pagados en ledger pero sin identidad (driver/person). Paid conciliado = 0."
  - [ ] Muestra métricas:
    - Total pagos pagados en ledger: X
    - Pagos sin identidad (driver/person): Y
    - Pagos con identidad enriquecida: Z
    - Pagos conciliados (paid_status='paid'): W
  - [ ] Botones "Ver ledger sin identidad" y "Ver ledger con match" funcionan

### 2.2 Card "Identidad del Ledger" (NUEVO)
- [ ] Card aparece en la fila de KPIs
- [ ] Muestra:
  - Pagos pagados: número correcto
  - Sin identidad: número de registros con ambos NULL
  - Enriquecidos: número de registros con identity_enriched=true
- [ ] Botones "Sin match" y "Con match" funcionan

### 2.2 Banner NO Aparece Cuando No Aplica
- [ ] Si `Total Paid > 0` O `ledger_rows_is_paid_true = 0`:
  - [ ] Banner NO aparece

## PASO 3: Validar Frontend - Modales

### 3.1 Modal "Ledger sin match"
- [ ] Click en "Sin match" en card "Identidad del Ledger"
- [ ] Modal se abre correctamente
- [ ] Título: "Ledger sin Match contra Claims"
- [ ] Muestra total de registros
- [ ] Tabla muestra columnas:
  - Payment Key
  - Pay Date
  - Milestone
  - Driver ID (debe mostrar "NULL" en rojo si es NULL)
  - Person Key
  - Driver Name
  - Match Rule
  - Match Confidence
  - Is Paid (chip verde si es true)
  - Enriquecido (chip azul si identity_enriched=true) (NUEVO)
- [ ] Botón "Cerrar" funciona

### 3.2 Modal "Ledger con match" (NUEVO)
- [ ] Click en "Con match" en card "Identidad del Ledger"
- [ ] Modal se abre correctamente
- [ ] Título: "Ledger con Match contra Claims"
- [ ] Muestra total de registros
- [ ] Tabla muestra mismas columnas que modal "sin match" incluyendo "Enriquecido"
- [ ] Si hay matches, muestra registros con driver_id o person_key

### 3.2 Modal "Ledger con match" (NUEVO)
- [ ] Click en "Con match" en card "Ledger SIN Conductor"
- [ ] Modal se abre correctamente
- [ ] Título: "Ledger con Match contra Claims"
- [ ] Muestra total de registros
- [ ] Tabla muestra mismas columnas que modal "sin match"
- [ ] Si hay matches, muestra registros
- [ ] Si no hay matches, muestra "No hay registros de ledger con match"

### 3.3 Modal "Detalle por Conductor" (NUEVO)
- [ ] En drilldown de items (click "Ver detalle" en una semana)
- [ ] Click en un `driver_id` (debe ser clickeable, azul)
- [ ] Modal se abre correctamente
- [ ] Header muestra:
  - "Detalle por Conductor"
  - Driver ID: {driver_id}
  - Person Key: {person_key} (si existe)
- [ ] Sección "Resumen" muestra:
  - Total Expected
  - Total Paid
  - Pagados (count)
  - Pendientes Activos (count)
  - Pendientes Vencidos (count)
- [ ] Tabla "Claims" muestra:
  - Milestone
  - Expected Amount
  - Lead Date
  - Due Date
  - Paid Status (con chips de color)
  - Match Method (con chips de color: driver_id=azul, person_key=purple)
  - Paid Date
- [ ] Botón "Cerrar" funciona

## PASO 4: Validar SQL - Vista Claims

### 4.1 Vista Enriquecida Se Ejecuta Sin Errores (NUEVO)
- [ ] Abrir pgAdmin
- [ ] Ejecutar: `SELECT COUNT(*) FROM ops.v_yango_payments_ledger_latest_enriched;`
- [ ] Debe retornar un número igual o mayor al ledger original
- [ ] Ejecutar: `SELECT COUNT(*) FILTER (WHERE identity_enriched = true) FROM ops.v_yango_payments_ledger_latest_enriched;`
- [ ] Debe retornar número de registros enriquecidos (puede ser 0 si no hay matches)

### 4.2 Vista Claims Se Ejecuta Sin Errores
- [ ] Abrir pgAdmin
- [ ] Ejecutar: `SELECT COUNT(*) FROM ops.v_yango_payments_claims_cabinet_14d;`
- [ ] Debe retornar un número (puede ser 0)

### 4.3 Columnas Existen
- [ ] Ejecutar:
  ```sql
  SELECT 
    expected_amount,
    due_date,
    paid_status,
    match_method,
    paid_payment_key,
    paid_date,
    is_paid_effective
  FROM ops.v_yango_payments_claims_cabinet_14d
  LIMIT 1;
  ```
- [ ] Debe ejecutarse sin errores
- [ ] Ejecutar:
  ```sql
  SELECT 
    driver_id,
    person_key,
    identity_enriched,
    match_rule,
    match_confidence
  FROM ops.v_yango_payments_ledger_latest_enriched
  LIMIT 1;
  ```
- [ ] Debe ejecutarse sin errores

### 4.3 Match Methods Distribución
- [ ] Ejecutar:
  ```sql
  SELECT 
    match_method,
    COUNT(*) AS count,
    COUNT(*) FILTER (WHERE paid_status = 'paid') AS count_paid
  FROM ops.v_yango_payments_claims_cabinet_14d
  GROUP BY match_method
  ORDER BY match_method;
  ```
- [ ] Debe mostrar: 'driver_id', 'person_key', 'none' (o subset)
- [ ] Si hay matches, `count_paid` debe ser > 0 para algunos métodos

## PASO 5: Validar Funcionalidad End-to-End

### 5.1 Flujo Completo: Banner → Modal sin match
- [ ] Abrir `/pagos` → Tab Yango
- [ ] Si banner aparece, click en "Ver pagos pagados sin conductor"
- [ ] Modal se abre y muestra registros
- [ ] Verificar que los registros son correctos (comparar con query SQL directa)

### 5.2 Flujo Completo: Drilldown → Driver Detail
- [ ] En tabla semanal, click "Ver detalle" en una semana
- [ ] En tabla de items, click en un `driver_id`
- [ ] Modal de detalle se abre
- [ ] Verificar que los claims mostrados corresponden a ese driver_id
- [ ] Verificar que el resumen es correcto (suma de expected, counts por status)

### 5.3 Flujo Completo: Ledger con Match
- [ ] Click en "Con match" en card "Ledger SIN Conductor"
- [ ] Si hay matches, verificar que los registros tienen driver_id o person_key
- [ ] Verificar que los payment_keys coinciden con claims

## PASO 6: Validar Panel Debug

### 6.1 Panel Debug Funciona
- [ ] Click en botón "🐛 Debug" (esquina inferior derecha)
- [ ] Panel se abre
- [ ] Muestra:
  - Mode
  - Filtros Enviados
  - Filtros Recibidos (incluye `_validation`)
  - Paid Status Distribution
  - Ledger Count
  - Validation (Backend) con todas las métricas

### 6.2 Panel Debug Solo en Desarrollo
- [ ] En producción (NODE_ENV !== 'development'), panel NO debe aparecer

## PASO 7: Validar Edge Cases

### 7.1 Sin Datos
- [ ] Si no hay claims: dashboard muestra "No hay datos disponibles"
- [ ] Si no hay ledger: card "Ledger SIN Conductor" muestra 0
- [ ] Si no hay matches: modal "Ledger con match" muestra mensaje vacío

### 7.2 Errores de API
- [ ] Si endpoint falla (simular desconectando backend):
  - Frontend muestra mensaje de error apropiado
  - No crashea la aplicación

### 7.3 Driver ID NULL
- [ ] En tabla de items, si `driver_id` es NULL:
  - Muestra "SIN CONDUCTOR" en rojo
  - NO es clickeable (no abre modal)

## PASO 8: Validación SQL Directa (Opcional)

### 8.1 Comparar Totales
- [ ] Ejecutar en pgAdmin:
  ```sql
  SELECT 
    SUM(expected_amount) AS total_expected,
    SUM(expected_amount) FILTER (WHERE paid_status='paid') AS total_paid,
    COUNT(*) FILTER (WHERE paid_status='pending_expired') AS total_anomalies
  FROM ops.v_yango_payments_claims_cabinet_14d;
  ```
- [ ] Comparar con valores mostrados en dashboard (Total Expected, Total Paid, Total Anomalías)
- [ ] Deben coincidir (con pequeñas diferencias por redondeo)

### 8.2 Comparar Ledger Metrics (usando vista enriquecida)
- [ ] Ejecutar:
  ```sql
  SELECT 
    COUNT(*) AS ledger_total_rows,
    COUNT(*) FILTER (WHERE is_paid = true) AS ledger_rows_is_paid_true,
    COUNT(*) FILTER (WHERE driver_id IS NULL) AS ledger_rows_driver_id_null,
    COUNT(*) FILTER (WHERE person_key IS NULL) AS ledger_rows_person_key_null,
    COUNT(*) FILTER (WHERE driver_id IS NULL AND person_key IS NULL) AS ledger_rows_both_identity_null,
    COUNT(*) FILTER (WHERE identity_enriched = true) AS ledger_rows_identity_enriched
  FROM ops.v_yango_payments_ledger_latest_enriched;
  ```
- [ ] Comparar con valores en `filters._validation` del endpoint summary
- [ ] Deben coincidir

### 8.3 Validar Enriquecimiento (NUEVO)
- [ ] Ejecutar scripts de validación:
  - `backend/sql/ops/validation_ledger_identity.sql`
  - `backend/sql/ops/validation_paid_reconciliation.sql`
- [ ] Verificar que:
  - Vista enriquecida tiene más identidades que la original (o igual si no hay matches)
  - Registros enriquecidos tienen `match_rule = 'driver_name_unique'` y `match_confidence = 'medium'`
  - Si hay registros enriquecidos con `is_paid=true`, entonces deben existir claims con `paid_status='paid'`

## Resultado Esperado

Después de completar todos los pasos:
- ✅ Todos los endpoints responden 200 OK
- ✅ Banner aparece cuando aplica
- ✅ Todos los modales funcionan correctamente
- ✅ Detalle por conductor muestra información correcta
- ✅ SQL se ejecuta sin errores
- ✅ Panel Debug muestra información completa
- ✅ No hay errores en consola del navegador
- ✅ No hay errores en logs del backend

## Notas

- Si algún paso falla, documentar el error específico
- Comparar valores con queries SQL directas para validar precisión
- Verificar que la lógica de matching (driver_id vs person_key) funciona correctamente
- Confirmar que Paid=0 es correcto cuando no hay matches reales

