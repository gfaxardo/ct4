# Inventario Completo de Endpoints del Backend

**Fecha de generación:** 2025-01-27  
**Versión API:** v1  
**Base URL:** `http://localhost:8000` (desarrollo)

---

## Índice

- [Health](#health)
- [Identity](#identity)
- [Attribution](#attribution)
- [Dashboard](#dashboard)
- [Liquidation](#liquidation)
- [Ops](#ops)
- [Payments](#payments)
- [Yango Payments](#yango-payments)

---

## Health

### `GET /health`

**Módulo:** `app/api/health.py`  
**Handler:** `health_check()`  
**Tags:** (sin tags)  
**Response Schema:** `dict` con `{"status": "ok"}`

**Descripción:** Health check básico del sistema.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/health"
```

**Vista SQL:** Ninguna (respuesta hardcoded)

---

## Identity

### `POST /api/v1/identity/drivers-index/refresh`

**Módulo:** `app/api/v1/identity.py`  
**Handler:** `refresh_drivers_index()`  
**Tags:** `["identity"]`  
**Response Schema:** `IngestionRunSchema` (`app/schemas/ingestion.py`)

**Descripción:** Refresca el índice de drivers antes de procesar matching.

**Ejemplo curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/identity/drivers-index/refresh"
```

**Vista SQL:** 
- Consume servicio `IngestionService.refresh_drivers_index_job()`
- Actualiza `canon.drivers_index`

---

### `POST /api/v1/identity/run`

**Módulo:** `app/api/v1/identity.py`  
**Handler:** `run_ingestion()`  
**Tags:** `["identity"]`  
**Response Schema:** `IngestionRunSchema` (`app/schemas/ingestion.py`)

**Query Parameters:**
- `date_from` (Optional[date]): Fecha inicio del scope
- `date_to` (Optional[date]): Fecha fin del scope
- `scope_date` (Optional[date]): Fecha única del scope (alternativa)
- `source_tables` (Optional[List[str]]): Tablas a procesar
- `incremental` (bool, default=True): Modo incremental
- `refresh_index` (bool, default=False): Refrescar drivers_index antes

**Descripción:** Ejecuta una corrida de ingesta de identidad (background task).

**Ejemplo curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/identity/run?date_from=2025-01-01&date_to=2025-01-31&incremental=true"
```

**Vista SQL:**
- Crea registro en `ops.ingestion_runs`
- Procesa tablas: `module_ct_cabinet_leads`, `module_ct_scouting_daily`, `drivers`
- Inserta en `canon.identity_registry`, `canon.identity_links`, `canon.identity_unmatched`

---

### `GET /api/v1/identity/persons`

**Módulo:** `app/api/v1/identity.py`  
**Handler:** `list_persons()`  
**Tags:** `["identity"]`  
**Response Schema:** `List[IdentityRegistrySchema]` (`app/schemas/identity.py`)

**Query Parameters:**
- `phone` (Optional[str]): Filtrar por teléfono
- `document` (Optional[str]): Filtrar por documento
- `license` (Optional[str]): Filtrar por licencia
- `name` (Optional[str]): Filtrar por nombre
- `confidence_level` (Optional[str]): Filtrar por nivel de confianza
- `skip` (int, default=0): Offset para paginación
- `limit` (int, default=100, max=1000): Límite de resultados

**Descripción:** Lista personas del registro canónico con filtros opcionales.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/identity/persons?phone=+51987654321&limit=50"
```

**Vista SQL:**
- Consulta directa a `canon.identity_registry`
- Filtros aplicados vía SQLAlchemy ORM

---

### `GET /api/v1/identity/stats`

**Módulo:** `app/api/v1/identity.py`  
**Handler:** `get_stats()`  
**Tags:** `["identity"]`  
**Response Schema:** `StatsResponse` (`app/schemas/identity.py`)

**Descripción:** Obtiene estadísticas agregadas del sistema de identidad.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/identity/stats"
```

**Vista SQL:**
- Consulta `canon.identity_registry` (COUNT)
- Consulta `canon.identity_unmatched` (COUNT con filtro status=OPEN)
- Consulta `canon.identity_links` (COUNT por source_table)

---

### `GET /api/v1/identity/persons/{person_key}`

**Módulo:** `app/api/v1/identity.py`  
**Handler:** `get_person()`  
**Tags:** `["identity"]`  
**Response Schema:** `PersonDetail` (`app/schemas/identity.py`)

**Path Parameters:**
- `person_key` (UUID): Clave única de la persona

**Descripción:** Obtiene detalle completo de una persona incluyendo sus links.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/identity/persons/123e4567-e89b-12d3-a456-426614174000"
```

**Vista SQL:**
- Consulta `canon.identity_registry` por `person_key`
- Consulta `canon.identity_links` filtrado por `person_key`

---

### `GET /api/v1/identity/unmatched`

**Módulo:** `app/api/v1/identity.py`  
**Handler:** `list_unmatched()`  
**Tags:** `["identity"]`  
**Response Schema:** `List[IdentityUnmatchedSchema]` (`app/schemas/identity.py`)

**Query Parameters:**
- `reason_code` (Optional[str]): Filtrar por código de razón
- `status` (Optional[str]): Filtrar por estado (OPEN, RESOLVED)
- `skip` (int, default=0): Offset
- `limit` (int, default=100, max=1000): Límite

**Descripción:** Lista registros no matcheados (unmatched).

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/identity/unmatched?status=OPEN&limit=50"
```

**Vista SQL:**
- Consulta `canon.identity_unmatched` con filtros opcionales

---

### `POST /api/v1/identity/unmatched/{id}/resolve`

**Módulo:** `app/api/v1/identity.py`  
**Handler:** `resolve_unmatched()`  
**Tags:** `["identity"]`  
**Response Schema:** `dict` con `{"message": str, "link_id": int}`

**Path Parameters:**
- `id` (int): ID del registro unmatched

**Body Schema:** `UnmatchedResolveRequest` (`app/schemas/identity.py`)
- `person_key` (UUID): Persona a la que vincular

**Descripción:** Resuelve manualmente un registro unmatched creando un link.

**Ejemplo curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/identity/unmatched/123/resolve" \
  -H "Content-Type: application/json" \
  -d '{"person_key": "123e4567-e89b-12d3-a456-426614174000"}'
```

**Vista SQL:**
- INSERT en `canon.identity_links` con `match_rule="MANUAL_RESOLUTION"`
- UPDATE en `canon.identity_unmatched` (status=RESOLVED, resolved_at)

---

### `POST /api/v1/identity/scouting/process-observations`

**Módulo:** `app/api/v1/identity.py`  
**Handler:** `process_scouting_observations()`  
**Tags:** `["identity"]`  
**Response Schema:** `dict` con `{"message": str, "stats": dict}`

**Query Parameters:**
- `date_from` (Optional[date]): Fecha inicio del scope
- `date_to` (Optional[date]): Fecha fin del scope
- `run_id` (Optional[int]): ID de corrida (opcional)

**Descripción:** Procesa observaciones de scouting para matching.

**Ejemplo curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/identity/scouting/process-observations?date_from=2025-01-01&date_to=2025-01-31"
```

**Vista SQL:**
- Consume servicio `ScoutingObservationService.process_scouting_observations()`
- Consulta `public.module_ct_scouting_daily`
- Inserta en `observational.scouting_match_candidates`

---

### `GET /api/v1/identity/runs/{run_id}/report`

**Módulo:** `app/api/v1/identity.py`  
**Handler:** `get_run_report()`  
**Tags:** `["identity"]`  
**Response Schema:** `RunReportResponse` (`app/schemas/identity.py`)

**Path Parameters:**
- `run_id` (int): ID de la corrida

**Query Parameters:**
- `group_by` (str, default="none"): Agrupación: 'none' o 'week'
- `source_table` (Optional[str]): Filtrar por fuente
- `event_week` (Optional[str]): Semana ISO del evento (ej: '2025-W51')
- `event_date_from` (Optional[date]): Fecha inicio del evento
- `event_date_to` (Optional[date]): Fecha fin del evento
- `include_weekly` (bool, default=True): Incluir datos semanales

**Descripción:** Obtiene reporte detallado de una corrida de ingesta.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/identity/runs/1/report?group_by=week&include_weekly=true"
```

**Vista SQL:**
- Consulta `ops.ingestion_runs` por `run_id`
- Consulta `canon.identity_links` filtrado por `run_id`
- Consulta `canon.identity_unmatched` filtrado por `run_id`
- Agregaciones semanales con `date_trunc('week', snapshot_date)`

---

### `GET /api/v1/identity/metrics/global`

**Módulo:** `app/api/v1/identity.py`  
**Handler:** `get_global_metrics()`  
**Tags:** `["identity"]`  
**Response Schema:** `MetricsResponse` (`app/schemas/identity.py`)

**Query Parameters:**
- `mode` (str, default="summary"): Modo: 'summary', 'weekly', o 'breakdowns'
- `source_table` (Optional[str]): Filtrar por fuente
- `event_date_from` (Optional[date]): Fecha inicio del evento
- `event_date_to` (Optional[date]): Fecha fin del evento

**Descripción:** Obtiene métricas globales (histórico completo) sin filtrar por run_id.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/identity/metrics/global?mode=weekly&source_table=module_ct_scouting_daily"
```

**Vista SQL:**
- Consulta `canon.identity_links` y `canon.identity_unmatched` sin filtro de `run_id`
- Agregaciones semanales opcionales

---

### `GET /api/v1/identity/metrics/run/{run_id}`

**Módulo:** `app/api/v1/identity.py`  
**Handler:** `get_run_metrics()`  
**Tags:** `["identity"]`  
**Response Schema:** `MetricsResponse` (`app/schemas/identity.py`)

**Path Parameters:**
- `run_id` (int): ID de la corrida

**Query Parameters:**
- `mode` (str, default="summary"): Modo: 'summary', 'weekly', o 'breakdowns'
- `source_table` (Optional[str]): Filtrar por fuente
- `event_date_from` (Optional[date]): Fecha inicio del evento
- `event_date_to` (Optional[date]): Fecha fin del evento

**Descripción:** Obtiene métricas para un run específico.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/identity/metrics/run/1?mode=breakdowns"
```

**Vista SQL:**
- Consulta `canon.identity_links` y `canon.identity_unmatched` filtrado por `run_id`
- Agregaciones semanales y breakdowns opcionales

---

### `GET /api/v1/identity/metrics/window`

**Módulo:** `app/api/v1/identity.py`  
**Handler:** `get_window_metrics()`  
**Tags:** `["identity"]`  
**Response Schema:** `MetricsResponse` (`app/schemas/identity.py`)

**Query Parameters:**
- `from` (date, required): Fecha inicio de la ventana
- `to` (date, required): Fecha fin de la ventana
- `mode` (str, default="summary"): Modo: 'summary', 'weekly', o 'breakdowns'
- `source_table` (Optional[str]): Filtrar por fuente

**Descripción:** Obtiene métricas para una ventana de tiempo específica (sin filtrar por run_id).

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/identity/metrics/window?from=2025-01-01&to=2025-01-31&mode=weekly"
```

**Vista SQL:**
- Consulta `canon.identity_links` y `canon.identity_unmatched` filtrado por `snapshot_date` en ventana
- Agregaciones semanales opcionales

---

## Attribution

### `POST /api/v1/attribution/populate-events`

**Módulo:** `app/api/v1/attribution.py`  
**Handler:** `populate_events()`  
**Tags:** `["attribution"]`  
**Response Schema:** `dict` con `{"status": str, "stats": dict}`

**Body Schema:** `PopulateEventsRequest` (`app/schemas/attribution.py`)
- `source_tables` (Optional[List[str]]): Tablas fuente
- `date_from` (Optional[date]): Fecha inicio
- `date_to` (Optional[date]): Fecha fin

**Descripción:** Pobla eventos de atribución desde tablas fuente (scouting, cabinet, migrations).

**Ejemplo curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/attribution/populate-events" \
  -H "Content-Type: application/json" \
  -d '{"date_from": "2025-01-01", "date_to": "2025-01-31", "source_tables": ["module_ct_scouting_daily"]}'
```

**Vista SQL:**
- Consume servicio `LeadAttributionService.populate_events_from_scouting()`
- Inserta en `observational.lead_events`
- Consulta `public.module_ct_scouting_daily`, `public.module_ct_cabinet_leads`, `public.module_ct_migrations`

---

### `POST /api/v1/attribution/process-ledger`

**Módulo:** `app/api/v1/attribution.py`  
**Handler:** `process_ledger()`  
**Tags:** `["attribution"]`  
**Response Schema:** `dict` con `{"status": str, "stats": dict}`

**Body Schema:** `ProcessLedgerRequest` (`app/schemas/attribution.py`)
- `date_from` (Optional[date]): Fecha inicio
- `date_to` (Optional[date]): Fecha fin
- `source_tables` (Optional[List[str]]): Tablas fuente
- `person_keys` (Optional[List[UUID]]): Personas específicas

**Descripción:** Procesa el ledger de atribución de leads.

**Ejemplo curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/attribution/process-ledger" \
  -H "Content-Type: application/json" \
  -d '{"date_from": "2025-01-01", "date_to": "2025-01-31"}'
```

**Vista SQL:**
- Consume servicio `LeadAttributionService.process_ledger()`
- Consulta `observational.lead_events`
- Inserta/actualiza `observational.lead_ledger`

---

### `GET /api/v1/attribution/ledger/{person_key}`

**Módulo:** `app/api/v1/attribution.py`  
**Handler:** `get_ledger_entry()`  
**Tags:** `["attribution"]`  
**Response Schema:** `LeadLedger` (`app/schemas/attribution.py`)

**Path Parameters:**
- `person_key` (UUID): Clave única de la persona

**Descripción:** Obtiene entrada del ledger de atribución para una persona.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/attribution/ledger/123e4567-e89b-12d3-a456-426614174000"
```

**Vista SQL:**
- Consulta `observational.lead_ledger` filtrado por `person_key`

---

### `GET /api/v1/attribution/events`

**Módulo:** `app/api/v1/attribution.py`  
**Handler:** `list_events()`  
**Tags:** `["attribution"]`  
**Response Schema:** `List[LeadEvent]` (`app/schemas/attribution.py`)

**Query Parameters:**
- `person_key` (Optional[UUID]): Filtrar por person_key
- `source_table` (Optional[str]): Filtrar por source_table
- `scout_id` (Optional[int]): Filtrar por scout_id
- `date_from` (Optional[date]): Fecha inicio
- `date_to` (Optional[date]): Fecha fin
- `skip` (int, default=0): Offset
- `limit` (int, default=100, max=1000): Límite

**Descripción:** Lista eventos de atribución con filtros opcionales.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/attribution/events?scout_id=123&limit=50"
```

**Vista SQL:**
- Consulta `observational.lead_events` con filtros opcionales

---

### `GET /api/v1/attribution/stats`

**Módulo:** `app/api/v1/attribution.py`  
**Handler:** `get_stats()`  
**Tags:** `["attribution"]`  
**Response Schema:** `AttributionStats` (`app/schemas/attribution.py`)

**Descripción:** Obtiene estadísticas agregadas del sistema de atribución.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/attribution/stats"
```

**Vista SQL:**
- Consulta `observational.lead_events` (COUNT total, COUNT con person_key)
- Consulta `observational.lead_ledger` (COUNT total, COUNT por decision_status)

---

## Dashboard

### `GET /api/v1/dashboard/scout/summary`

**Módulo:** `app/api/v1/dashboard.py`  
**Handler:** `get_scout_summary()`  
**Tags:** `["dashboard"]`  
**Response Schema:** `ScoutSummaryResponse` (`app/schemas/dashboard.py`)

**Query Parameters:**
- `week_start` (Optional[date]): Fecha inicio de semana
- `week_end` (Optional[date]): Fecha fin de semana
- `scout_id` (Optional[int]): ID del scout
- `lead_origin` (Optional[str]): Origen del lead: 'cabinet' o 'migration'

**Descripción:** Obtiene resumen de liquidación scouts con totales, por semana y top scouts.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/scout/summary?week_start=2025-01-01&week_end=2025-01-31"
```

**Vista SQL:**
- `ops.v_scout_liquidation_open_items_payable_policy` (totales payable)
- `ops.v_scout_liquidation_open_items_enriched` (totales blocked, por semana)
- Agregaciones por semana con `date_trunc('week', payable_date)`

---

### `GET /api/v1/dashboard/scout/open_items`

**Módulo:** `app/api/v1/dashboard.py`  
**Handler:** `get_scout_open_items()`  
**Tags:** `["dashboard"]`  
**Response Schema:** `ScoutOpenItemsResponse` (`app/schemas/dashboard.py`)

**Query Parameters:**
- `week_start_monday` (Optional[date]): Fecha inicio de semana
- `scout_id` (Optional[int]): ID del scout
- `confidence` (str, default="policy"): Confidence: 'policy', 'high', 'medium', 'unknown'
- `limit` (int, default=100, max=1000): Límite
- `offset` (int, default=0): Offset

**Descripción:** Obtiene items abiertos de liquidación scouts con paginación.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/scout/open_items?confidence=policy&limit=50"
```

**Vista SQL:**
- `ops.v_scout_liquidation_open_items_payable_policy` (si confidence=policy)
- `ops.v_scout_liquidation_open_items_enriched` (si confidence=high/medium/unknown)
- Filtro por `attribution_confidence` cuando aplica

---

### `GET /api/v1/dashboard/yango/summary`

**Módulo:** `app/api/v1/dashboard.py`  
**Handler:** `get_yango_summary()`  
**Tags:** `["dashboard"]`  
**Response Schema:** `YangoSummaryResponse` (`app/schemas/dashboard.py`)

**Query Parameters:**
- `week_start` (Optional[date]): Fecha inicio de semana
- `week_end` (Optional[date]): Fecha fin de semana

**Descripción:** Obtiene resumen de cobranza Yango con totales y por semana.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/yango/summary?week_start=2025-01-01&week_end=2025-01-31"
```

**Vista SQL:**
- `ops.v_yango_receivable_payable` (totales y por semana)
- Agregaciones por `pay_week_start_monday`

---

### `GET /api/v1/dashboard/yango/receivable_items`

**Módulo:** `app/api/v1/dashboard.py`  
**Handler:** `get_yango_receivable_items()`  
**Tags:** `["dashboard"]`  
**Response Schema:** `YangoReceivableItemsResponse` (`app/schemas/dashboard.py`)

**Query Parameters:**
- `week_start_monday` (Optional[date]): Fecha inicio de semana
- `limit` (int, default=100, max=1000): Límite
- `offset` (int, default=0): Offset

**Descripción:** Obtiene items de cobranza Yango con paginación.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/dashboard/yango/receivable_items?week_start_monday=2025-01-06&limit=50"
```

**Vista SQL:**
- `ops.v_yango_receivable_payable_detail` (items detallados)

---

## Liquidation

### `GET /api/v1/liquidation/scout/preview`

**Módulo:** `app/api/v1/liquidation.py`  
**Handler:** `get_scout_preview()`  
**Tags:** `["liquidation"]`  
**Response Schema:** `ScoutPreviewResponse` (`app/schemas/liquidation.py`)

**Query Parameters:**
- `scout_id` (int, required): ID del scout
- `cutoff_date` (date, required): Fecha de corte (YYYY-MM-DD)

**Descripción:** Previsualiza items que serán marcados como pagados para un scout.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/liquidation/scout/preview?scout_id=123&cutoff_date=2025-01-31"
```

**Vista SQL:**
- `ops.v_scout_liquidation_open_items_payable_policy`
- Filtro: `acquisition_scout_id = :scout_id AND payable_date <= :cutoff_date`

---

### `POST /api/v1/liquidation/scout/mark_paid`

**Módulo:** `app/api/v1/liquidation.py`  
**Handler:** `mark_scout_paid()`  
**Tags:** `["liquidation"]`  
**Response Schema:** `ScoutMarkPaidResponse` (`app/schemas/liquidation.py`)

**Headers:**
- `X-Admin-Token` (required): Token de administrador

**Body Schema:** `ScoutMarkPaidRequest` (`app/schemas/liquidation.py`)
- `scout_id` (int): ID del scout
- `cutoff_date` (date): Fecha de corte
- `paid_by` (str): Usuario que marca como pagado
- `payment_ref` (Optional[str]): Referencia de pago
- `notes` (Optional[str]): Notas

**Descripción:** Marca items como pagados para un scout hasta una fecha de corte. Requiere token de administrador.

**Ejemplo curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/liquidation/scout/mark_paid" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: your-admin-token" \
  -d '{"scout_id": 123, "cutoff_date": "2025-01-31", "paid_by": "admin"}'
```

**Vista SQL:**
- SELECT desde `ops.v_scout_liquidation_open_items_payable_policy` (preview)
- INSERT en `ops.scout_liquidation_ledger` con `ON CONFLICT DO NOTHING`

---

## Ops

### `GET /api/v1/ops/health`

**Módulo:** `app/api/v1/ops.py`  
**Handler:** `ops_health()`  
**Tags:** `["ops"]`  
**Response Schema:** `dict` con `{"status": "ok", "module": "ops"}`

**Descripción:** Health check para el módulo de operaciones.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/ops/health"
```

**Vista SQL:** Ninguna (respuesta hardcoded)

---

## Payments

### `GET /api/v1/payments/eligibility`

**Módulo:** `app/api/v1/payments.py`  
**Handler:** `get_payment_eligibility()`  
**Tags:** `["payments"]`  
**Response Schema:** `PaymentEligibilityResponse` (`app/schemas/payments.py`)

**Query Parameters:**
- `origin_tag` (Optional[str]): Filtra por 'cabinet' o 'fleet_migration'
- `rule_scope` (Optional[str]): Filtra por 'scout' o 'partner'
- `is_payable` (Optional[bool]): Filtra por is_payable
- `scout_id` (Optional[int]): Filtra por scout_id
- `driver_id` (Optional[str]): Filtra por driver_id
- `payable_from` (Optional[date]): Filtra por payable_date >= payable_from
- `payable_to` (Optional[date]): Filtra por payable_date <= payable_to
- `limit` (int, default=200, max=1000): Límite
- `offset` (int, default=0): Offset
- `order_by` (OrderByField, default=payable_date): Campo para ordenar
- `order_dir` (OrderDirection, default=asc): Dirección del ordenamiento

**Descripción:** Consulta la vista ops.v_payment_calculation con filtros opcionales.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/payments/eligibility?is_payable=true&payable_from=2025-01-01&payable_to=2025-01-31&limit=50"
```

**Vista SQL:**
- `ops.v_payment_calculation` (vista materializada o view)
- Filtros dinámicos en WHERE
- Ordenamiento y paginación

---

## Yango Payments

**Nota:** Estos endpoints están bajo el prefijo `/api/v1/yango` pero duplican funcionalidad de `/api/v1/payments`. Verificar si están activos o deprecados.

### `GET /api/v1/yango/payments/reconciliation/summary`

**Módulo:** `app/api/v1/yango_payments.py`  
**Handler:** `get_reconciliation_summary()`  
**Tags:** `["yango"]`  
**Response Schema:** `YangoReconciliationSummaryResponse` (`app/schemas/payments.py`)

**Query Parameters:**
- `week_start` (Optional[date]): Filtra por semana (lunes)
- `milestone_value` (Optional[int]): Filtra por milestone (1, 5, 25)
- `mode` (Literal['real', 'assumed'], default='real'): Modo de cálculo
- `limit` (int, default=1000, max=10000): Límite

**Descripción:** Obtiene resumen agregado de reconciliación de pagos Yango por semana y milestone.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/yango/payments/reconciliation/summary?week_start=2025-01-06&milestone_value=1"
```

**Vista SQL:**
- `ops.v_yango_payments_claims_cabinet_14d` (agregaciones por semana y milestone)
- `ops.v_yango_payments_ledger_latest_enriched` (validación)

---

### `GET /api/v1/yango/payments/reconciliation/items`

**Módulo:** `app/api/v1/yango_payments.py`  
**Handler:** `get_reconciliation_items()`  
**Tags:** `["yango"]`  
**Response Schema:** `YangoReconciliationItemsResponse` (`app/schemas/payments.py`)

**Query Parameters:**
- `week_start` (Optional[date]): Filtra por semana (lunes)
- `milestone_value` (Optional[int]): Filtra por milestone (1, 5, 25)
- `driver_id` (Optional[str]): Filtra por driver_id
- `paid_status` (Optional[str]): Filtra por paid_status
- `limit` (int, default=1000, max=10000): Límite
- `offset` (int, default=0): Offset

**Descripción:** Obtiene items detallados de reconciliación de pagos Yango.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/yango/payments/reconciliation/items?week_start=2025-01-06&limit=50"
```

**Vista SQL:**
- `ops.v_yango_payments_claims_cabinet_14d` (items detallados)
- COUNT para total, SELECT con paginación

---

### `GET /api/v1/yango/payments/reconciliation/ledger/unmatched`

**Módulo:** `app/api/v1/yango_payments.py`  
**Handler:** `get_ledger_unmatched()`  
**Tags:** `["yango"]`  
**Response Schema:** `YangoLedgerUnmatchedResponse` (`app/schemas/payments.py`)

**Query Parameters:**
- `is_paid` (Optional[bool]): Filtra por is_paid
- `driver_id` (Optional[str]): Filtra por driver_id
- `identity_status` (Optional[str]): Filtra por identity_status
- `limit` (int, default=1000, max=10000): Límite
- `offset` (int, default=0): Offset

**Descripción:** Obtiene registros del ledger que no tienen match contra claims.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/yango/payments/reconciliation/ledger/unmatched?is_paid=false&limit=50"
```

**Vista SQL:**
- `ops.v_yango_payments_ledger_latest_enriched` (alias `l`)
- NOT EXISTS contra `ops.v_yango_payments_claims_cabinet_14d` (alias `c`)

---

### `GET /api/v1/yango/payments/reconciliation/ledger/matched`

**Módulo:** `app/api/v1/yango_payments.py`  
**Handler:** `get_ledger_matched()`  
**Tags:** `["yango"]`  
**Response Schema:** `YangoLedgerUnmatchedResponse` (`app/schemas/payments.py`)

**Query Parameters:**
- `is_paid` (Optional[bool]): Filtra por is_paid
- `driver_id` (Optional[str]): Filtra por driver_id
- `limit` (int, default=1000, max=10000): Límite
- `offset` (int, default=0): Offset

**Descripción:** Obtiene registros del ledger que tienen match contra claims.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/yango/payments/reconciliation/ledger/matched?is_paid=true&limit=50"
```

**Vista SQL:**
- `ops.v_yango_payments_ledger_latest_enriched` (alias `l`)
- EXISTS contra `ops.v_yango_payments_claims_cabinet_14d` (alias `c`)

---

### `GET /api/v1/yango/payments/reconciliation/driver/{driver_id}`

**Módulo:** `app/api/v1/yango_payments.py`  
**Handler:** `get_driver_detail()`  
**Tags:** `["yango"]`  
**Response Schema:** `YangoDriverDetailResponse` (`app/schemas/payments.py`)

**Path Parameters:**
- `driver_id` (str): ID del conductor

**Descripción:** Obtiene detalle de claims y pagos para un conductor específico.

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/yango/payments/reconciliation/driver/DRIVER123"
```

**Vista SQL:**
- `ops.v_yango_payments_claims_cabinet_14d` (claims del conductor)
- Agregaciones para resumen (total_expected, total_paid, counts)

---

## Resumen de Vistas SQL Utilizadas

### Schema `ops`
- `ops.v_scout_liquidation_open_items_payable_policy`
- `ops.v_scout_liquidation_open_items_enriched`
- `ops.v_yango_receivable_payable`
- `ops.v_yango_receivable_payable_detail`
- `ops.v_payment_calculation`
- `ops.v_yango_payments_claims_cabinet_14d`
- `ops.v_yango_payments_ledger_latest_enriched`

### Schema `canon`
- `canon.identity_registry`
- `canon.identity_links`
- `canon.identity_unmatched`
- `canon.drivers_index`

### Schema `observational`
- `observational.lead_events`
- `observational.lead_ledger`
- `observational.scouting_match_candidates`

### Schema `public`
- `public.module_ct_scouting_daily`
- `public.module_ct_cabinet_leads`
- `public.module_ct_migrations`
- `public.drivers`

### Schema `ops` (tablas)
- `ops.ingestion_runs`
- `ops.scout_liquidation_ledger`

---

## Comandos para Validar

### 1. Verificar que el servidor está corriendo
```bash
curl -X GET "http://localhost:8000/health"
```

### 2. Listar todos los endpoints disponibles (FastAPI docs)
```bash
# Abrir en navegador
http://localhost:8000/docs
```

### 3. Verificar endpoints por módulo
```bash
# Health
curl -X GET "http://localhost:8000/health"

# Identity - Stats
curl -X GET "http://localhost:8000/api/v1/identity/stats"

# Attribution - Stats
curl -X GET "http://localhost:8000/api/v1/attribution/stats"

# Dashboard - Scout Summary
curl -X GET "http://localhost:8000/api/v1/dashboard/scout/summary"

# Payments - Eligibility (sin filtros)
curl -X GET "http://localhost:8000/api/v1/payments/eligibility?limit=10"
```

### 4. Validar estructura de respuestas
```bash
# Verificar que las respuestas tienen el schema correcto
curl -X GET "http://localhost:8000/api/v1/identity/stats" | jq .

# Verificar paginación
curl -X GET "http://localhost:8000/api/v1/identity/persons?limit=10&skip=0" | jq '. | length'
```

### 5. Validar endpoints con autenticación
```bash
# Liquidation requiere X-Admin-Token
curl -X POST "http://localhost:8000/api/v1/liquidation/scout/mark_paid" \
  -H "X-Admin-Token: test-token" \
  -H "Content-Type: application/json" \
  -d '{"scout_id": 1, "cutoff_date": "2025-01-31", "paid_by": "test"}'
```

---

## Notas Importantes

1. **Endpoints duplicados:** Los endpoints en `yango_payments.py` parecen duplicar funcionalidad de `payments.py`. Verificar si están activos o deprecados.

2. **Background Tasks:** Algunos endpoints (`/identity/run`, `/identity/drivers-index/refresh`) ejecutan tareas en background. La respuesta inmediata es el objeto `IngestionRun`, pero el procesamiento continúa asíncronamente.

3. **Autenticación:** Solo el endpoint `/liquidation/scout/mark_paid` requiere header `X-Admin-Token`. El resto de endpoints son públicos (en desarrollo).

4. **Paginación:** La mayoría de endpoints de listado soportan `skip`/`offset` y `limit`. Los límites máximos varían (100-10000 según el endpoint).

5. **Filtros de fecha:** Muchos endpoints aceptan filtros de fecha. Usar formato ISO: `YYYY-MM-DD`.

6. **UUIDs:** Los `person_key` son UUIDs. Usar formato estándar: `123e4567-e89b-12d3-a456-426614174000`.

---

## Archivos Modificados

- `docs/contracts/backend_endpoints_inventory.md` (creado)

---

## Comandos para Validar

```bash
# 1. Verificar que el archivo fue creado
ls -la docs/contracts/backend_endpoints_inventory.md

# 2. Verificar formato markdown
cat docs/contracts/backend_endpoints_inventory.md | head -50

# 3. Contar endpoints documentados
grep -c "^### \`" docs/contracts/backend_endpoints_inventory.md

# 4. Verificar que todos los módulos están cubiertos
grep "^## " docs/contracts/backend_endpoints_inventory.md
```



