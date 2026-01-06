# Contrato Canónico Frontend-Backend v1

**Fecha de generación:** 2025-01-27  
**Versión API:** v1  
**Base URL:** `http://localhost:8000` (desarrollo)

---

## Índice

- [Endpoints UI-Ready](#endpoints-ui-ready)
  - [Dashboard](#dashboard)
  - [Identity](#identity)
  - [Payments](#payments)
  - [Yango Payments (Reconciliation)](#yango-payments-reconciliation)
- [Endpoints Administrativos (NO UI)](#endpoints-administrativos-no-ui)
- [Endpoints Faltantes](#endpoints-faltantes)
- [Auth & Admin](#auth--admin)
- [Contract Coverage Checklist](#contract-coverage-checklist)

---

## Endpoints UI-Ready

### Dashboard

#### `GET /api/v1/dashboard/scout/summary`

**Purpose:** Obtiene resumen agregado de liquidación scouts con totales, desglose por semana y top scouts.

**Grain:** 1 fila = agregación por semana o top scout

**Params:**
- Query:
  - `week_start` (Optional[date]): Fecha inicio de semana
  - `week_end` (Optional[date]): Fecha fin de semana
  - `scout_id` (Optional[int]): ID del scout
  - `lead_origin` (Optional[str]): 'cabinet' o 'migration'

**Response Schema:**
```typescript
{
  totals: {
    payable_amount: Decimal,      // Monto total pagable (policy)
    payable_items: int,            // Cantidad de items pagables
    payable_drivers: int,          // Cantidad de drivers únicos
    payable_scouts: int,            // Cantidad de scouts únicos
    blocked_amount: Decimal,        // Monto bloqueado (unknown confidence)
    blocked_items: int              // Cantidad de items bloqueados
  },
  by_week: [{
    week_start_monday: date,        // Lunes de la semana
    iso_year_week: string,          // Formato ISO: "2025-W01"
    payable_amount: Decimal,
    payable_items: int,
    blocked_amount: Decimal,
    blocked_items: int
  }],
  top_scouts: [{
    acquisition_scout_id: int | null,
    acquisition_scout_name: string | null,
    amount: Decimal,                // Monto total del scout
    items: int,                     // Cantidad de items
    drivers: int                     // Cantidad de drivers únicos
  }]
}
```

**Invariants:**
- Todos los montos (`payable_amount`, `blocked_amount`) vienen calculados del backend
- El frontend NO debe recalcular montos, due dates, o buckets
- `by_week` está ordenado por `week_start_monday DESC` (más reciente primero)
- `top_scouts` está limitado a 10 y ordenado por `amount DESC`

**Error Modes:**
- `400`: Parámetros inválidos (fechas mal formateadas, lead_origin no válido)
  - UI: Mostrar mensaje "Parámetros inválidos" con detalles
- `500`: Error en consulta SQL
  - UI: Mostrar "Error al cargar resumen de scouts. Intente más tarde."

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/scout/summary?week_start=2025-01-01&week_end=2025-01-31"
```

**Source SQL View:** `ops.v_scout_liquidation_open_items_payable_policy`, `ops.v_scout_liquidation_open_items_enriched`

---

#### `GET /api/v1/dashboard/scout/open_items`

**Purpose:** Obtiene lista paginada de items abiertos de liquidación scouts con filtros por confidence.

**Grain:** 1 fila = 1 item de pago scout

**Params:**
- Query:
  - `week_start_monday` (Optional[date]): Fecha inicio de semana (lunes)
  - `scout_id` (Optional[int]): ID del scout
  - `confidence` (str, default="policy"): 'policy', 'high', 'medium', 'unknown'
  - `limit` (int, default=100, max=1000): Límite de resultados
  - `offset` (int, default=0): Offset para paginación

**Response Schema:**
```typescript
{
  items: [{
    payment_item_key: string,       // Clave única del item
    person_key: string,             // UUID de la persona
    lead_origin: string | null,     // 'cabinet' o 'migration'
    scout_id: int | null,           // ID del scout original
    acquisition_scout_id: int | null, // ID del scout atribuido
    acquisition_scout_name: string | null,
    attribution_confidence: string | null, // 'policy', 'high', 'medium', 'unknown'
    attribution_rule: string | null,
    milestone_type: string | null,  // Tipo de milestone
    milestone_value: int | null,      // Valor del milestone (1, 5, 25)
    payable_date: date | null,       // Fecha en que se vuelve pagable
    achieved_date: date | null,      // Fecha en que se alcanzó el milestone
    amount: Decimal,                 // Monto del pago
    currency: string | null,         // Moneda (ej: "PEN")
    driver_id: string | null        // ID del driver
  }],
  total: int,                       // Total de items que cumplen filtros
  limit: int,
  offset: int
}
```

**Invariants:**
- `amount` viene del backend, NO recalcular
- `payable_date` y `achieved_date` vienen del backend
- Ordenamiento: `payable_date DESC, amount DESC`
- Si `confidence="policy"`, usa vista `v_scout_liquidation_open_items_payable_policy`
- Si `confidence` es 'high'/'medium'/'unknown', usa `v_scout_liquidation_open_items_enriched` con filtro

**Error Modes:**
- `400`: `confidence` no válido (debe ser: policy, high, medium, unknown)
  - UI: Mostrar "Nivel de confianza inválido"
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar items. Intente más tarde."

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/scout/open_items?confidence=policy&limit=50&offset=0"
```

**Source SQL View:** `ops.v_scout_liquidation_open_items_payable_policy` o `ops.v_scout_liquidation_open_items_enriched`

---

#### `GET /api/v1/dashboard/yango/summary`

**Purpose:** Obtiene resumen de cobranza Yango con totales y desglose por semana.

**Grain:** 1 fila = agregación por semana

**Params:**
- Query:
  - `week_start` (Optional[date]): Fecha inicio de semana
  - `week_end` (Optional[date]): Fecha fin de semana

**Response Schema:**
```typescript
{
  totals: {
    receivable_amount: Decimal,     // Monto total por cobrar
    receivable_items: int,        // Cantidad de items
    receivable_drivers: int         // Cantidad de drivers únicos
  },
  by_week: [{
    week_start_monday: date,        // Lunes de la semana
    iso_year_week: string,          // Formato ISO: "2025-W01"
    amount: Decimal,                 // Monto de la semana
    items: int,                      // Cantidad de items
    drivers: int                     // Cantidad de drivers únicos
  }]
}
```

**Invariants:**
- `receivable_amount` viene del backend, NO recalcular
- `by_week` ordenado por `week_start_monday DESC`

**Error Modes:**
- `400`: Fechas inválidas
  - UI: Mostrar "Rango de fechas inválido"
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar resumen Yango"

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/yango/summary?week_start=2025-01-01&week_end=2025-01-31"
```

**Source SQL View:** `ops.v_yango_receivable_payable`

---

#### `GET /api/v1/dashboard/yango/receivable_items`

**Purpose:** Obtiene lista paginada de items de cobranza Yango.

**Grain:** 1 fila = 1 item de cobranza Yango

**Params:**
- Query:
  - `week_start_monday` (Optional[date]): Fecha inicio de semana (lunes)
  - `limit` (int, default=100, max=1000): Límite
  - `offset` (int, default=0): Offset

**Response Schema:**
```typescript
{
  items: [{
    pay_week_start_monday: date,    // Lunes de la semana de pago
    pay_iso_year_week: string,       // Semana ISO
    payable_date: date,              // Fecha en que se vuelve pagable
    achieved_date: date | null,      // Fecha de logro
    lead_date: date | null,          // Fecha del lead
    lead_origin: string | null,      // Origen del lead
    payer: string,                   // Quien paga (ej: "yango")
    milestone_type: string | null,
    milestone_value: int | null,     // 1, 5, 25
    window_days: int | null,         // Días de ventana
    trips_in_window: int | null,     // Viajes en ventana
    person_key: string,               // UUID de la persona
    driver_id: string | null,
    amount: Decimal,                  // Monto
    currency: string | null,
    created_at_export: date | null   // Fecha de exportación
  }],
  total: int,
  limit: int,
  offset: int
}
```

**Invariants:**
- `amount` viene del backend, NO recalcular
- Ordenamiento: `pay_week_start_monday DESC, amount DESC`

**Error Modes:**
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar items Yango"

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/yango/receivable_items?week_start_monday=2025-01-06&limit=50"
```

**Source SQL View:** `ops.v_yango_receivable_payable_detail`

---

### Identity

#### `GET /api/v1/identity/stats`

**Purpose:** Obtiene estadísticas agregadas del sistema de identidad (totales de personas, unmatched, links, tasa de conversión).

**Grain:** 1 respuesta = estadísticas globales

**Params:** Ninguno

**Response Schema:**
```typescript
{
  total_persons: int,               // Total de personas en registry
  total_unmatched: int,             // Total de unmatched con status=OPEN
  total_links: int,                 // Total de links creados
  drivers_links: int,                // Links desde tabla 'drivers'
  conversion_rate: float            // Tasa de conversión (drivers_links / cabinet_scouting_links * 100)
}
```

**Invariants:**
- `conversion_rate` viene calculado del backend
- Frontend NO debe recalcular `conversion_rate`

**Error Modes:**
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar estadísticas"

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/identity/stats"
```

**Source SQL:** Consultas directas a `canon.identity_registry`, `canon.identity_unmatched`, `canon.identity_links`

---

#### `GET /api/v1/identity/persons`

**Purpose:** Lista personas del registro canónico con filtros opcionales y paginación.

**Grain:** 1 fila = 1 persona

**Params:**
- Query:
  - `phone` (Optional[str]): Filtrar por teléfono (normalizado)
  - `document` (Optional[str]): Filtrar por documento (contains)
  - `license` (Optional[str]): Filtrar por licencia (normalizado)
  - `name` (Optional[str]): Filtrar por nombre (tokenizado)
  - `confidence_level` (Optional[str]): 'HIGH', 'MEDIUM', 'LOW'
  - `skip` (int, default=0): Offset
  - `limit` (int, default=100, max=1000): Límite

**Response Schema:**
```typescript
[{
  person_key: UUID,                  // Clave única
  confidence_level: string,         // 'HIGH', 'MEDIUM', 'LOW'
  primary_phone: string | null,
  primary_document: string | null,
  primary_license: string | null,
  primary_full_name: string | null,
  flags: object | null,             // JSONB con flags adicionales
  created_at: datetime,
  updated_at: datetime
}]
```

**Invariants:**
- Array directo (no wrapper)
- Ordenamiento implícito por creación

**Error Modes:**
- `400`: `confidence_level` inválido
  - UI: Mostrar "Nivel de confianza inválido"
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar personas"

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/identity/persons?phone=+51987654321&limit=50"
```

**Source SQL:** Consulta directa a `canon.identity_registry`

---

#### `GET /api/v1/identity/persons/{person_key}`

**Purpose:** Obtiene detalle completo de una persona incluyendo todos sus links y si tiene conversión a driver.

**Grain:** 1 respuesta = 1 persona con sus links

**Params:**
- Path:
  - `person_key` (UUID, required): Clave única de la persona

**Response Schema:**
```typescript
{
  person: {
    person_key: UUID,
    confidence_level: string,
    primary_phone: string | null,
    primary_document: string | null,
    primary_license: string | null,
    primary_full_name: string | null,
    flags: object | null,
    created_at: datetime,
    updated_at: datetime
  },
  links: [{
    id: int,
    person_key: UUID,
    source_table: string,            // 'drivers', 'module_ct_cabinet_leads', etc.
    source_pk: string,               // PK de la tabla fuente
    snapshot_date: datetime,
    match_rule: string,              // 'PHONE_EXACT', 'LICENSE_EXACT', etc.
    match_score: int,                // 0-100
    confidence_level: string,
    evidence: object | null,         // JSONB con evidencia
    linked_at: datetime,
    run_id: int | null
  }],
  driver_links: [{                  // Subset de links donde source_table='drivers'
    // Misma estructura que links
  }],
  has_driver_conversion: boolean    // true si tiene al menos 1 driver_link
}
```

**Invariants:**
- `has_driver_conversion` viene del backend
- `driver_links` es un subset filtrado de `links`

**Error Modes:**
- `404`: Persona no encontrada
  - UI: Mostrar "Persona no encontrada" con botón para volver
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar detalle de persona"

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/identity/persons/123e4567-e89b-12d3-a456-426614174000"
```

**Source SQL:** `canon.identity_registry`, `canon.identity_links`

---

#### `GET /api/v1/identity/unmatched`

**Purpose:** Lista registros no matcheados (unmatched) con filtros y paginación.

**Grain:** 1 fila = 1 registro unmatched

**Params:**
- Query:
  - `reason_code` (Optional[str]): Código de razón (ej: 'MISSING_KEYS', 'AMBIGUOUS')
  - `status` (Optional[str]): 'OPEN' o 'RESOLVED'
  - `skip` (int, default=0): Offset
  - `limit` (int, default=100, max=1000): Límite

**Response Schema:**
```typescript
[{
  id: int,
  source_table: string,
  source_pk: string,
  snapshot_date: datetime,
  reason_code: string,              // 'MISSING_KEYS', 'AMBIGUOUS', etc.
  details: object | null,            // JSONB con detalles (puede incluir 'missing_keys')
  candidates_preview: object | null, // JSONB con preview de candidatos
  status: string,                    // 'OPEN' o 'RESOLVED'
  created_at: datetime,
  resolved_at: datetime | null,
  run_id: int | null
}]
```

**Invariants:**
- Array directo
- Ordenamiento: `created_at DESC`

**Error Modes:**
- `400`: `status` inválido
  - UI: Mostrar "Estado inválido"
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar unmatched"

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/identity/unmatched?status=OPEN&limit=50"
```

**Source SQL:** `canon.identity_unmatched`

---

#### `POST /api/v1/identity/unmatched/{id}/resolve`

**Purpose:** Resuelve manualmente un registro unmatched creando un link a una persona específica.

**Grain:** 1 request = 1 resolución

**Params:**
- Path:
  - `id` (int, required): ID del registro unmatched
- Body:
  ```typescript
  {
    person_key: UUID  // Persona a la que vincular
  }
  ```

**Response Schema:**
```typescript
{
  message: string,                   // "Resuelto exitosamente"
  link_id: int                      // ID del link creado
}
```

**Invariants:**
- Crea link con `match_rule="MANUAL_RESOLUTION"`, `match_score=100`, `confidence_level=HIGH`
- Actualiza unmatched a `status=RESOLVED`, `resolved_at=now()`

**Error Modes:**
- `404`: Unmatched no encontrado
  - UI: Mostrar "Registro no encontrado"
- `404`: Persona no encontrada
  - UI: Mostrar "Persona no encontrada"
- `500`: Error al crear link
  - UI: Mostrar "Error al resolver unmatched"

**Ejemplo curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/identity/unmatched/123/resolve" \
  -H "Content-Type: application/json" \
  -d '{"person_key": "123e4567-e89b-12d3-a456-426614174000"}'
```

**Source SQL:** INSERT en `canon.identity_links`, UPDATE en `canon.identity_unmatched`

---

#### `GET /api/v1/identity/runs/{run_id}/report`

**Purpose:** Obtiene reporte detallado de una corrida de ingesta con opción de agrupación semanal.

**Grain:** 1 respuesta = 1 reporte de corrida

**Params:**
- Path:
  - `run_id` (int, required): ID de la corrida
- Query:
  - `group_by` (str, default="none"): 'none' o 'week'
  - `source_table` (Optional[str]): Filtrar por fuente
  - `event_week` (Optional[str]): Semana ISO del evento (ej: '2025-W51')
  - `event_date_from` (Optional[date]): Fecha inicio del evento
  - `event_date_to` (Optional[date]): Fecha fin del evento
  - `include_weekly` (bool, default=True): Incluir datos semanales

**Response Schema:**
```typescript
{
  run: {
    id: int,
    status: string,                 // 'RUNNING', 'COMPLETED', 'FAILED'
    started_at: datetime | null,
    completed_at: datetime | null,
    scope_date_from: date | null,
    scope_date_to: date | null,
    incremental: boolean
  },
  counts_by_source_table: {
    [source_table: string]: {
      total_processed: int,
      matched_count: int,
      unmatched_count: int,
      skipped_count: int
    }
  },
  matched_breakdown: {
    by_match_rule: { [rule: string]: int },
    by_confidence: { [level: string]: int }
  },
  unmatched_breakdown: {
    by_reason_code: { [reason: string]: int },
    top_missing_keys: [{ key: string, count: int }]
  },
  samples: {
    top_unmatched: [{ id, source_table, source_pk, reason_code, details, candidates_preview }],
    top_matched: [{ id, source_table, source_pk, match_rule, confidence_level, match_score }]
  },
  weekly?: [{                      // Solo si group_by='week' y include_weekly=true
    week_start: string,             // ISO date string
    week_label: string,             // "2025-W01"
    source_table: string,
    matched: int,
    unmatched: int,
    processed_total: int,
    match_rate: float,
    matched_by_rule: { [rule: string]: int },
    matched_by_confidence: { [level: string]: int },
    unmatched_by_reason: { [reason: string]: int },
    top_missing_keys: [{ key: string, count: int }]
  }],
  weekly_trend?: [{                // Solo si include_weekly=true
    week_label: string,
    source_table: string | null,
    delta_match_rate: float | null,
    delta_matched: int | null,
    delta_unmatched: int | null,
    current_match_rate: float,
    previous_match_rate: float | null
  }],
  available_event_weeks?: string[], // Solo si include_weekly=true
  scouting_kpis?: [{               // Solo si include_weekly=true y source_table incluye scouting
    week_label: string,
    source_table: string,
    processed_scouting: int,
    candidates_detected: int,
    candidate_rate: float,
    high_confidence_candidates: int,
    avg_time_to_match_days: float | null
  }]
}
```

**Invariants:**
- `match_rate` viene calculado del backend (matched / processed_total * 100)
- Frontend NO debe recalcular `match_rate`
- `weekly_trend` compara última semana vs penúltima

**Error Modes:**
- `404`: Run no encontrado
  - UI: Mostrar "Corrida no encontrada"
- `400`: `event_week` formato inválido (debe ser 'YYYY-Www')
  - UI: Mostrar "Formato de semana inválido. Use 'YYYY-Www'"
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar reporte"

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/identity/runs/1/report?group_by=week&include_weekly=true"
```

**Source SQL:** `ops.ingestion_runs`, `canon.identity_links`, `canon.identity_unmatched`, agregaciones semanales

---

#### `GET /api/v1/identity/metrics/global`

**Purpose:** Obtiene métricas globales (histórico completo) sin filtrar por run_id, con opciones de modo (summary, weekly, breakdowns).

**Grain:** 1 respuesta = métricas globales

**Params:**
- Query:
  - `mode` (str, default="summary"): 'summary', 'weekly', o 'breakdowns'
  - `source_table` (Optional[str]): Filtrar por fuente
  - `event_date_from` (Optional[date]): Fecha inicio del evento
  - `event_date_to` (Optional[date]): Fecha fin del evento

**Response Schema:**
```typescript
{
  scope: {
    run_id: null,                   // Siempre null para global
    source_table: string | null,
    event_date_from: date | null,
    event_date_to: date | null,
    mode: string                    // 'summary', 'weekly', 'breakdowns'
  },
  totals: {
    total_processed: int,           // matched + unmatched
    matched: int,
    unmatched: int,
    match_rate: float               // Porcentaje (0-100)
  },
  weekly?: [{                      // Solo si mode='weekly' o 'breakdowns'
    // Misma estructura que en runs/{run_id}/report
  }],
  weekly_trend?: [{                // Solo si mode='weekly' o 'breakdowns'
    // Misma estructura que en runs/{run_id}/report
  }],
  available_event_weeks?: string[], // Solo si mode='weekly' o 'breakdowns'
  breakdowns?: {                    // Solo si mode='breakdowns'
    matched_by_rule: { [rule: string]: int },
    matched_by_confidence: { [level: string]: int },
    unmatched_by_reason: { [reason: string]: int }
  }
}
```

**Invariants:**
- `match_rate` viene del backend
- Si `mode='summary'`, solo retorna `totals`
- Si `mode='weekly'`, incluye `weekly`, `weekly_trend`, `available_event_weeks`
- Si `mode='breakdowns'`, incluye todo lo anterior + `breakdowns`

**Error Modes:**
- `400`: `mode` inválido (debe ser 'summary', 'weekly', 'breakdowns')
  - UI: Mostrar "Modo inválido"
- `400`: `event_date_from > event_date_to`
  - UI: Mostrar "Rango de fechas inválido"
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar métricas"

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/identity/metrics/global?mode=weekly&source_table=module_ct_scouting_daily"
```

**Source SQL:** `canon.identity_links`, `canon.identity_unmatched` (sin filtro de run_id)

---

#### `GET /api/v1/identity/metrics/run/{run_id}`

**Purpose:** Obtiene métricas para un run específico con opciones de modo.

**Grain:** 1 respuesta = métricas de un run

**Params:**
- Path:
  - `run_id` (int, required): ID de la corrida
- Query:
  - `mode` (str, default="summary"): 'summary', 'weekly', o 'breakdowns'
  - `source_table` (Optional[str]): Filtrar por fuente
  - `event_date_from` (Optional[date]): Fecha inicio del evento
  - `event_date_to` (Optional[date]): Fecha fin del evento

**Response Schema:** Misma estructura que `/metrics/global`, pero `scope.run_id` será el `run_id` proporcionado.

**Invariants:**
- Similar a `/metrics/global` pero filtrado por `run_id`

**Error Modes:**
- `404`: Run no encontrado
  - UI: Mostrar "Corrida no encontrada"
- `400`: `mode` inválido o fechas inválidas
  - UI: Mostrar mensaje de error correspondiente
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar métricas"

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/identity/metrics/run/1?mode=breakdowns"
```

**Source SQL:** `canon.identity_links`, `canon.identity_unmatched` (filtrado por `run_id`)

---

#### `GET /api/v1/identity/metrics/window`

**Purpose:** Obtiene métricas para una ventana de tiempo específica (sin filtrar por run_id).

**Grain:** 1 respuesta = métricas de ventana

**Params:**
- Query:
  - `from` (date, required, alias="from"): Fecha inicio de la ventana
  - `to` (date, required, alias="to"): Fecha fin de la ventana
  - `mode` (str, default="summary"): 'summary', 'weekly', o 'breakdowns'
  - `source_table` (Optional[str]): Filtrar por fuente

**Response Schema:** Misma estructura que `/metrics/global`, pero `scope.event_date_from` y `scope.event_date_to` serán los valores proporcionados.

**Invariants:**
- Similar a `/metrics/global` pero filtrado por `snapshot_date` en ventana

**Error Modes:**
- `400`: `from > to`
  - UI: Mostrar "Fecha inicio debe ser <= fecha fin"
- `400`: `mode` inválido
  - UI: Mostrar "Modo inválido"
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar métricas"

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/identity/metrics/window?from=2025-01-01&to=2025-01-31&mode=weekly"
```

**Source SQL:** `canon.identity_links`, `canon.identity_unmatched` (filtrado por `snapshot_date` en ventana)

---

### Payments

#### `GET /api/v1/payments/eligibility`

**Purpose:** Consulta la vista de elegibilidad de pagos con filtros opcionales y ordenamiento.

**Grain:** 1 fila = 1 registro de elegibilidad de pago

**Params:**
- Query:
  - `origin_tag` (Optional[str]): 'cabinet' o 'fleet_migration'
  - `rule_scope` (Optional[str]): 'scout' o 'partner'
  - `is_payable` (Optional[bool]): Filtrar por is_payable
  - `scout_id` (Optional[int]): Filtrar por scout_id
  - `driver_id` (Optional[str]): Filtrar por driver_id
  - `payable_from` (Optional[date]): Filtrar por payable_date >= payable_from
  - `payable_to` (Optional[date]): Filtrar por payable_date <= payable_to
  - `limit` (int, default=200, max=1000): Límite
  - `offset` (int, default=0): Offset
  - `order_by` (OrderByField, default=payable_date): 'payable_date', 'lead_date', 'amount'
  - `order_dir` (OrderDirection, default=asc): 'asc' o 'desc'

**Response Schema:**
```typescript
{
  status: string,                   // "ok"
  count: int,                      // Cantidad de filas retornadas
  filters: {                       // Filtros aplicados (solo los no-null)
    [key: string]: any
  },
  rows: [{
    person_key: string | null,
    origin_tag: string | null,      // 'cabinet' o 'fleet_migration'
    scout_id: int | null,
    driver_id: string | null,
    lead_date: date | null,
    rule_id: int | null,
    rule_scope: string | null,      // 'scout' o 'partner'
    milestone_trips: int | null,    // Viajes requeridos para milestone
    window_days: int | null,        // Días de ventana
    currency: string | null,
    amount: Decimal | null,         // Monto del pago
    rule_valid_from: date | null,
    rule_valid_to: date | null,
    milestone_achieved: bool | null,
    achieved_date: date | null,
    achieved_trips_in_window: int | null,
    is_payable: bool | null,        // Si cumple condiciones para ser pagable
    payable_date: date | null,      // Fecha en que se vuelve pagable
    payment_scheme: string | null   // Esquema de pago
  }]
}
```

**Invariants:**
- `amount`, `payable_date`, `is_payable` vienen del backend, NO recalcular
- Ordenamiento según `order_by` y `order_dir`

**Error Modes:**
- `400`: `origin_tag` inválido (debe ser 'cabinet' o 'fleet_migration')
  - UI: Mostrar "Origen inválido"
- `400`: `rule_scope` inválido (debe ser 'scout' o 'partner')
  - UI: Mostrar "Scope de regla inválido"
- `400`: `order_by` inválido
  - UI: Mostrar "Campo de ordenamiento inválido"
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar elegibilidad de pagos"

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/payments/eligibility?is_payable=true&payable_from=2025-01-01&payable_to=2025-01-31&limit=50"
```

**Source SQL View:** `ops.v_payment_calculation`

---

### Yango Payments (Reconciliation)

#### `GET /api/v1/yango/payments/reconciliation/summary`

**Purpose:** Obtiene resumen agregado de reconciliación de pagos Yango por semana y milestone.

**Grain:** 1 fila = agregación por semana + milestone

**Params:**
- Query:
  - `week_start` (Optional[date]): Filtra por semana (lunes)
  - `milestone_value` (Optional[int]): Filtra por milestone (1, 5, 25)
  - `mode` (Literal['real', 'assumed'], default='real'): 'real' (solo pagos confirmados) o 'assumed' (incluye asumidos)
  - `limit` (int, default=1000, max=10000): Límite

**Response Schema:**
```typescript
{
  status: string,                   // "ok"
  count: int,
  filters: {
    week_start: string | null,
    milestone_value: int | null,
    mode: string,
    limit: int,
    _validation?: {                 // Metadatos de validación
      ledger_total_rows: int,
      ledger_rows_is_paid_true: int,
      ledger_rows_is_paid_true_and_driver_id_null: int
    }
  },
  rows: [{
    pay_week_start_monday: date,
    milestone_value: int,           // 1, 5, 25
    amount_expected_sum: Decimal,   // Monto esperado total
    amount_paid_confirmed_sum: Decimal, // Monto pagado confirmado
    amount_paid_enriched_sum: Decimal,  // Monto pagado enriquecido
    amount_paid_total_visible: Decimal, // Total visible (confirmed + enriched)
    amount_pending_active_sum: Decimal, // Monto pendiente activo
    amount_pending_expired_sum: Decimal, // Monto pendiente expirado
    amount_diff: Decimal,           // Diferencia (expected - paid_visible)
    amount_diff_assumed: Decimal,   // Diferencia asumida (expected - paid_visible - pending_active)
    anomalies_total: int,           // Cantidad de anomalías
    count_expected: int,            // Cantidad esperada
    count_paid_confirmed: int,
    count_paid_enriched: int,
    count_paid: int,                // Total pagado
    count_pending_active: int,
    count_pending_expired: int,
    count_drivers: int              // Drivers únicos
  }]
}
```

**Invariants:**
- Todos los montos vienen del backend, NO recalcular
- `amount_diff` = `amount_expected_sum - amount_paid_total_visible`
- `amount_diff_assumed` = `amount_expected_sum - amount_paid_total_visible - amount_pending_active_sum`
- Ordenamiento: `pay_week_start_monday DESC, milestone_value ASC`

**Error Modes:**
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar resumen de reconciliación"

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/yango/payments/reconciliation/summary?week_start=2025-01-06&milestone_value=1"
```

**Source SQL View:** `ops.v_yango_payments_claims_cabinet_14d`, `ops.v_yango_payments_ledger_latest_enriched` (validación)

---

#### `GET /api/v1/yango/payments/reconciliation/items`

**Purpose:** Obtiene items detallados de reconciliación de pagos Yango con paginación.

**Grain:** 1 fila = 1 item de claim/pago

**Params:**
- Query:
  - `week_start` (Optional[date]): Filtra por semana (lunes)
  - `milestone_value` (Optional[int]): Filtra por milestone (1, 5, 25)
  - `driver_id` (Optional[str]): Filtra por driver_id
  - `paid_status` (Optional[str]): Filtra por paid_status
  - `limit` (int, default=1000, max=10000): Límite
  - `offset` (int, default=0): Offset

**Response Schema:**
```typescript
{
  status: string,
  count: int,                       // Cantidad retornada
  total: int,                       // Total que cumple filtros
  filters: {
    [key: string]: any
  },
  rows: [{
    driver_id: string | null,
    person_key: string | null,
    lead_date: date | null,
    pay_week_start_monday: date | null,
    milestone_value: int | null,
    expected_amount: Decimal | null,
    currency: string | null,
    due_date: date | null,          // lead_date + 14 days
    window_status: string | null,   // 'active' o 'expired'
    paid_payment_key: string | null,
    paid_payment_key_confirmed: string | null,
    paid_payment_key_enriched: string | null,
    paid_date: date | null,
    paid_date_confirmed: date | null,
    paid_date_enriched: date | null,
    is_paid_effective: bool | null, // Si está efectivamente pagado
    match_method: string | null,
    paid_status: string | null,    // 'paid_confirmed', 'paid_enriched', 'pending_active', 'pending_expired'
    identity_status: string | null,
    match_rule: string | null,
    match_confidence: string | null
  }]
}
```

**Invariants:**
- `expected_amount`, `due_date`, `is_paid_effective` vienen del backend, NO recalcular
- `due_date` = `lead_date + 14 days` (calculado en SQL)
- Ordenamiento: `pay_week_start_monday DESC, milestone_value ASC, lead_date DESC`

**Error Modes:**
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar items de reconciliación"

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/yango/payments/reconciliation/items?week_start=2025-01-06&limit=50"
```

**Source SQL View:** `ops.v_yango_payments_claims_cabinet_14d`

---

#### `GET /api/v1/yango/payments/reconciliation/ledger/unmatched`

**Purpose:** Obtiene registros del ledger que no tienen match contra claims.

**Grain:** 1 fila = 1 registro del ledger sin match

**Params:**
- Query:
  - `is_paid` (Optional[bool]): Filtrar por is_paid
  - `driver_id` (Optional[str]): Filtrar por driver_id
  - `identity_status` (Optional[str]): Filtrar por identity_status
  - `limit` (int, default=1000, max=10000): Límite
  - `offset` (int, default=0): Offset

**Response Schema:**
```typescript
{
  status: string,
  count: int,
  total: int,
  filters: {
    [key: string]: any
  },
  rows: [{
    payment_key: string,
    pay_date: date | null,
    is_paid: bool | null,
    milestone_value: int | null,
    driver_id: string | null,
    person_key: string | null,
    raw_driver_name: string | null,
    driver_name_normalized: string | null,
    match_rule: string | null,
    match_confidence: string | null,
    latest_snapshot_at: datetime | null,
    source_pk: string | null,
    identity_source: string | null,
    identity_enriched: string | null,
    driver_id_final: string | null,
    person_key_final: string | null,
    identity_status: string | null
  }]
}
```

**Invariants:**
- Solo registros que NO tienen match en `v_yango_payments_claims_cabinet_14d`
- Ordenamiento: `pay_date DESC, payment_key`

**Error Modes:**
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar ledger sin match"

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/yango/payments/reconciliation/ledger/unmatched?is_paid=false&limit=50"
```

**Source SQL View:** `ops.v_yango_payments_ledger_latest_enriched` (con NOT EXISTS contra `v_yango_payments_claims_cabinet_14d`)

---

#### `GET /api/v1/yango/payments/reconciliation/ledger/matched`

**Purpose:** Obtiene registros del ledger que tienen match contra claims.

**Grain:** 1 fila = 1 registro del ledger con match

**Params:**
- Query:
  - `is_paid` (Optional[bool]): Filtrar por is_paid
  - `driver_id` (Optional[str]): Filtrar por driver_id
  - `limit` (int, default=1000, max=10000): Límite
  - `offset` (int, default=0): Offset

**Response Schema:** Misma estructura que `/ledger/unmatched`

**Invariants:**
- Solo registros que SÍ tienen match en `v_yango_payments_claims_cabinet_14d`

**Error Modes:**
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar ledger con match"

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/yango/payments/reconciliation/ledger/matched?is_paid=true&limit=50"
```

**Source SQL View:** `ops.v_yango_payments_ledger_latest_enriched` (con EXISTS contra `v_yango_payments_claims_cabinet_14d`)

---

#### `GET /api/v1/yango/payments/reconciliation/driver/{driver_id}`

**Purpose:** Obtiene detalle de claims y pagos para un conductor específico.

**Grain:** 1 respuesta = 1 conductor con todos sus claims

**Params:**
- Path:
  - `driver_id` (str, required): ID del conductor

**Response Schema:**
```typescript
{
  status: string,
  driver_id: string,
  person_key: string | null,
  claims: [{
    milestone_value: int | null,
    expected_amount: Decimal | null,
    currency: string | null,
    lead_date: date | null,
    due_date: date | null,          // lead_date + 14 days
    pay_week_start_monday: date | null,
    paid_status: string | null,
    paid_payment_key: string | null,
    paid_date: date | null,
    is_paid_effective: bool | null,
    match_method: string | null,
    identity_status: string | null,
    match_rule: string | null,
    match_confidence: string | null
  }],
  summary: {
    total_expected: Decimal,        // Suma de expected_amount
    total_paid: Decimal,            // Suma de expected_amount donde is_paid_effective=true
    count_paid: int,                // Cantidad de claims pagados
    count_pending_active: int,      // Cantidad con paid_status='pending_active'
    count_pending_expired: int      // Cantidad con paid_status='pending_expired'
  }
}
```

**Invariants:**
- `summary.total_expected`, `summary.total_paid` vienen del backend, NO recalcular
- `claims` ordenado por: `pay_week_start_monday DESC, milestone_value ASC, lead_date DESC`

**Error Modes:**
- `500`: Error en consulta
  - UI: Mostrar "Error al cargar detalle del conductor"

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/yango/payments/reconciliation/driver/DRIVER123"
```

**Source SQL View:** `ops.v_yango_payments_claims_cabinet_14d`

---

## Endpoints Administrativos (NO UI)

Estos endpoints **NO** deben ser consumidos por el frontend en la UI normal. Son para operaciones administrativas o background:

- `POST /api/v1/identity/drivers-index/refresh` - Refresca índice (background job)
- `POST /api/v1/identity/run` - Ejecuta corrida de ingesta (background task)
- `POST /api/v1/identity/scouting/process-observations` - Procesa observaciones (background)
- `POST /api/v1/attribution/populate-events` - Pobla eventos (background)
- `POST /api/v1/attribution/process-ledger` - Procesa ledger (background)
- `POST /api/v1/liquidation/scout/mark_paid` - Marca pagos (requiere admin token, acción administrativa)

**Nota:** Si se necesita una UI para ejecutar estas operaciones, debe ser una sección administrativa separada con autenticación adecuada.

---

## Endpoints Faltantes

Para una UI limpia y completa, se identifican los siguientes endpoints faltantes:

### 1. Listado de Corridas (Runs)

**Suggested Path:** `GET /api/v1/identity/runs`

**Purpose:** Lista todas las corridas de ingesta con paginación y filtros.

**Required Response Fields:**
```typescript
{
  runs: [{
    id: int,
    status: string,                 // 'RUNNING', 'COMPLETED', 'FAILED'
    job_type: string,               // 'IDENTITY_RUN'
    started_at: datetime | null,
    completed_at: datetime | null,
    scope_date_from: date | null,
    scope_date_to: date | null,
    incremental: boolean,
    error_message: string | null     // Si status='FAILED'
  }],
  total: int,
  limit: int,
  offset: int
}
```

**Source SQL:** `ops.ingestion_runs` (tabla directa)

**Status:** ✅ **Needs endpoint** (tabla existe, solo falta el endpoint)

---

### 2. Listado de Alertas

**Suggested Path:** `GET /api/v1/ops/alerts`

**Purpose:** Lista alertas del sistema con filtros por severidad y estado.

**Required Response Fields:**
```typescript
{
  alerts: [{
    id: int,
    severity: string,               // 'error', 'warning', 'info'
    week_label: string,             // Semana ISO
    message: string,
    details: object | null,         // JSONB con detalles
    acknowledged: boolean,
    acknowledged_at: datetime | null,
    created_at: datetime
  }],
  total: int,
  limit: int,
  offset: int
}
```

**Source SQL:** `ops.alerts` (tabla existe según migraciones)

**Status:** ✅ **Needs endpoint** (tabla existe, solo falta el endpoint)

---

### 3. Reconocer Alerta

**Suggested Path:** `POST /api/v1/ops/alerts/{alert_id}/acknowledge`

**Purpose:** Marca una alerta como reconocida.

**Required Response Fields:**
```typescript
{
  message: string,                  // "Alerta reconocida"
  alert_id: int
}
```

**Source SQL:** UPDATE en `ops.alerts` (acknowledged=true, acknowledged_at=now())

**Status:** ✅ **Needs endpoint**

---

### 4. Preview de Liquidación Scout (UI)

**Suggested Path:** `GET /api/v1/liquidation/scout/preview` (ya existe pero requiere admin)

**Purpose:** Previsualiza items que serán marcados como pagados.

**Status:** ✅ **Exists** pero requiere admin token. Considerar versión read-only para UI.

---

### 5. Estadísticas de Attribution (UI)

**Suggested Path:** `GET /api/v1/attribution/stats` (ya existe)

**Purpose:** Estadísticas agregadas del sistema de atribución.

**Status:** ✅ **Exists** - Puede usarse en UI

---

### 6. Listado de Eventos de Attribution (UI)

**Suggested Path:** `GET /api/v1/attribution/events` (ya existe)

**Purpose:** Lista eventos de atribución con filtros.

**Status:** ✅ **Exists** - Puede usarse en UI

---

### 7. Detalle de Ledger de Attribution (UI)

**Suggested Path:** `GET /api/v1/attribution/ledger/{person_key}` (ya existe)

**Purpose:** Obtiene entrada del ledger de atribución para una persona.

**Status:** ✅ **Exists** - Puede usarse en UI

---

## Auth & Admin

### Endpoints que Requieren X-Admin-Token

Solo un endpoint requiere autenticación administrativa:

- `POST /api/v1/liquidation/scout/mark_paid` - Requiere header `X-Admin-Token`

**Política Recomendada para UI:**

1. **Ocultar acciones administrativas si no hay token:**
   - El frontend debe verificar si tiene un token de administrador configurado
   - Si no hay token, ocultar botones/acciones que llamen a endpoints administrativos
   - Mostrar mensaje: "Esta acción requiere permisos de administrador"

2. **Manejo de errores 401:**
   - Si el endpoint retorna `401 Unauthorized`, mostrar: "Token de administrador inválido o faltante"
   - Ofrecer opción de ingresar token (si aplica en la UI)

3. **Endpoints read-only:**
   - Los endpoints de lectura (GET) son públicos y no requieren autenticación
   - El frontend puede consumirlos libremente

4. **Endpoints de escritura:**
   - `POST /api/v1/identity/unmatched/{id}/resolve` - NO requiere admin token (acción de usuario)
   - Solo `mark_paid` requiere admin token

---

## Contract Coverage Checklist

### Páginas del Frontend y Endpoints Soportados

#### ✅ `/dashboard` (page.tsx)
- [x] `GET /api/v1/identity/stats` - Estadísticas generales
- [x] `GET /api/v1/identity/metrics/global` - Métricas globales
- [x] `GET /api/v1/identity/runs/{run_id}/report` - Reporte de última corrida
- [ ] `GET /api/v1/identity/runs` - **FALTA** (listado de corridas)
- [ ] `GET /api/v1/ops/alerts` - **FALTA** (listado de alertas)
- [ ] `POST /api/v1/ops/alerts/{alert_id}/acknowledge` - **FALTA** (reconocer alerta)

#### ✅ `/persons` (page.tsx)
- [x] `GET /api/v1/identity/persons` - Listado de personas

#### ✅ `/persons/[person_key]` (page.tsx)
- [x] `GET /api/v1/identity/persons/{person_key}` - Detalle de persona

#### ✅ `/runs` (page.tsx)
- [ ] `GET /api/v1/identity/runs` - **FALTA** (listado de corridas)
- [x] `GET /api/v1/identity/runs/{run_id}/report` - Reporte de corrida
- [x] `GET /api/v1/identity/metrics/run/{run_id}` - Métricas de corrida

#### ✅ `/unmatched` (page.tsx)
- [x] `GET /api/v1/identity/unmatched` - Listado de unmatched
- [x] `POST /api/v1/identity/unmatched/{id}/resolve` - Resolver unmatched

#### ⚠️ `/liquidaciones` (page.tsx)
- [x] `GET /api/v1/dashboard/scout/summary` - Resumen scouts
- [x] `GET /api/v1/dashboard/scout/open_items` - Items abiertos
- [ ] `GET /api/v1/liquidation/scout/preview` - Existe pero requiere admin (considerar versión read-only)

#### ⚠️ `/pagos` (page.tsx)
- [x] `GET /api/v1/payments/eligibility` - Elegibilidad de pagos

#### ⚠️ `/pagos/claims` (page.tsx)
- [ ] **FALTA ENDPOINT** - No hay endpoint específico para claims. Considerar:
  - `GET /api/v1/payments/claims` - Listado de claims con filtros

#### ⚠️ `/pagos/yango-cabinet` (page.tsx)
- [x] `GET /api/v1/yango/payments/reconciliation/summary` - Resumen reconciliación
- [x] `GET /api/v1/yango/payments/reconciliation/items` - Items de reconciliación
- [x] `GET /api/v1/yango/payments/reconciliation/driver/{driver_id}` - Detalle conductor

#### ⚠️ `/pagos/cobranza-yango` (page.tsx)
- [x] `GET /api/v1/dashboard/yango/summary` - Resumen cobranza
- [x] `GET /api/v1/dashboard/yango/receivable_items` - Items por cobrar

#### ⚠️ `/ops/data-health` (page.tsx)
- [ ] **FALTA ENDPOINT** - No hay endpoint para data health. Considerar:
  - `GET /api/v1/ops/data-health` - Métricas de salud de datos

---

### Resumen de Cobertura

**Endpoints UI-Ready:** 20 endpoints  
**Endpoints Administrativos (NO UI):** 6 endpoints  
**Endpoints Faltantes Identificados:** 5 endpoints

**Cobertura por Módulo:**
- ✅ **Dashboard:** 4/4 endpoints (100%)
- ✅ **Identity:** 8/11 endpoints UI-ready (73% - 3 son admin/background)
- ⚠️ **Payments:** 1/1 endpoint (100%)
- ✅ **Yango Payments:** 5/5 endpoints (100%)
- ⚠️ **Ops:** 0/2 endpoints (0% - faltan alerts y data-health)
- ⚠️ **Attribution:** 3/5 endpoints UI-ready (60% - 2 son background)

---

## Archivos Modificados

- `docs/contracts/FRONTEND_BACKEND_CONTRACT_v1.md` (creado)

---

## Comandos para Validar

```bash
# 1. Verificar que el archivo fue creado
Test-Path docs\contracts\FRONTEND_BACKEND_CONTRACT_v1.md

# 2. Contar endpoints UI-ready documentados
Select-String -Path docs\contracts\FRONTEND_BACKEND_CONTRACT_v1.md -Pattern "^#### \`" | Measure-Object | Select-Object -ExpandProperty Count

# 3. Verificar endpoints faltantes
Select-String -Path docs\contracts\FRONTEND_BACKEND_CONTRACT_v1.md -Pattern "Status:.*FALTA" | Select-Object -ExpandProperty Line
```









