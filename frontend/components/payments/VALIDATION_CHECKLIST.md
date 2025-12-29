# Checklist de Validación - Pagos Yango Dashboard

Este documento contiene el checklist de validación manual para verificar que todas las funcionalidades del dashboard de pagos Yango funcionan correctamente.

## Contexto

El dashboard muestra:
- **Expected**: Montos esperados desde `ops.v_yango_payments_claims_cabinet_14d`
- **Paid (Real)**: Montos donde `paid_status='paid'`
- **Paid (Estimado)**: Montos donde `paid_status='pending_active'` (cuando mode=assumed)
- **Anomalías**: Items donde `paid_status='pending_expired'` (vencidos)

## 1. Toggle Modo (Real / Estimado)

### Ubicación
En la parte superior del dashboard Yango, antes de los KPIs cards.

### Validación

- [ ] **Default**: Al cargar la página, el modo debe ser "Real" (botón azul activo)
- [ ] **Cambiar a Estimado**: 
  - Click en botón "Pagos Estimados"
  - Debe aparecer badge "Estimado" en los KPIs de Paid y Diff
  - Los valores de "Total Paid" y "Total Diff" deben cambiar
  - `Total Paid` debe ser = `SUM(expected_amount WHERE paid_status='pending_active')`
  - `Total Diff` debe ser = `Expected Total - Paid (Estimado)`
- [ ] **Cambiar a Real**:
  - Click en botón "Pagos Reales"
  - Badge "Estimado" desaparece
  - Los valores vuelven a valores reales
  - `Total Paid` debe ser = `SUM(expected_amount WHERE paid_status='paid')`
  - `Total Diff` debe ser = `Expected Total - Paid (Real)`
- [ ] **Badge "Estimado" visible**: Cuando mode='assumed', el badge amarillo debe aparecer junto a "Total Paid" y "Total Diff"

**Comando SQL de verificación:**
```sql
-- Real
SELECT SUM(expected_amount) AS paid_real FROM ops.v_yango_payments_claims_cabinet_14d WHERE paid_status='paid';

-- Estimado
SELECT SUM(expected_amount) AS paid_assumed FROM ops.v_yango_payments_cabinet_14d WHERE paid_status='pending_active';
```

## 2. Filtros

### 2.1. Filtro por Semana

**Ubicación**: Selector de semana en la parte superior (heredado de la página principal)

- [ ] **Sin filtro**: Muestra todas las semanas
- [ ] **Con filtro**: Al seleccionar una semana específica:
  - La tabla semanal se reduce a solo esa semana
  - Los KPIs totales cambian para reflejar solo esa semana
  - El drilldown al hacer click en "Ver Detalle" muestra solo items de esa semana

### 2.2. Filtro por Milestone

**Ubicación**: En el panel de filtros adicionales del dashboard

- [ ] **Sin filtro (Todos)**: Muestra milestones 1, 5 y 25
- [ ] **Milestone 1**: Solo muestra filas con `milestone_value=1`
- [ ] **Milestone 5**: Solo muestra filas con `milestone_value=5`
- [ ] **Milestone 25**: Solo muestra filas con `milestone_value=25`

**Verificación SQL:**
```sql
SELECT milestone_value, COUNT(*) FROM ops.v_yango_payments_claims_cabinet_14d 
WHERE pay_week_start_monday = '2025-01-06'  -- ajustar fecha
GROUP BY milestone_value;
```

### 2.3. Búsqueda por Driver ID / Person Key

**Ubicación**: Campo de búsqueda en el panel de filtros

- [ ] **Búsqueda por Driver ID**: 
  - Escribir un driver_id existente
  - La tabla debe filtrar para mostrar solo items con ese driver_id
  - Si no hay resultados, mostrar mensaje "No hay items..."
- [ ] **Búsqueda por Person Key**:
  - Escribir un person_key existente
  - Debe filtrar correctamente
- [ ] **Búsqueda por Driver Name** (en drilldown):
  - En el modal de detalle, buscar por nombre de driver
  - Debe filtrar correctamente

### 2.4. Checkbox "Solo SIN CONDUCTOR"

**Ubicación**: En el panel de filtros adicionales

- [ ] **Sin activar**: Muestra todos los items (con y sin driver_id)
- [ ] **Activado**: 
  - Solo muestra items donde `driver_id IS NULL`
  - En la tabla, estos items deben mostrar "SIN CONDUCTOR" en rojo
  - El conteo debe coincidir con la query SQL

**Verificación SQL:**
```sql
SELECT COUNT(*) FROM ops.v_yango_payments_claims_cabinet_14d 
WHERE driver_id IS NULL;
```

## 3. Tabs en Drilldown (Modal de Detalle)

### Ubicación
Al hacer click en "Ver Detalle" en una fila de la tabla semanal.

### Tabs disponibles

- [ ] **Tab "Vencidos" (default)**:
  - Al abrir el modal, este tab debe estar activo por defecto
  - Solo muestra items con `paid_status='pending_expired'`
  - El conteo en el tab debe coincidir con `summary.pending_expired`

- [ ] **Tab "Pendientes Activos"**:
  - Click en el tab
  - Solo muestra items con `paid_status='pending_active'`
  - El conteo debe coincidir con `summary.pending_active`

- [ ] **Tab "Pagados"**:
  - Click en el tab
  - Solo muestra items con `paid_status='paid'`
  - El conteo debe coincidir con `summary.paid`

- [ ] **Tab "Todos"**:
  - Click en el tab
  - Muestra todos los items sin filtrar por status
  - El conteo debe coincidir con `summary.total`

**Verificación SQL:**
```sql
SELECT paid_status, COUNT(*) 
FROM ops.v_yango_payments_claims_cabinet_14d 
WHERE pay_week_start_monday = '2025-01-06'  -- ajustar fecha
GROUP BY paid_status;
```

## 4. KPIs Cards

### Ubicación
En la parte superior del dashboard, después del toggle de modo.

### Validación

- [ ] **Total Expected**:
  - Debe ser > 0
  - Debe coincidir con `SUM(expected_amount)` de todos los items
  - Se actualiza cuando se aplican filtros de semana/milestone

- [ ] **Total Paid**:
  - En modo Real: `SUM(expected_amount WHERE paid_status='paid')`
  - En modo Estimado: `SUM(expected_amount WHERE paid_status='pending_active')`
  - Debe cambiar cuando se cambia el modo

- [ ] **Total Diff**:
  - Debe ser = `Total Expected - Total Paid`
  - Debe cambiar según el modo (real vs assumed)
  - Color: rojo si diff >= 0, verde si diff < 0

- [ ] **Total Anomalías**:
  - Siempre = `COUNT(*) WHERE paid_status='pending_expired'`
  - NO cambia según el modo (siempre es vencidos)
  - Debe ser >= 0

**Verificación SQL:**
```sql
SELECT 
  SUM(expected_amount) AS expected_total,
  SUM(expected_amount) FILTER (WHERE paid_status='paid') AS paid_total_real,
  SUM(expected_amount) FILTER (WHERE paid_status='pending_active') AS paid_total_assumed,
  COUNT(*) FILTER (WHERE paid_status='pending_expired') AS anomalies_total
FROM ops.v_yango_payments_claims_cabinet_14d;
```

## 5. Tabla Semanal

### Ubicación
En el dashboard principal, después de los KPIs.

### Validación

- [ ] **Columnas visibles**:
  - Semana, Expected, Paid, Diff, Count Expected, Count Paid
  - Pending Active, Pending Expired, Anomalías, Anomaly %, Acción

- [ ] **Datos correctos**:
  - Cada fila representa una semana (`pay_week_start_monday`)
  - Los montos deben sumar correctamente
  - Anomalías debe ser = `count_pending_expired` del summary

- [ ] **Click en "Ver Detalle"**:
  - Abre el modal con items de esa semana
  - El tab default debe ser "Vencidos"

- [ ] **Orden**:
  - Las semanas deben estar ordenadas descendente (más reciente primero)

## 6. Tabla Items (Modal Drilldown)

### Ubicación
En el modal que se abre al hacer click en "Ver Detalle".

### Validación de Columnas

- [ ] **Driver ID**:
  - Muestra el `driver_id` o "SIN CONDUCTOR" (en rojo) si es NULL

- [ ] **Person Key**: 
  - Muestra el `person_key`

- [ ] **Milestone**: 
  - Muestra el `milestone_value` (1, 5, 25)

- [ ] **Expected Amount**: 
  - Formato moneda PEN
  - Muestra el `expected_amount`

- [ ] **Currency**: 
  - Muestra la moneda (generalmente PEN)

- [ ] **Lead Date**: 
  - Fecha formateada (DD/MM/YYYY)

- [ ] **Due Date**: 
  - Fecha formateada (lead_date + 14 días)

- [ ] **Window Status**: 
  - Chip coloreado: azul para "active", rojo para "expired"

- [ ] **Paid Status**: 
  - Chip coloreado:
    - Verde: "Pagado" (paid)
    - Amarillo: "Pendiente Activo" (pending_active)
    - Rojo: "Vencido" (pending_expired)

- [ ] **Paid Payment Key**: 
  - Muestra `paid_payment_key` si existe

- [ ] **Paid Date**: 
  - Fecha formateada si existe

- [ ] **Is Paid Effective**: 
  - Chip verde "Sí" o gris "No"

- [ ] **Match Method**: 
  - Muestra `match_method` (generalmente "driver_id")

- [ ] **Match Rule**: 
  - Muestra `paid_match_rule`

- [ ] **Match Confidence**: 
  - Muestra `paid_match_confidence`

### Validación de Funcionalidad

- [ ] **Paginación**: 
  - Si hay más de 50 items, muestra controles de paginación
  - Botones "Anterior" y "Siguiente" funcionan correctamente

- [ ] **Filtros aplicados**: 
  - Los filtros (búsqueda, milestone, sin conductor) se aplican correctamente
  - El conteo "Mostrando X de Y items" es correcto

## 7. Export CSV

### Ubicación
Botón "📥 Exportar CSV" en el modal de drilldown.

### Validación

- [ ] **Click en botón**: 
  - Descarga un archivo CSV
  - Nombre: `yango_reconciliation_YYYY-MM-DD_YYYY-MM-DD.csv`

- [ ] **Campos incluidos**: 
  - Semana, Driver ID, Person Key, Milestone, Expected Amount, Currency
  - Lead Date, Due Date, Window Status, Paid Status
  - Paid Payment Key, Paid Date, Is Paid Effective
  - Match Method, Match Rule, Match Confidence

- [ ] **Datos correctos**: 
  - Solo exporta los items filtrados visibles en la tabla
  - Los valores coinciden con lo mostrado en la UI

## 8. Panel Debug

### Ubicación
Botón flotante "🐛 Debug" en la esquina inferior derecha (solo en desarrollo).

### Validación

- [ ] **Visibilidad**: 
  - Solo aparece si `NODE_ENV === 'development'`
  - No aparece en producción

- [ ] **Click para abrir**: 
  - Abre panel flotante con información de debug

- [ ] **Información mostrada**:
  - Mode actual (real/assumed)
  - Filtros enviados al backend
  - Filtros recibidos del backend (includes mode)
  - Counts: total, loaded, filtered

- [ ] **Cerrar panel**: 
  - Botón X cierra el panel
  - Vuelve a mostrar solo el botón flotante

## 9. Empty States

### Validación

- [ ] **Sin datos**: 
  - Si no hay rows en summary, mostrar "No hay datos disponibles"
  - Si no hay items en drilldown, mostrar "No hay items para mostrar con los filtros aplicados"

- [ ] **Con filtros que no devuelven resultados**: 
  - Debe mostrar mensaje claro
  - Los filtros deben poder resetearse

## 10. Integración con Backend

### Endpoints

- [ ] **GET /api/v1/yango/payments/reconciliation/summary**:
  - Acepta query params: `week_start`, `milestone_value`, `mode` (real/assumed), `limit`
  - Retorna `amount_expected_sum`, `amount_paid_sum`, `amount_paid_assumed`, `amount_diff`, `amount_diff_assumed`
  - Retorna `anomalies_total`, `count_paid`, `count_pending_active`, `count_pending_expired`

- [ ] **GET /api/v1/yango/payments/reconciliation/items**:
  - Default status = `pending_expired` si no se especifica
  - Acepta query params: `week_start`, `status` (paid/pending_active/pending_expired), `milestone_value`, `driver_id`, `person_key`, `limit`, `offset`
  - Retorna items con `paid_status`, `due_date`, `window_status`, `match_method`, etc.

## Notas Finales

- Todas las validaciones deben ejecutarse tanto en modo "Real" como en modo "Estimado"
- Los valores mostrados deben coincidir con las queries SQL de verificación
- No debe haber errores en la consola del navegador
- El rendimiento debe ser aceptable incluso con grandes volúmenes de datos (paginación funcionando)

## Cómo Reportar Problemas

Si encuentras un problema durante la validación:

1. Anotar el paso exacto donde ocurre
2. Capturar screenshot si aplica
3. Revisar la consola del navegador (F12) para errores
4. Verificar los valores en la base de datos con las queries SQL proporcionadas
5. Verificar el panel de debug para ver qué se está enviando/recibiendo



