# Identity Gap Mapping - Cabinet Leads

Este documento mapea las tablas y campos reales del repositorio para el módulo de Identity Gap & Recovery.

## Tabla de Leads Cabinet

- **Tabla**: `public.module_ct_cabinet_leads`
- **Campo ID**: `id` (PK integer)
- **Campo ID Externo**: `external_id` (VARCHAR, puede ser NULL)
- **Campo Lead Date**: `lead_created_at` (TIMESTAMP)
- **Campos para Matching**:
  - `park_phone` (VARCHAR) - teléfono
  - `first_name`, `middle_name`, `last_name` (VARCHAR) - nombre
  - `asset_plate_number` (VARCHAR) - placa
  - `asset_model` (VARCHAR) - modelo
- **Nota**: Si `external_id` es NULL, usar `id` como `source_pk`

## Vínculo a Person Key

- **Tabla de vínculo**: `canon.identity_links`
- **Campos**:
  - `source_table` = 'module_ct_cabinet_leads'
  - `source_pk` = `external_id` (o `id` si external_id es NULL)
  - `person_key` = UUID (FK a `canon.identity_registry.person_key`)

## Tabla de Origen Canónico

- **Tabla**: `canon.identity_origin`
- **Campos**:
  - `person_key` (PK, FK a `canon.identity_registry.person_key`)
  - `origin_tag` (ENUM: 'cabinet_lead', 'scout_registration', 'migration', 'legacy_external')
  - `origin_source_id` (VARCHAR) - debe ser el `external_id` o `id` del lead
  - `origin_created_at` (TIMESTAMPTZ)
  - `created_by` (implícito en `decided_by`)

## Tabla de Historial (Append-Only)

- **Tabla**: `canon.identity_origin_history`
- **Ya existe** en migration 013
- **Trigger**: Necesitamos crear trigger para INSERT automático en updates

## Tabla de Actividad (Trips)

- **Tabla**: `public.summary_daily`
- **Campos**:
  - `driver_id` (VARCHAR) - ID del driver
  - `date_file` (DATE) - fecha del viaje
  - `count_orders_completed` (INTEGER) - número de viajes completados
- **Vínculo a person_key**: A través de `canon.identity_links` donde `source_table='drivers'` y `source_pk=driver_id`

## Tabla de Jobs de Matching

- **Tabla nueva**: `ops.identity_matching_jobs`
- **Propósito**: Trackear reintentos de matching para leads sin identidad
- **Campos**:
  - `id` (BIGSERIAL PK)
  - `source_type` (TEXT CHECK = 'cabinet')
  - `source_id` (TEXT) - `external_id` o `id` del lead
  - `status` (TEXT CHECK in ('pending','matched','failed'))
  - `attempt_count` (INT default 0)
  - `last_attempt_at` (TIMESTAMP)
  - `matched_person_key` (UUID nullable)
  - `fail_reason` (TEXT nullable)
  - `created_at`, `updated_at` (TIMESTAMP)

## Estrategia de Matching

1. **Obtener person_key desde identity_links**:
   ```sql
   SELECT person_key 
   FROM canon.identity_links 
   WHERE source_table = 'module_ct_cabinet_leads' 
     AND source_pk = :lead_id
   ```

2. **Verificar si existe origin**:
   ```sql
   SELECT * 
   FROM canon.identity_origin 
   WHERE person_key = :person_key
   ```

3. **Obtener trips 14d**:
   ```sql
   SELECT COUNT(*) 
   FROM public.summary_daily sd
   JOIN canon.identity_links il ON il.source_pk = sd.driver_id AND il.source_table = 'drivers'
   WHERE il.person_key = :person_key
     AND sd.date_file BETWEEN :lead_date AND :lead_date + INTERVAL '14 days'
   ```

## Campos para Matching (en orden de prioridad)

1. **document_number**: No disponible en cabinet_leads
2. **phone_normalized**: Desde `park_phone` (normalizar)
3. **email**: No disponible en cabinet_leads
4. **nombre + fecha_nac**: Solo nombre disponible, fecha_nac no disponible

**Nota**: El matching debe usar el `MatchingEngine` existente que ya tiene lógica para phone, license, plate, etc.
