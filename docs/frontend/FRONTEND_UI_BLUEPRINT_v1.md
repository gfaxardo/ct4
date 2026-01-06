# Frontend UI Blueprint v1

**Fecha de generación:** 2025-01-27  
**Basado en:** `docs/contracts/FRONTEND_BACKEND_CONTRACT_v1.md`  
**Versión API:** v1

---

## Índice

- [A) Navegación (Sidebar)](#a-navegación-sidebar)
- [B) Páginas NO PENDING](#b-páginas-no-pending)
  - [Dashboard](#1-dashboard)
  - [Personas](#2-persons)
  - [Detalle de Persona](#3-personsperson_key)
  - [Unmatched](#4-unmatched)
  - [Liquidaciones Scouts](#5-liquidaciones)
  - [Pagos - Elegibilidad](#6-pagos)
  - [Yango - Reconciliación](#7-pagosyango-cabinet)
  - [Yango - Cobranza](#8-pagoscobranza-yango)
- [C) Páginas PENDING](#c-páginas-pending)
  - [Runs (Listado)](#1-runs-listado-pending-parcial)
  - [Claims](#2-pagosclaims-pending)
  - [Ops Alerts](#3-opsalerts-pending)
  - [Data Health](#4-opsdata-health-pending)

---

## A) Navegación (Sidebar)

```
📊 Dashboard
👥 Identidad
   ├── Personas
   ├── Unmatched
   └── Runs (PENDING parcial - falta listado)
💰 Pagos
   ├── Elegibilidad
   └── Yango
       ├── Reconciliación
       └── Cobranza Yango
   └── (PENDING) Claims
💵 Liquidaciones
   └── Scouts
⚙️ Ops
   ├── (PENDING) Alerts
   └── (PENDING) Data Health
```

---

## B) Páginas NO PENDING

### 1. Dashboard

**Ruta:** `/dashboard`

#### Objetivo
Responde: **"¿Cuál es el estado general del sistema de identidad?"**

Muestra métricas agregadas del sistema, última corrida ejecutada, breakdowns de matching y tendencias semanales.

#### Endpoints Consumidos

1. **`GET /api/v1/identity/stats`**
   - Params: Ninguno
   - Uso: Estadísticas generales (total_persons, total_unmatched, conversion_rate)

2. **`GET /api/v1/identity/metrics/global`**
   - Params:
     - `mode` (str): 'summary', 'weekly', o 'breakdowns
     - `source_table` (Optional[str])
     - `event_date_from` (Optional[date])
     - `event_date_to` (Optional[date])
   - Uso: Métricas globales con breakdowns o datos semanales

3. **`GET /api/v1/identity/runs/{run_id}/report`**
   - Params:
     - `run_id` (int, path): ID de la última corrida completada
     - `group_by` (str, default="none"): 'none' o 'week'
     - `include_weekly` (bool, default=True)
   - Uso: Reporte detallado de la última corrida

#### Componentes UI

- **StatCards** (3 cards):
  - `total_persons` (Personas Identificadas)
  - `total_unmatched` (Sin Resolver)
  - `conversion_rate` (Tasa de Match) - calculado: `(total_persons / (total_persons + total_unmatched)) * 100`
  
- **ModeSelector**: Toggle entre 'summary' y 'weekly'

- **FiltersBar** (cuando mode='weekly'):
  - Selector de `source_table` (dropdown)
  - Selector de `event_week` (dropdown con `available_event_weeks`)

- **BreakdownCharts** (cuando mode='summary' o 'breakdowns'):
  - Gráfico de barras: `matched_breakdown.by_match_rule`
  - Gráfico de barras: `unmatched_breakdown.by_reason_code` (Top 5)

- **WeeklyMetricsView** (cuando mode='weekly'):
  - Tabla: `weekly` con columnas: week_label, source_table, matched, unmatched, match_rate
  - Gráfico de líneas: `weekly_trend` (delta_match_rate por semana)

- **LastRunCard**:
  - Muestra: `run.status`, `run.started_at`, `run.completed_at`
  - Link a `/runs/{run_id}`

- **AlertsSection** (PENDING - requiere endpoint):
  - Lista de alertas activas (cuando exista `GET /api/v1/ops/alerts`)

#### Columnas de Tabla
N/A (dashboard agregado, no tabla de datos)

#### Filtros
- `mode`: 'summary' | 'weekly' | 'breakdowns' (selector)
- `source_table`: Opcional (dropdown)
- `event_week`: Opcional (dropdown, solo si mode='weekly')
- `event_date_from` / `event_date_to`: Opcional (date picker, solo si mode='weekly')

#### Drilldown
- Click en "Última Corrida" → `/runs/{run_id}` → `GET /api/v1/identity/runs/{run_id}/report`

#### Estados Vacíos/Errores

- **Loading:** Spinner con texto "Cargando..."
- **Error 500 (stats):** Mensaje: "Error al cargar estadísticas"
- **Error 500 (metrics):** Mensaje: "Error al cargar métricas"
- **Error 400 (mode inválido):** Mensaje: "Modo inválido"
- **Error 400 (fechas inválidas):** Mensaje: "Rango de fechas inválido"
- **Empty (sin corridas):** Mensaje: "No hay corridas ejecutadas aún"
- **Empty (sin métricas):** Mensaje: "No hay métricas disponibles"

---

### 2. Persons

**Ruta:** `/persons`

#### Objetivo
Responde: **"¿Qué personas están en el registro canónico?"**

Lista todas las personas identificadas con capacidad de búsqueda y filtrado.

#### Endpoints Consumidos

1. **`GET /api/v1/identity/persons`**
   - Params:
     - `phone` (Optional[str])
     - `document` (Optional[str])
     - `license` (Optional[str])
     - `name` (Optional[str])
     - `confidence_level` (Optional[str]): 'HIGH', 'MEDIUM', 'LOW'
     - `skip` (int, default=0)
     - `limit` (int, default=100, max=1000)

#### Componentes UI

- **FiltersBar**:
  - Input: `phone` (text)
  - Input: `document` (text)
  - Input: `license` (text)
  - Input: `name` (text)
  - Select: `confidence_level` (dropdown: HIGH, MEDIUM, LOW, Todos)

- **DataTable**:
  - Columnas según response schema (ver abajo)
  - Paginación: `skip` / `limit`
  - Ordenamiento: Por `created_at DESC` (implícito)

- **Pagination**: Control de `skip` y `limit`

#### Columnas Exactas (del Contract)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `person_key` | UUID | Clave única (link a detalle) |
| `primary_full_name` | string \| null | Nombre completo |
| `primary_phone` | string \| null | Teléfono normalizado |
| `primary_document` | string \| null | Documento |
| `primary_license` | string \| null | Licencia normalizada |
| `confidence_level` | string | 'HIGH', 'MEDIUM', 'LOW' |
| `created_at` | datetime | Fecha de creación |
| `updated_at` | datetime | Fecha de actualización |

**Nota:** `flags` (JSONB) no se muestra en tabla, solo en detalle.

#### Filtros (Query Params)

- `phone`: Input de texto
- `document`: Input de texto
- `license`: Input de texto
- `name`: Input de texto
- `confidence_level`: Dropdown (HIGH, MEDIUM, LOW, null=all)
- `skip`: Controlado por paginación
- `limit`: Selector (50, 100, 200, 500, 1000)

#### Drilldown

- Click en `person_key` → `/persons/{person_key}` → `GET /api/v1/identity/persons/{person_key}`

#### Estados Vacíos/Errores

- **Loading:** Spinner con texto "Cargando personas..."
- **Empty:** Mensaje: "No se encontraron personas que coincidan con los filtros"
- **Error 400 (confidence_level inválido):** Mensaje: "Nivel de confianza inválido"
- **Error 500:** Mensaje: "Error al cargar personas"

---

### 3. Persons/[person_key]

**Ruta:** `/persons/[person_key]`

#### Objetivo
Responde: **"¿Qué información tiene esta persona y a qué fuentes está vinculada?"**

Muestra detalle completo de una persona, todos sus links y si tiene conversión a driver.

#### Endpoints Consumidos

1. **`GET /api/v1/identity/persons/{person_key}`**
   - Params:
     - `person_key` (UUID, path): Clave única de la persona

#### Componentes UI

- **PersonCard**:
  - Muestra: `person.person_key`, `person.primary_full_name`, `person.primary_phone`, `person.primary_document`, `person.primary_license`, `person.confidence_level`, `person.created_at`, `person.updated_at`
  - Badge: `confidence_level` con color (HIGH=verde, MEDIUM=amarillo, LOW=rojo)

- **DriverConversionBadge**:
  - Muestra: `has_driver_conversion` (true/false)
  - Si true: "✓ Tiene conversión a driver"
  - Si false: "✗ Sin conversión a driver"

- **LinksTable**:
  - Tabla con todos los `links`
  - Columnas según response schema (ver abajo)

- **DriverLinksSection** (opcional):
  - Subsección destacada con `driver_links` (subset de links donde source_table='drivers')

#### Columnas Exactas (LinksTable - del Contract)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | int | ID del link |
| `source_table` | string | 'drivers', 'module_ct_cabinet_leads', etc. |
| `source_pk` | string | PK de la tabla fuente |
| `match_rule` | string | 'PHONE_EXACT', 'LICENSE_EXACT', etc. |
| `match_score` | int | 0-100 |
| `confidence_level` | string | 'HIGH', 'MEDIUM', 'LOW' |
| `snapshot_date` | datetime | Fecha del snapshot |
| `linked_at` | datetime | Fecha de creación del link |
| `run_id` | int \| null | ID de la corrida |

**Nota:** `evidence` (JSONB) no se muestra en tabla, solo expandible en detalle.

#### Filtros
N/A (página de detalle)

#### Drilldown
N/A (página de detalle)

#### Estados Vacíos/Errores

- **Loading:** Spinner con texto "Cargando detalle de persona..."
- **404:** Mensaje: "Persona no encontrada" + Botón "Volver a Personas"
- **Error 500:** Mensaje: "Error al cargar detalle de persona"
- **Empty (sin links):** Mensaje: "Esta persona no tiene links asociados"

---

### 4. Unmatched

**Ruta:** `/unmatched`

#### Objetivo
Responde: **"¿Qué registros no pudieron ser matcheados?"**

Lista registros que no pudieron ser vinculados a una persona, con capacidad de resolución manual.

#### Endpoints Consumidos

1. **`GET /api/v1/identity/unmatched`**
   - Params:
     - `reason_code` (Optional[str])
     - `status` (Optional[str]): 'OPEN' o 'RESOLVED'
     - `skip` (int, default=0)
     - `limit` (int, default=100, max=1000)

2. **`POST /api/v1/identity/unmatched/{id}/resolve`**
   - Params:
     - `id` (int, path): ID del registro unmatched
   - Body:
     ```typescript
     {
       person_key: UUID
     }
     ```

#### Componentes UI

- **FiltersBar**:
  - Select: `reason_code` (dropdown con valores únicos: MISSING_KEYS, AMBIGUOUS, etc.)
  - Select: `status` (dropdown: OPEN, RESOLVED, Todos)

- **DataTable**:
  - Columnas según response schema (ver abajo)
  - Acción: Botón "Resolver" por fila

- **ResolveModal**:
  - Input: `person_key` (UUID)
  - Botón: "Resolver"
  - Valida UUID antes de enviar

- **Pagination**: Control de `skip` y `limit`

#### Columnas Exactas (del Contract)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | int | ID del registro |
| `source_table` | string | Tabla fuente |
| `source_pk` | string | PK de la tabla fuente |
| `reason_code` | string | 'MISSING_KEYS', 'AMBIGUOUS', etc. |
| `status` | string | 'OPEN' o 'RESOLVED' |
| `snapshot_date` | datetime | Fecha del snapshot |
| `created_at` | datetime | Fecha de creación |
| `resolved_at` | datetime \| null | Fecha de resolución |
| `details` | object \| null | JSONB (expandible) |
| `candidates_preview` | object \| null | JSONB (expandible) |
| `run_id` | int \| null | ID de la corrida |

#### Filtros (Query Params)

- `reason_code`: Dropdown (valores únicos del dataset)
- `status`: Dropdown (OPEN, RESOLVED, null=all)
- `skip`: Controlado por paginación
- `limit`: Selector (50, 100, 200, 500, 1000)

#### Drilldown
N/A (acción: resolver unmatched)

#### Estados Vacíos/Errores

- **Loading:** Spinner con texto "Cargando unmatched..."
- **Empty:** Mensaje: "No hay registros unmatched que coincidan con los filtros"
- **Error 400 (status inválido):** Mensaje: "Estado inválido"
- **Error 500 (GET):** Mensaje: "Error al cargar unmatched"
- **Error 404 (POST - unmatched no encontrado):** Mensaje: "Registro no encontrado"
- **Error 404 (POST - persona no encontrada):** Mensaje: "Persona no encontrada"
- **Error 500 (POST):** Mensaje: "Error al resolver unmatched"
- **Success (POST):** Toast: "Registro resuelto exitosamente. Link ID: {link_id}"

---

### 5. Liquidaciones

**Ruta:** `/liquidaciones`

#### Objetivo
Responde: **"¿Cuánto se debe pagar a scouts y qué items están abiertos?"**

Muestra resumen de liquidación scouts con totales, desglose por semana, top scouts e items abiertos.

#### Endpoints Consumidos

1. **`GET /api/v1/dashboard/scout/summary`**
   - Params:
     - `week_start` (Optional[date])
     - `week_end` (Optional[date])
     - `scout_id` (Optional[int])
     - `lead_origin` (Optional[str]): 'cabinet' o 'migration'

2. **`GET /api/v1/dashboard/scout/open_items`**
   - Params:
     - `week_start_monday` (Optional[date])
     - `scout_id` (Optional[int])
     - `confidence` (str, default="policy"): 'policy', 'high', 'medium', 'unknown'
     - `limit` (int, default=100, max=1000)
     - `offset` (int, default=0)

#### Componentes UI

- **StatCards** (6 cards):
  - `totals.payable_amount` (Monto Pagable)
  - `totals.payable_items` (Items Pagables)
  - `totals.payable_drivers` (Drivers Únicos)
  - `totals.payable_scouts` (Scouts Únicos)
  - `totals.blocked_amount` (Monto Bloqueado)
  - `totals.blocked_items` (Items Bloqueados)

- **FiltersBar**:
  - DatePicker: `week_start` / `week_end`
  - Input: `scout_id` (number)
  - Select: `lead_origin` (dropdown: cabinet, migration, Todos)
  - Select: `confidence` (dropdown: policy, high, medium, unknown)

- **WeeklyChart**:
  - Gráfico de barras: `by_week` con `payable_amount` y `blocked_amount` por semana
  - Eje X: `iso_year_week`
  - Eje Y: Monto (Decimal)

- **TopScoutsTable**:
  - Tabla: `top_scouts` (máx 10)
  - Columnas: acquisition_scout_id, acquisition_scout_name, amount, items, drivers

- **OpenItemsTable**:
  - Tabla: `items` del endpoint `/scout/open_items`
  - Columnas según response schema (ver abajo)
  - Paginación: `offset` / `limit`

#### Columnas Exactas (OpenItemsTable - del Contract)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `payment_item_key` | string | Clave única del item |
| `person_key` | string | UUID de la persona |
| `lead_origin` | string \| null | 'cabinet' o 'migration' |
| `scout_id` | int \| null | ID del scout original |
| `acquisition_scout_id` | int \| null | ID del scout atribuido |
| `acquisition_scout_name` | string \| null | Nombre del scout |
| `attribution_confidence` | string \| null | 'policy', 'high', 'medium', 'unknown' |
| `attribution_rule` | string \| null | Regla de atribución |
| `milestone_type` | string \| null | Tipo de milestone |
| `milestone_value` | int \| null | 1, 5, 25 |
| `payable_date` | date \| null | Fecha en que se vuelve pagable |
| `achieved_date` | date \| null | Fecha de logro |
| `amount` | Decimal | Monto del pago |
| `currency` | string \| null | Moneda (ej: "PEN") |
| `driver_id` | string \| null | ID del driver |

#### Filtros (Query Params)

**Summary:**
- `week_start`: DatePicker
- `week_end`: DatePicker
- `scout_id`: Input number
- `lead_origin`: Dropdown (cabinet, migration, null=all)

**Open Items:**
- `week_start_monday`: DatePicker
- `scout_id`: Input number
- `confidence`: Dropdown (policy, high, medium, unknown)
- `limit`: Selector (50, 100, 200, 500, 1000)
- `offset`: Controlado por paginación

#### Drilldown
N/A (o futuro: detalle de scout si se agrega endpoint)

#### Estados Vacíos/Errores

- **Loading:** Spinner con texto "Cargando liquidaciones..."
- **Empty (summary):** Mensaje: "No hay datos de liquidación para los filtros seleccionados"
- **Empty (items):** Mensaje: "No hay items abiertos que coincidan con los filtros"
- **Error 400 (fechas inválidas):** Mensaje: "Parámetros inválidos" + detalles
- **Error 400 (lead_origin inválido):** Mensaje: "Origen del lead inválido"
- **Error 400 (confidence inválido):** Mensaje: "Nivel de confianza inválido"
- **Error 500:** Mensaje: "Error al cargar resumen de scouts. Intente más tarde." o "Error al cargar items. Intente más tarde."

---

### 6. Pagos

**Ruta:** `/pagos`

#### Objetivo
Responde: **"¿Qué pagos son elegibles y cumplen condiciones?"**

Lista pagos que cumplen condiciones de elegibilidad con filtros y ordenamiento.

#### Endpoints Consumidos

1. **`GET /api/v1/payments/eligibility`**
   - Params:
     - `origin_tag` (Optional[str]): 'cabinet' o 'fleet_migration'
     - `rule_scope` (Optional[str]): 'scout' o 'partner'
     - `is_payable` (Optional[bool])
     - `scout_id` (Optional[int])
     - `driver_id` (Optional[str])
     - `payable_from` (Optional[date])
     - `payable_to` (Optional[date])
     - `limit` (int, default=200, max=1000)
     - `offset` (int, default=0)
     - `order_by` (OrderByField, default=payable_date): 'payable_date', 'lead_date', 'amount'
     - `order_dir` (OrderDirection, default=asc): 'asc' o 'desc'

#### Componentes UI

- **FiltersBar**:
  - Select: `origin_tag` (dropdown: cabinet, fleet_migration, Todos)
  - Select: `rule_scope` (dropdown: scout, partner, Todos)
  - Checkbox: `is_payable` (true/false/null)
  - Input: `scout_id` (number)
  - Input: `driver_id` (text)
  - DatePicker: `payable_from` / `payable_to`

- **SortControls**:
  - Select: `order_by` (dropdown: payable_date, lead_date, amount)
  - Toggle: `order_dir` (asc/desc)

- **DataTable**:
  - Columnas según response schema (ver abajo)
  - Paginación: `offset` / `limit`

- **Pagination**: Control de `offset` y `limit`

#### Columnas Exactas (del Contract)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `person_key` | string \| null | UUID de la persona |
| `origin_tag` | string \| null | 'cabinet' o 'fleet_migration' |
| `scout_id` | int \| null | ID del scout |
| `driver_id` | string \| null | ID del driver |
| `lead_date` | date \| null | Fecha del lead |
| `rule_id` | int \| null | ID de la regla |
| `rule_scope` | string \| null | 'scout' o 'partner' |
| `milestone_trips` | int \| null | Viajes requeridos |
| `window_days` | int \| null | Días de ventana |
| `currency` | string \| null | Moneda |
| `amount` | Decimal \| null | Monto del pago |
| `rule_valid_from` | date \| null | Fecha inicio validez regla |
| `rule_valid_to` | date \| null | Fecha fin validez regla |
| `milestone_achieved` | bool \| null | Si se alcanzó milestone |
| `achieved_date` | date \| null | Fecha de logro |
| `achieved_trips_in_window` | int \| null | Viajes en ventana |
| `is_payable` | bool \| null | Si cumple condiciones |
| `payable_date` | date \| null | Fecha en que se vuelve pagable |
| `payment_scheme` | string \| null | Esquema de pago |

#### Filtros (Query Params)

- `origin_tag`: Dropdown (cabinet, fleet_migration, null=all)
- `rule_scope`: Dropdown (scout, partner, null=all)
- `is_payable`: Checkbox (true/false/null=all)
- `scout_id`: Input number
- `driver_id`: Input text
- `payable_from`: DatePicker
- `payable_to`: DatePicker
- `order_by`: Dropdown (payable_date, lead_date, amount)
- `order_dir`: Toggle (asc/desc)
- `limit`: Selector (50, 100, 200, 500, 1000)
- `offset`: Controlado por paginación

#### Drilldown
N/A

#### Estados Vacíos/Errores

- **Loading:** Spinner con texto "Cargando elegibilidad de pagos..."
- **Empty:** Mensaje: "No hay pagos elegibles que coincidan con los filtros"
- **Error 400 (origin_tag inválido):** Mensaje: "Origen inválido"
- **Error 400 (rule_scope inválido):** Mensaje: "Scope de regla inválido"
- **Error 400 (order_by inválido):** Mensaje: "Campo de ordenamiento inválido"
- **Error 500:** Mensaje: "Error al cargar elegibilidad de pagos"

---

### 7. Pagos/Yango-Cabinet

**Ruta:** `/pagos/yango-cabinet`

#### Objetivo
Responde: **"¿Cuál es el estado de reconciliación de pagos Yango?"**

Muestra resumen agregado de reconciliación, items detallados, y ledger (matched/unmatched).

#### Endpoints Consumidos

1. **`GET /api/v1/yango/payments/reconciliation/summary`**
   - Params:
     - `week_start` (Optional[date])
     - `milestone_value` (Optional[int]): 1, 5, 25
     - `mode` (Literal['real', 'assumed'], default='real')
     - `limit` (int, default=1000, max=10000)

2. **`GET /api/v1/yango/payments/reconciliation/items`**
   - Params:
     - `week_start` (Optional[date])
     - `milestone_value` (Optional[int])
     - `driver_id` (Optional[str])
     - `paid_status` (Optional[str])
     - `limit` (int, default=1000, max=10000)
     - `offset` (int, default=0)

3. **`GET /api/v1/yango/payments/reconciliation/driver/{driver_id}`**
   - Params:
     - `driver_id` (str, path): ID del conductor
   - Uso: Drilldown desde items

4. **`GET /api/v1/yango/payments/reconciliation/ledger/unmatched`** (opcional)
   - Params:
     - `is_paid` (Optional[bool])
     - `driver_id` (Optional[str])
     - `identity_status` (Optional[str])
     - `limit` (int, default=1000, max=10000)
     - `offset` (int, default=0)

5. **`GET /api/v1/yango/payments/reconciliation/ledger/matched`** (opcional)
   - Params:
     - `is_paid` (Optional[bool])
     - `driver_id` (Optional[str])
     - `limit` (int, default=1000, max=10000)
     - `offset` (int, default=0)

#### Componentes UI

- **Tabs**:
  - Tab 1: "Resumen" (Summary)
  - Tab 2: "Items" (Items)
  - Tab 3: "Ledger Sin Match" (Unmatched)
  - Tab 4: "Ledger Con Match" (Matched)

- **FiltersBar** (compartido):
  - DatePicker: `week_start`
  - Select: `milestone_value` (dropdown: 1, 5, 25, Todos)
  - Toggle: `mode` (real/assumed) - solo para Summary
  - Input: `driver_id` (text) - solo para Items/Ledger
  - Select: `paid_status` (dropdown) - solo para Items

- **SummaryTable** (Tab 1):
  - Tabla: `rows` del endpoint `/reconciliation/summary`
  - Columnas según response schema (ver abajo)

- **ItemsTable** (Tab 2):
  - Tabla: `rows` del endpoint `/reconciliation/items`
  - Columnas según response schema (ver abajo)
  - Paginación: `offset` / `limit`

- **LedgerUnmatchedTable** (Tab 3):
  - Tabla: `rows` del endpoint `/ledger/unmatched`
  - Columnas según response schema del contract

- **LedgerMatchedTable** (Tab 4):
  - Tabla: `rows` del endpoint `/ledger/matched`
  - Columnas según response schema del contract

#### Columnas Exactas (SummaryTable - del Contract)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `pay_week_start_monday` | date | Lunes de la semana |
| `milestone_value` | int | 1, 5, 25 |
| `amount_expected_sum` | Decimal | Monto esperado total |
| `amount_paid_confirmed_sum` | Decimal | Monto pagado confirmado |
| `amount_paid_enriched_sum` | Decimal | Monto pagado enriquecido |
| `amount_paid_total_visible` | Decimal | Total visible (confirmed + enriched) |
| `amount_pending_active_sum` | Decimal | Monto pendiente activo |
| `amount_pending_expired_sum` | Decimal | Monto pendiente expirado |
| `amount_diff` | Decimal | Diferencia (expected - paid_visible) |
| `amount_diff_assumed` | Decimal | Diferencia asumida |
| `anomalies_total` | int | Cantidad de anomalías |
| `count_expected` | int | Cantidad esperada |
| `count_paid_confirmed` | int | Cantidad pagada confirmada |
| `count_paid_enriched` | int | Cantidad pagada enriquecida |
| `count_paid` | int | Total pagado |
| `count_pending_active` | int | Cantidad pendiente activa |
| `count_pending_expired` | int | Cantidad pendiente expirada |
| `count_drivers` | int | Drivers únicos |

#### Columnas Exactas (ItemsTable - del Contract)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `driver_id` | string \| null | ID del conductor (link a drilldown) |
| `person_key` | string \| null | UUID de la persona |
| `lead_date` | date \| null | Fecha del lead |
| `pay_week_start_monday` | date \| null | Lunes de la semana |
| `milestone_value` | int \| null | 1, 5, 25 |
| `expected_amount` | Decimal \| null | Monto esperado |
| `currency` | string \| null | Moneda |
| `due_date` | date \| null | lead_date + 14 days |
| `window_status` | string \| null | 'active' o 'expired' |
| `paid_payment_key` | string \| null | Clave de pago |
| `paid_payment_key_confirmed` | string \| null | Clave confirmada |
| `paid_payment_key_enriched` | string \| null | Clave enriquecida |
| `paid_date` | date \| null | Fecha de pago |
| `paid_date_confirmed` | date \| null | Fecha confirmada |
| `paid_date_enriched` | date \| null | Fecha enriquecida |
| `is_paid_effective` | bool \| null | Si está efectivamente pagado |
| `match_method` | string \| null | Método de match |
| `paid_status` | string \| null | 'paid_confirmed', 'paid_enriched', 'pending_active', 'pending_expired' |
| `identity_status` | string \| null | Estado de identidad |
| `match_rule` | string \| null | Regla de match |
| `match_confidence` | string \| null | Confianza de match |

#### Filtros (Query Params)

**Summary:**
- `week_start`: DatePicker
- `milestone_value`: Dropdown (1, 5, 25, null=all)
- `mode`: Toggle (real/assumed)
- `limit`: Selector (100, 500, 1000, 5000, 10000)

**Items:**
- `week_start`: DatePicker
- `milestone_value`: Dropdown (1, 5, 25, null=all)
- `driver_id`: Input text
- `paid_status`: Dropdown (paid_confirmed, paid_enriched, pending_active, pending_expired, null=all)
- `limit`: Selector (100, 500, 1000, 5000, 10000)
- `offset`: Controlado por paginación

**Ledger Unmatched/Matched:**
- `is_paid`: Checkbox (true/false/null=all)
- `driver_id`: Input text
- `identity_status`: Dropdown (solo para Unmatched)
- `limit`: Selector (100, 500, 1000, 5000, 10000)
- `offset`: Controlado por paginación

#### Drilldown

- Click en `driver_id` (ItemsTable) → `/pagos/yango-cabinet/driver/{driver_id}` → `GET /api/v1/yango/payments/reconciliation/driver/{driver_id}`

**Página de Drilldown:** Detalle de Conductor
- **StatCards**: `summary.total_expected`, `summary.total_paid`, `summary.count_paid`, `summary.count_pending_active`, `summary.count_pending_expired`
- **ClaimsTable**: `claims` con columnas: milestone_value, expected_amount, due_date, paid_status, is_paid_effective, match_rule

#### Estados Vacíos/Errores

- **Loading:** Spinner con texto "Cargando reconciliación..."
- **Empty (summary):** Mensaje: "No hay datos de reconciliación para los filtros seleccionados"
- **Empty (items):** Mensaje: "No hay items que coincidan con los filtros"
- **Empty (ledger):** Mensaje: "No hay registros en el ledger que coincidan con los filtros"
- **Error 500:** Mensaje: "Error al cargar resumen de reconciliación" / "Error al cargar items de reconciliación" / "Error al cargar ledger sin match" / "Error al cargar ledger con match" / "Error al cargar detalle del conductor"

---

### 8. Pagos/Cobranza-Yango

**Ruta:** `/pagos/cobranza-yango`

#### Objetivo
Responde: **"¿Cuánto se debe cobrar a Yango y qué items están pendientes?"**

Muestra resumen de cobranza Yango con totales, desglose por semana e items por cobrar.

#### Endpoints Consumidos

1. **`GET /api/v1/dashboard/yango/summary`**
   - Params:
     - `week_start` (Optional[date])
     - `week_end` (Optional[date])

2. **`GET /api/v1/dashboard/yango/receivable_items`**
   - Params:
     - `week_start_monday` (Optional[date])
     - `limit` (int, default=100, max=1000)
     - `offset` (int, default=0)

#### Componentes UI

- **StatCards** (3 cards):
  - `totals.receivable_amount` (Monto por Cobrar)
  - `totals.receivable_items` (Items por Cobrar)
  - `totals.receivable_drivers` (Drivers Únicos)

- **FiltersBar**:
  - DatePicker: `week_start` / `week_end` (para summary)
  - DatePicker: `week_start_monday` (para items)

- **WeeklyChart**:
  - Gráfico de barras: `by_week` con `amount` por semana
  - Eje X: `iso_year_week`
  - Eje Y: Monto (Decimal)

- **ReceivableItemsTable**:
  - Tabla: `items` del endpoint `/yango/receivable_items`
  - Columnas según response schema (ver abajo)
  - Paginación: `offset` / `limit`

#### Columnas Exactas (ReceivableItemsTable - del Contract)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `pay_week_start_monday` | date | Lunes de la semana de pago |
| `pay_iso_year_week` | string | Semana ISO |
| `payable_date` | date | Fecha en que se vuelve pagable |
| `achieved_date` | date \| null | Fecha de logro |
| `lead_date` | date \| null | Fecha del lead |
| `lead_origin` | string \| null | Origen del lead |
| `payer` | string | Quien paga (ej: "yango") |
| `milestone_type` | string \| null | Tipo de milestone |
| `milestone_value` | int \| null | 1, 5, 25 |
| `window_days` | int \| null | Días de ventana |
| `trips_in_window` | int \| null | Viajes en ventana |
| `person_key` | string | UUID de la persona |
| `driver_id` | string \| null | ID del driver |
| `amount` | Decimal | Monto |
| `currency` | string \| null | Moneda |
| `created_at_export` | date \| null | Fecha de exportación |

#### Filtros (Query Params)

**Summary:**
- `week_start`: DatePicker
- `week_end`: DatePicker

**Items:**
- `week_start_monday`: DatePicker
- `limit`: Selector (50, 100, 200, 500, 1000)
- `offset`: Controlado por paginación

#### Drilldown
N/A

#### Estados Vacíos/Errores

- **Loading:** Spinner con texto "Cargando cobranza Yango..."
- **Empty (summary):** Mensaje: "No hay datos de cobranza para el rango seleccionado"
- **Empty (items):** Mensaje: "No hay items por cobrar que coincidan con los filtros"
- **Error 500:** Mensaje: "Error al cargar resumen Yango" / "Error al cargar items Yango"

---

## C) Páginas PENDING

### 1. Runs (Listado) - PENDING Parcial

**Ruta:** `/runs`

#### Qué Falta

- **Endpoint:** `GET /api/v1/identity/runs` (listado de corridas)
- **Qué existe:** 
  - `GET /api/v1/identity/runs/{run_id}/report` ✅
  - `GET /api/v1/identity/metrics/run/{run_id}` ✅

#### Tabla/Vista Sugerida

- **Tabla:** `ops.ingestion_runs` (existe según contrato)
- **Status:** ✅ Tabla existe, solo falta el endpoint

#### Qué se Mostraría en UI cuando Exista

**Objetivo:** "¿Qué corridas de ingesta se han ejecutado y cuál es su estado?"

**Componentes UI:**
- **DataTable** con columnas:
  - `id` (int) - link a detalle
  - `status` (string): 'RUNNING', 'COMPLETED', 'FAILED'
  - `started_at` (datetime)
  - `completed_at` (datetime | null)
  - `scope_date_from` (date | null)
  - `scope_date_to` (date | null)
  - `incremental` (boolean)
  - `error_message` (string | null) - solo si status='FAILED'

**Filtros:**
- `status`: Dropdown (RUNNING, COMPLETED, FAILED, Todos)
- `scope_date_from` / `scope_date_to`: DatePicker
- `skip` / `limit`: Paginación

**Drilldown:**
- Click en `id` → `/runs/{run_id}` → `GET /api/v1/identity/runs/{run_id}/report`

**Estados:**
- Loading, Empty, Error 500

---

### 2. Pagos/Claims - PENDING

**Ruta:** `/pagos/claims`

#### Qué Falta

- **Endpoint:** `GET /api/v1/payments/claims`
- **Status:** ❌ Endpoint no existe, necesita vista SQL

#### Tabla/Vista Sugerida

- **Vista SQL:** No especificada en contrato
- **Sugerencia:** Crear vista `ops.v_payments_claims` o similar que agregue claims con información de pagos

#### Qué se Mostraría en UI cuando Exista

**Objetivo:** "¿Qué claims de pago existen y cuál es su estado?"

**Componentes UI:**
- **DataTable** con columnas sugeridas (depende de la vista SQL):
  - `claim_id` (int)
  - `driver_id` (string)
  - `person_key` (string)
  - `milestone_value` (int)
  - `expected_amount` (Decimal)
  - `paid_status` (string)
  - `pay_week_start_monday` (date)
  - `lead_date` (date)
  - `due_date` (date)
  - `is_paid_effective` (bool)

**Filtros sugeridos:**
- `week_start`: DatePicker
- `milestone_value`: Dropdown (1, 5, 25, Todos)
- `driver_id`: Input text
- `paid_status`: Dropdown
- `skip` / `limit`: Paginación

**Drilldown:**
- Click en `driver_id` → `/pagos/yango-cabinet/driver/{driver_id}` (si aplica)

**Estados:**
- Loading, Empty, Error 500

---

### 3. Ops/Alerts - PENDING

**Ruta:** `/ops/alerts`

#### Qué Falta

- **Endpoints:**
  - `GET /api/v1/ops/alerts` (listado)
  - `POST /api/v1/ops/alerts/{alert_id}/acknowledge` (reconocer)

#### Tabla/Vista Sugerida

- **Tabla:** `ops.alerts` (existe según migraciones y contrato)
- **Status:** ✅ Tabla existe, solo faltan los endpoints

#### Qué se Mostraría en UI cuando Exista

**Objetivo:** "¿Qué alertas del sistema están activas y requieren atención?"

**Componentes UI:**
- **DataTable** con columnas (según contrato):
  - `id` (int)
  - `severity` (string): 'error', 'warning', 'info' - Badge con color
  - `week_label` (string): Semana ISO
  - `message` (string)
  - `details` (object | null): JSONB expandible
  - `acknowledged` (boolean)
  - `acknowledged_at` (datetime | null)
  - `created_at` (datetime)

- **ActionButton**: "Reconocer" por fila (solo si `acknowledged=false`)

**Filtros:**
- `severity`: Dropdown (error, warning, info, Todos)
- `acknowledged`: Checkbox (true/false/null=all)
- `week_label`: Dropdown (valores únicos)
- `skip` / `limit`: Paginación

**Acciones:**
- Click en "Reconocer" → `POST /api/v1/ops/alerts/{alert_id}/acknowledge`

**Estados:**
- Loading, Empty, Error 500
- Success (POST): Toast "Alerta reconocida"

---

### 4. Ops/Data-Health - PENDING

**Ruta:** `/ops/data-health`

#### Qué Falta

- **Endpoint:** `GET /api/v1/ops/data-health`
- **Status:** ❌ Endpoint no existe, necesita vista SQL

#### Tabla/Vista Sugerida

- **Vista SQL:** No especificada en contrato
- **Sugerencia:** Crear vista que agregue métricas de salud de datos:
  - Completitud de campos
  - Calidad de datos
  - Inconsistencias
  - Duplicados potenciales

#### Qué se Mostraría en UI cuando Exista

**Objetivo:** "¿Cuál es el estado de salud de los datos del sistema?"

**Componentes UI sugeridos:**
- **StatCards**:**
  - Completitud de datos (%)
  - Calidad de datos (score)
  - Inconsistencias detectadas (count)
  - Duplicados potenciales (count)

- **MetricsTable**: Métricas por tabla/fuente
- **HealthScore**: Score general de salud

**Filtros sugeridos:**
- `source_table`: Dropdown
- `date_from` / `date_to`: DatePicker

**Estados:**
- Loading, Error 500

---

## Resumen de Cobertura

### Páginas Implementables (NO PENDING): 8
1. ✅ `/dashboard`
2. ✅ `/persons`
3. ✅ `/persons/[person_key]`
4. ✅ `/unmatched`
5. ✅ `/liquidaciones`
6. ✅ `/pagos`
7. ✅ `/pagos/yango-cabinet`
8. ✅ `/pagos/cobranza-yango`

### Páginas PENDING: 4
1. ⚠️ `/runs` (parcial - falta listado)
2. ❌ `/pagos/claims` (falta endpoint y vista)
3. ❌ `/ops/alerts` (falta endpoints, tabla existe)
4. ❌ `/ops/data-health` (falta endpoint y vista)

---

## Reglas de Implementación

### Invariantes Críticos

1. **NO recalcular montos:** Todos los montos (`amount`, `payable_amount`, `receivable_amount`, etc.) vienen del backend. El frontend solo renderiza.

2. **NO recalcular fechas:** `due_date`, `payable_date`, `achieved_date` vienen del backend. El frontend solo renderiza.

3. **NO recalcular buckets:** Agrupaciones, totales, y agregaciones vienen del backend.

4. **NO recalcular tasas:** `match_rate`, `conversion_rate` vienen calculados del backend.

5. **Campos del contrato únicamente:** Solo usar campos documentados en el contrato. No inventar campos adicionales.

### Manejo de Errores

- **400 (Bad Request):** Mostrar mensaje específico según el contrato
- **404 (Not Found):** Mostrar mensaje + botón de navegación cuando aplique
- **500 (Server Error):** Mostrar mensaje genérico + opción de retry cuando aplique
- **401 (Unauthorized):** Solo para endpoints admin (mostrar mensaje de permisos)

### Paginación

- Todos los endpoints de listado soportan `skip`/`offset` y `limit`
- Límites máximos varían según endpoint (100-10000)
- UI debe respetar límites máximos del contrato

### Formato de Datos

- **Fechas:** Formato ISO `YYYY-MM-DD` para inputs, formato localizado para display
- **UUIDs:** Formato estándar `123e4567-e89b-12d3-a456-426614174000`
- **Decimales:** Mostrar con 2 decimales, usar formato de moneda cuando aplique
- **Semanas ISO:** Formato `YYYY-Www` (ej: "2025-W01")

---

## Archivos Modificados

- `docs/frontend/FRONTEND_UI_BLUEPRINT_v1.md` (creado)

---

## Comandos para Validar

```bash
# 1. Verificar que el archivo fue creado
Test-Path docs\frontend\FRONTEND_UI_BLUEPRINT_v1.md

# 2. Contar páginas NO PENDING documentadas
Select-String -Path docs\frontend\FRONTEND_UI_BLUEPRINT_v1.md -Pattern "^### \d+\." | Measure-Object | Select-Object -ExpandProperty Count

# 3. Contar páginas PENDING documentadas
Select-String -Path docs\frontend\FRONTEND_UI_BLUEPRINT_v1.md -Pattern "^### \d+\..*PENDING" | Measure-Object | Select-Object -ExpandProperty Count
```










