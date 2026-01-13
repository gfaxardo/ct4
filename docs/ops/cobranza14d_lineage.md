# Lineage: Cobranza Yango Cabinet 14d

**Fecha:** 2026-01-XX  
**Endpoint:** `GET /api/v1/ops/payments/cabinet-financial-14d`

---

## Endpoint Backend

**Archivo:** `backend/app/api/v1/ops_payments.py`  
**Función:** `get_cabinet_financial_14d` (línea 309)

**Parámetros:**
- `only_with_debt`: bool (filtra `amount_due_yango > 0`)
- `min_debt`: float (filtra `amount_due_yango >= min_debt`)
- `reached_milestone`: str ('m1', 'm5', 'm25')
- `scout_id`: int
- `week_start`: date (filtra por semana ISO)
- `limit`: int (default: 200, max: 1000)
- `offset`: int (paginación)
- `include_summary`: bool
- `use_materialized`: bool

**Orden actual:** `ORDER BY week_start DESC NULLS LAST, lead_date DESC NULLS LAST, driver_id`

---

## Vista SQL Base

**Vista principal:** `ops.v_cabinet_financial_14d`

**Tipo:** DRIVER-FIRST (1 fila por `driver_id`)

**Archivo:** `backend/sql/ops/v_cabinet_financial_14d.sql`

### Estructura

```
observational.v_conversion_metrics (cabinet)
    ↓ driver_id, lead_date, first_connection_date
ops.v_payment_calculation (cabinet)
    ↓ driver_id, lead_date (fallback)
all_drivers_base (UNION)
    ↓ driver_id, lead_date
public.summary_daily
    ↓ driver_id, prod_date, count_orders_completed
trips_14d (ventana 14d desde lead_date)
    ↓ total_trips_14d
milestones_14d
    ↓ reached_m1_14d, reached_m5_14d, reached_m25_14d
    ↓ expected_amount_m1/m5/m25, expected_total_yango
ops.v_claims_payment_status_cabinet
    ↓ claim_m1/m5/m25_exists, claim_m1/m5/m25_paid
    ↓ paid_amount_m1/m5/m25, total_paid_yango
ops.v_cabinet_financial_14d (FINAL)
    ↓ driver_id, lead_date, week_start, ...
    ↓ amount_due_yango = expected_total_yango - total_paid_yango
```

### Join Keys

- `driver_id`: clave principal (1 fila por driver)
- `lead_date`: desde `v_conversion_metrics` o `v_payment_calculation`
- `week_start`: `DATE_TRUNC('week', lead_date)::date`

### Filtros por Fecha

- **Ventana 14d:** `[lead_date, lead_date + INTERVAL '14 days')`
- **Viajes:** `summary_daily.prod_date >= lead_date AND prod_date < lead_date + INTERVAL '14 days'`
- **Milestones:** Solo si `total_trips_14d >= threshold` dentro de ventana 14d

### Limitaciones (DRIVER-FIRST)

- ❌ **Excluye leads sin driver_id:** Si un lead no tiene `person_key` → `driver_id`, NO aparece en la vista
- ❌ **No muestra leads en limbo:** Leads que no pasaron matching no aparecen
- ❌ **No muestra etapa exacta:** No indica si falta identity, driver, trips, o claims

---

## Tablas Fuente

### 1. `public.module_ct_cabinet_leads` (RAW)

**Campos clave:**
- `id`: integer (PK)
- `external_id`: varchar (source_pk canónico)
- `lead_created_at`: timestamp (anchor para lead_date)
- `park_phone`: varchar (para matching R1)
- `first_name`, `middle_name`, `last_name`: varchar (para matching R3/R4)
- `asset_plate_number`: varchar (para matching R3)

**source_pk canónico:** `COALESCE(external_id::text, id::text)`

### 2. `canon.identity_links`

**Campos clave:**
- `source_table`: varchar ('module_ct_cabinet_leads')
- `source_pk`: varchar (debe coincidir con source_pk canónico)
- `person_key`: uuid (FK a `canon.identity_registry`)
- `linked_at`: timestamp

**Join:** `il.source_table = 'module_ct_cabinet_leads' AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)`

### 3. `public.drivers`

**Campos clave:**
- `driver_id`: varchar (PK)
- `full_name`: varchar
- `phone`: varchar
- `license_number`: varchar
- `car_number`: varchar (placa)

**Join a identity:** `canon.identity_links` con `source_table='drivers'` y `source_pk=driver_id`

### 4. `observational.v_conversion_metrics`

**Campos clave:**
- `person_key`: uuid
- `origin_tag`: varchar ('cabinet')
- `lead_date`: date
- `driver_id`: varchar (resuelto desde `identity_links`)

**Filtro:** `origin_tag = 'cabinet' AND driver_id IS NOT NULL AND lead_date IS NOT NULL`

### 5. `public.summary_daily`

**Campos clave:**
- `driver_id`: varchar
- `date_file`: varchar (formato 'DD-MM-YYYY')
- `count_orders_completed`: integer

**Normalización:** `to_date(date_file, 'DD-MM-YYYY') AS prod_date`

### 6. `ops.v_claims_payment_status_cabinet`

**Campos clave:**
- `driver_id`: varchar
- `milestone_value`: integer (1, 5, 25)
- `lead_date`: date
- `paid_flag`: bool
- `expected_amount`: numeric

**Filtro:** Ya está filtrado para cabinet (no necesita `origin_tag`)

---

## Flujo de Datos

### Flujo Normal (Lead → Driver → Cobranza)

```
1. module_ct_cabinet_leads (lead_created_at)
   ↓ populate_events_from_cabinet
2. observational.lead_events (event_date, person_key=NULL)
   ↓ run_ingestion (matching)
3. canon.identity_links (person_key, source_pk='module_ct_cabinet_leads')
   ↓ resolver driver_id
4. canon.identity_links (person_key, source_pk='drivers' → driver_id)
   ↓
5. observational.v_conversion_metrics (lead_date, driver_id)
   ↓
6. ops.v_cabinet_financial_14d (driver_id, lead_date, milestones, claims)
```

### Puntos de Ruptura

1. **NO_IDENTITY:** Lead no tiene `identity_link` (no pasó matching)
2. **NO_DRIVER:** Lead tiene `person_key` pero no tiene `identity_link` a `drivers`
3. **NO_TRIPS_14D:** Driver no tiene viajes en ventana 14d
4. **TRIPS_NO_CLAIM:** Driver alcanzó milestones pero no tiene claims

---

## Frontend

**Archivo:** `frontend/app/pagos/cobranza-yango/page.tsx`

**API Client:** `frontend/lib/api.ts` → `getCabinetFinancial14d`

**Orden actual:** No especificado explícitamente (usa orden del backend)

**Filtros:** Implementados en frontend (debt, milestone, week_start)

---

## Materialized Views

**Prioridad de selección:**
1. `ops.mv_yango_cabinet_cobranza_enriched_14d` (si existe)
2. `ops.mv_cabinet_financial_14d` (si existe)
3. `ops.v_cabinet_financial_14d` (fallback)

---

## Notas

- La vista actual es **DRIVER-FIRST**, lo que excluye leads sin driver_id
- No hay vista **LEAD-FIRST** que muestre todos los leads (incluyendo limbo)
- El orden semanal ya está implementado (`week_start DESC, lead_date DESC`)
- Falta módulo de "Leads en Limbo" en UI
