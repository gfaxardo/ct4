# Data Contract - Fase 1 Identidad

Este documento define el mapeo explícito entre columnas reales de las tablas RAW y los campos lógicos estándar usados por el sistema de matching.

**Fecha de introspección**: Generado automáticamente desde `schema_introspection.json`

## Campos Lógicos Estándar

- `source_pk`: Identificador único del registro en la fuente RAW
- `snapshot_date`: Fecha de corte/snapshot del evento
- `park_id`: ID del parque (si aplica)
- `phone_raw`: Teléfono en formato crudo
- `license_raw`: Licencia en formato crudo
- `name_raw`: Nombre completo en formato crudo
- `plate_raw`: Placa en formato crudo
- `brand_raw`: Marca del vehículo en formato crudo
- `model_raw`: Modelo del vehículo en formato crudo
- `created_at_raw`: Timestamp de creación del registro
- `scout_id`: ID del scout (metadata, NO matching)
- `acquisition_method`: Método de adquisición (metadata, NO matching)

## 1. public.module_ct_cabinet_leads

### Mapeo de Columnas

| Campo Lógico | Columna Real | Notas |
|-------------|--------------|-------|
| `source_pk` | `external_id` | Si es NULL, usar `id` como fallback |
| `snapshot_date` | `lead_created_at::date` | Convertir timestamp a date |
| `park_id` | **NO DISPONIBLE** | No existe columna park_id en esta tabla |
| `phone_raw` | `park_phone` | Disponible |
| `license_raw` | **NO DISPONIBLE** | No existe columna de licencia |
| `name_raw` | `CONCAT(first_name, ' ', COALESCE(middle_name, ''), ' ', last_name)` | Concatenar partes del nombre |
| `plate_raw` | `asset_plate_number` | Disponible |
| `brand_raw` | **NO DISPONIBLE** | No existe asset_brand, solo asset_model |
| `model_raw` | `asset_model` | Disponible |
| `created_at_raw` | `lead_created_at` | Disponible (timestamp) |

### Columnas Disponibles (no usadas en matching)
- `id`, `activation_city`, `active_*`, `asset_color`, `last_active_date`, `park_name`, `status`, `tariff`, `target_city`, `created_at`

### Notas
- Si `external_id` es NULL, se debe usar `id` como `source_pk`
- `park_id` no está disponible, se debe manejar como NULL
- `brand_raw` no está disponible (solo `asset_model`)

## 2. public.module_ct_scouting_daily

### Mapeo de Columnas

| Campo Lógico | Columna Real | Notas |
|-------------|--------------|-------|
| `source_pk` | `md5(scout_id \|\| phone_norm \|\| license_norm \|\| registration_date)` | Generar canónico |
| `snapshot_date` | `registration_date` | Disponible (date) |
| `park_id` | **NO DISPONIBLE** | No existe columna park_id |
| `phone_raw` | `driver_phone` | Disponible |
| `license_raw` | `driver_license` | Disponible |
| `name_raw` | `driver_name` | Disponible |
| `plate_raw` | **NO DISPONIBLE** | No existe columna de placa |
| `brand_raw` | **NO DISPONIBLE** | No existe |
| `model_raw` | **NO DISPONIBLE** | No existe |
| `created_at_raw` | `created_at` | Disponible (timestamp) |
| `scout_id` | `scout_id` | Metadata (NO matching) |
| `acquisition_method` | `acquisition_method` | Metadata (NO matching) |

### Columnas Disponibles (no usadas en matching)
- `id`, `updated_at`

### Notas
- `source_pk` se genera canónicamente usando `md5(scout_id|phone_norm|license_norm|snapshot_date)`
- `scout_id` y `acquisition_method` son metadata y NO participan en matching
- `park_id` no está disponible

## 3. public.drivers

### Mapeo de Columnas

| Campo Lógico | Columna Real | Preferencia | Notas |
|-------------|--------------|-------------|-------|
| `source_pk` | `driver_id` | Único | Disponible |
| `snapshot_date` | Parámetro de corrida | - | No existe columna run_date, usar parámetro |
| `park_id` | `park_id` | Único | Disponible |
| `phone_raw` | `phone` | Único | Disponible |
| `license_raw` | `license_normalized_number` > `license_number` | Preferir normalized | Si normalized existe, usarlo; sino license_number |
| `name_raw` | `full_name` > `CONCAT(first_name, ' ', COALESCE(middle_name, ''), ' ', last_name)` | Preferir full_name | Si full_name existe, usarlo; sino concatenar |
| `plate_raw` | `car_normalized_number` > `car_number` | Preferir normalized | Si normalized existe, usarlo; sino car_number |
| `brand_raw` | `car_brand` | Único | Disponible |
| `model_raw` | `car_model` | Único | Disponible |
| `created_at_raw` | `created_at` | Único | Disponible (timestamp) |
| `hire_date` | `hire_date` | Único | Disponible (date, para filtros de ventana) |

### Columnas Disponibles (no usadas en matching)
- `id`, `first_name`, `last_name`, `middle_name`, `rating`, `work_status`, `fire_date`, `is_selfemployed`, `car_id`, `car_color`, `car_callsign`, `license_country`, `license_expiration_date`, `license_issue_date`, `account_*`, `current_status`, `status_updated_at`, `document_type`, `document_number`, `updated_at`, `active`

### Notas
- `snapshot_date` no existe como columna, se pasa como parámetro a la corrida
- Para `license_raw`: preferir `license_normalized_number`, fallback a `license_number`
- Para `plate_raw`: preferir `car_normalized_number`, fallback a `car_number`
- Para `name_raw`: preferir `full_name`, fallback a concatenación de partes
- `hire_date` existe y se usa para ventanas de tiempo en reglas débiles (R3/R4)

## Manejo de Campos No Disponibles

Cuando un campo lógico no tiene columna correspondiente:

1. El mapeo retorna `None`
2. El código debe detectar `MISSING_KEYS` y registrar en `identity_unmatched` con `reason_code=MISSING_KEYS`
3. NO se debe lanzar error ni crash, solo registrar como unmatched

## Validación

- Todas las columnas referenciadas en este contrato fueron verificadas mediante introspección SQL
- Si una columna esperada no existe, está marcada como **NO DISPONIBLE**
- El código debe validar existencia antes de usar columnas opcionales




