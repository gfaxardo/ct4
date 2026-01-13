# Lineage: Claims Gap 14D

**Fecha:** 2026-01-13

---

## Flujo de Datos

```
public.module_ct_cabinet_leads (RAW)
    ↓
    lead_date_canonico = lead_created_at::date
    source_pk = COALESCE(external_id::text, id::text)
    ↓
canon.identity_links (C0)
    ↓
    person_key (si existe link)
    ↓
canon.identity_links (drivers)
    ↓
    driver_id (si existe link)
    ↓
public.summary_daily (RAW)
    ↓
    trips en ventana 14d [lead_date_canonico, lead_date_canonico + 14 days)
    ↓
ops.v_cabinet_claims_expected_14d (FUENTE DE VERDAD)
    ↓
    claim_expected = milestone_reached AND driver_id NOT NULL AND person_key NOT NULL
    ↓
canon.claims_yango_cabinet_14d (TABLA FÍSICA)
    ↓
    claim_exists = EXISTS (person_key, lead_date, milestone)
    ↓
ops.v_cabinet_claims_gap_14d (GAP VIEW)
    ↓
    gap_reason = 'CLAIM_NOT_GENERATED' si expected=true y exists=false
```

---

## Tablas y Vistas

### RAW Tables

1. **public.module_ct_cabinet_leads**
   - Campo clave: `lead_created_at` (timestamp)
   - Campo clave: `external_id`, `id` (para source_pk)

2. **public.summary_daily**
   - Campo clave: `driver_id`, `date_file` (DD-MM-YYYY), `count_orders_completed`

### Canonical Tables (C0)

1. **canon.identity_links**
   - `source_table = 'module_ct_cabinet_leads'`
   - `source_pk = COALESCE(external_id::text, id::text)`
   - `person_key` (UUID)

2. **canon.identity_links** (drivers)
   - `source_table = 'drivers'`
   - `source_pk = driver_id`
   - `person_key` (mismo que lead)

3. **canon.claims_yango_cabinet_14d** (TABLA FÍSICA)
   - `person_key`, `lead_date`, `milestone` (unique constraint)
   - `status` (expected, generated, paid, rejected, expired)
   - `amount_expected`, `paid_at`, `generated_at`

### Operational Views

1. **ops.v_cabinet_claims_expected_14d** (FUENTE DE VERDAD)
   - Calcula qué claims DEBEN existir
   - Grano: (lead_source_pk, milestone)

2. **ops.v_cabinet_claims_gap_14d** (GAP VIEW)
   - Identifica gaps: expected=true pero exists=false
   - Grano: (lead_source_pk, milestone) donde hay gap

---

## Join Keys

1. **lead → identity:**
   - `canon.identity_links.source_table = 'module_ct_cabinet_leads'`
   - `canon.identity_links.source_pk = COALESCE(external_id::text, id::text)`

2. **identity → driver:**
   - `canon.identity_links.person_key = person_key`
   - `canon.identity_links.source_table = 'drivers'`
   - `canon.identity_links.source_pk = driver_id`

3. **driver → trips:**
   - `public.summary_daily.driver_id = driver_id`
   - `public.summary_daily.prod_date >= lead_date_canonico`
   - `public.summary_daily.prod_date < lead_date_canonico + 14 days`

4. **expected → claims:**
   - `canon.claims_yango_cabinet_14d.person_key::text = expected.person_key`
   - `canon.claims_yango_cabinet_14d.lead_date = expected.lead_date_canonico`
   - `canon.claims_yango_cabinet_14d.milestone = expected.milestone`

---

## Filtros por Fecha

- **lead_date_canonico:** `lead_created_at::date` (fecha cero operativa)
- **Ventana 14d:** `[lead_date_canonico, lead_date_canonico + INTERVAL '14 days')`
- **week_start:** `DATE_TRUNC('week', lead_date_canonico)::date` (lunes ISO)

---

## Orden Canónico

- **Siempre:** `week_start DESC, lead_date_canonico DESC, milestone DESC`
