# Explicación: ¿Cómo y por qué se crea `observational.lead_events`?

## ¿Qué es `lead_events`?

`observational.lead_events` es una **tabla** (no una vista) que almacena eventos de leads (registros de conductores) de diferentes fuentes. Es el punto central de entrada para el sistema de atribución de leads y métricas de conversión.

## ¿Por qué se crea?

### Propósito Principal

1. **Unificar eventos de leads de múltiples fuentes:**
   - `module_ct_cabinet_leads` (registros desde Yango)
   - `module_ct_scouting_daily` (registros desde scouts)
   - `module_ct_migrations` (migraciones de flota)

2. **Proporcionar `lead_date` (fecha del lead) para:**
   - `observational.v_conversion_metrics` (métricas de conversión)
   - `ops.v_payment_calculation` (cálculo de pagos)
   - `ops.v_cabinet_financial_14d` (vista financiera)

3. **Sistema de atribución:**
   - Determinar qué scout o fuente generó cada lead
   - Calcular métricas de conversión por origen
   - Soporte para el sistema de pagos a scouts y partners

## ¿Cómo se crea?

### 1. Migración de Base de Datos

La tabla se crea mediante la migración de Alembic:

**Archivo:** `backend/alembic/versions/010_create_lead_attribution_system.py`

**Estructura de la tabla:**
```sql
CREATE TABLE observational.lead_events (
    id SERIAL PRIMARY KEY,
    source_table VARCHAR NOT NULL,        -- Ej: 'module_ct_cabinet_leads'
    source_pk VARCHAR NOT NULL,            -- PK del registro en la fuente
    event_date DATE NOT NULL,             -- Fecha del lead (usado como lead_date)
    person_key UUID,                      -- FK a canon.identity_registry
    scout_id INTEGER,                     -- ID del scout (si aplica)
    payload_json JSONB,                   -- Datos adicionales del evento
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (source_table, source_pk)
);
```

### 2. Poblado de la Tabla

La tabla se alimenta mediante el servicio `LeadAttributionService`:

**Archivo:** `backend/app/services/lead_attribution.py`

**Métodos principales:**
- `populate_events_from_cabinet_leads()`: Inserta eventos desde `module_ct_cabinet_leads`
- `populate_events_from_scouting()`: Inserta eventos desde `module_ct_scouting_daily`
- `populate_events_from_migrations()`: Inserta eventos desde `module_ct_migrations`

### 3. Proceso de Inserción

**Para `module_ct_cabinet_leads`:**
```python
event = LeadEvent(
    source_table="module_ct_cabinet_leads",
    source_pk=external_id or str(id),
    event_date=lead_created_at.date(),  # ← Este es el lead_date
    person_key=person_key,  # Se obtiene del matching de identidad
    scout_id=None,  # Cabinet no tiene scout
    payload_json={...}
)
```

**Para `module_ct_scouting_daily`:**
```python
event = LeadEvent(
    source_table="module_ct_scouting_daily",
    source_pk=scouting_pk,
    event_date=registration_date,  # ← Este es el lead_date
    person_key=person_key,
    scout_id=scout_id,
    payload_json={...}
)
```

## Cadena de Dependencias

```
1. Tablas RAW (public.module_ct_*)
   ↓ (proceso de ingesta/matching)
2. observational.lead_events (tabla)
   ↓ (event_date = lead_date)
3. observational.v_conversion_metrics (vista)
   ↓ (lead_date desde lead_events)
4. ops.v_payment_calculation (vista)
   ↓ (lead_date desde v_conversion_metrics)
5. ops.v_cabinet_financial_14d (vista final)
```

## ¿Cuándo se actualiza?

### Proceso Automático

La tabla se actualiza cuando se ejecuta:

1. **Proceso de Ingesta de Identidad:**
   - Endpoint: `POST /api/v1/identity/run`
   - Procesa `module_ct_cabinet_leads` y `module_ct_scouting_daily`
   - Crea eventos en `lead_events` para cada registro nuevo

2. **Proceso de Atribución de Leads:**
   - Endpoint: `POST /api/v1/attribution/populate-events`
   - Pobla `lead_events` desde las tablas fuente
   - Asigna `person_key` mediante matching de identidad

### Proceso Manual

También se puede poblar manualmente mediante scripts SQL:

**Ejemplo:** `backend/sql/observational/ingest_module_ct_migrations_to_lead_events.sql`
```sql
INSERT INTO observational.lead_events (...)
SELECT ... FROM public.module_ct_migrations
WHERE NOT EXISTS (...);
```

## Problema Actual: Datos hasta 14/12/2025

### Diagnóstico

Si `lead_events` solo tiene datos hasta el 14/12/2025, significa que:

1. **No se han ejecutado procesos de ingesta después del 14/12:**
   - El proceso de ingesta de identidad no se ha ejecutado
   - O se ejecutó pero no procesó leads nuevos

2. **No hay nuevos leads en las tablas fuente:**
   - `module_ct_cabinet_leads` no tiene registros nuevos
   - `module_ct_scouting_daily` no tiene registros nuevos

### Solución

1. **Verificar si hay nuevos leads:**
   ```sql
   SELECT MAX(lead_created_at) FROM public.module_ct_cabinet_leads;
   SELECT MAX(registration_date) FROM public.module_ct_scouting_daily;
   ```

2. **Ejecutar proceso de ingesta:**
   ```bash
   POST /api/v1/identity/run?date_from=2025-12-15&date_to=2026-01-07
   ```

3. **O ejecutar proceso de atribución:**
   ```bash
   POST /api/v1/attribution/populate-events
   ```

## Resumen

- **¿Qué es?** Tabla que almacena eventos de leads de múltiples fuentes
- **¿Por qué existe?** Para unificar leads y proporcionar `lead_date` a las vistas de métricas y pagos
- **¿Cómo se crea?** Mediante migración de Alembic (010_create_lead_attribution_system)
- **¿Cómo se alimenta?** Mediante procesos de ingesta y atribución que insertan eventos desde tablas RAW
- **¿Cuándo se actualiza?** Cuando se ejecutan procesos de ingesta o atribución para leads nuevos


