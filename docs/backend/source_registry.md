# Source Registry - Registry Canónico de Fuentes

## Objetivo

Mantener un registry centralizado y canónico de todas las fuentes de datos (tablas, vistas, materialized views) con metadatos, dependencias, y flags de monitoreo. Permite overrides manuales para casos especiales.

## Tabla

**Schema:** `ops.source_registry`

**Archivo SQL:** `backend/sql/ops/source_registry.sql`

## Estructura

```sql
CREATE TABLE ops.source_registry (
    id bigserial PRIMARY KEY,
    schema_name text NOT NULL,
    object_name text NOT NULL,
    object_type text NOT NULL, -- 'table', 'view', 'matview'
    layer text, -- 'RAW', 'DERIVED', 'MV', 'CANON'
    role text, -- 'PRIMARY', 'SECONDARY'
    criticality text, -- 'critical', 'important', 'normal'
    should_monitor boolean,
    is_expected boolean, -- override manual
    is_critical boolean, -- override manual
    health_enabled boolean, -- override manual
    description text,
    usage_context text, -- 'endpoint', 'script', 'both', null
    refresh_schedule text, -- para MVs
    depends_on jsonb, -- array de {schema, name}
    discovered_at timestamptz,
    last_verified_at timestamptz,
    notes text, -- override manual
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    UNIQUE(schema_name, object_name)
);
```

## Campos

### Identificación
- `schema_name`: Schema donde reside el objeto
- `object_name`: Nombre del objeto
- `object_type`: Tipo: `table`, `view`, `matview`

### Clasificación
- `layer`: Capa del objeto
  - `RAW`: Schema `raw`
  - `CANON`: Schema `canon`
  - `MV`: Materialized view
  - `DERIVED`: Vista o tabla en `ops`/`public` (default)

- `role`: Rol del objeto
  - `PRIMARY`: RAW y CANON (fuentes primarias)
  - `SECONDARY`: MV y DERIVED (fuentes derivadas)

- `criticality`: Nivel de criticidad
  - `critical`: MV en `refresh_ops_mvs.py` o usado por endpoints UI-ready
  - `important`: Usado por endpoints
  - `normal`: Otros casos

### Monitoreo
- `should_monitor`: Si debe monitorearse (derivado de `criticality` y `health_enabled`)
- `health_enabled`: Override manual para habilitar/deshabilitar health checks
- `is_expected`: Override manual para marcar objetos esperados
- `is_critical`: Override manual para marcar objetos críticos

### Metadatos
- `description`: Descripción del objeto
- `usage_context`: Contexto de uso: `endpoint`, `script`, `both`, `null`
- `refresh_schedule`: Schedule de refresh para MVs (ej: "daily", "hourly")
- `depends_on`: JSONB array de dependencias `[{schema, name}, ...]`
- `notes`: Notas manuales

### Timestamps
- `discovered_at`: Primera vez que se descubrió (solo se setea si es NULL)
- `last_verified_at`: Última vez que se verificó (siempre se actualiza)
- `created_at`: Timestamp de creación
- `updated_at`: Timestamp de última actualización

## Población Automática

**Script:** `backend/scripts/populate_source_registry.py`

### Fuentes de Datos

1. **Discovery Objects** (`discovery_objects.csv`)
   - Todos los objetos encontrados en DB
   - Metadatos: `estimated_rows`, `size_mb`, `last_analyze`

2. **Discovery Dependencies** (`discovery_dependencies.csv`)
   - Dependencias entre objetos
   - Se almacena en `depends_on` como JSONB

3. **Discovery Usage** (`discovery_usage_backend.csv`)
   - Contexto de uso (endpoint/script)
   - Usado para inferir `criticality`

### Heurísticas Automáticas

#### Layer
```python
if schema_name == "raw":
    layer = "RAW"
elif schema_name == "canon":
    layer = "CANON"
elif object_type == "matview":
    layer = "MV"
else:
    layer = "DERIVED"
```

#### Role
```python
if layer in ("RAW", "CANON"):
    role = "PRIMARY"
else:  # MV, DERIVED
    role = "SECONDARY"
```

#### Criticality
```python
if full_name in CRITICAL_MVS:  # MVs en refresh_ops_mvs.py
    criticality = "critical"
elif (schema_name, object_name) in CRITICAL_OBJECTS_FROM_ENDPOINTS:
    criticality = "critical"
elif usage_context and "endpoint" in usage_context:
    criticality = "important"
else:
    criticality = "normal"
```

## Overrides Manuales

Las siguientes columnas **NO se pisan** si tienen valor (NOT NULL):
- `is_expected`
- `is_critical`
- `health_enabled`
- `notes`

Esto permite que los usuarios marquen manualmente objetos especiales sin que el script los sobrescriba.

### Ejemplo de Override

```sql
-- Marcar manualmente un objeto como crítico
UPDATE ops.source_registry
SET is_critical = true,
    notes = 'Objeto crítico para reportes mensuales'
WHERE schema_name = 'ops' AND object_name = 'v_monthly_report';

-- El script populate_source_registry.py NO pisará estos valores
```

## UPSERT Idempotente

El script `populate_source_registry.py` es idempotente:
- Puede ejecutarse múltiples veces sin duplicar registros
- Respeta overrides manuales
- Actualiza `last_verified_at` en cada ejecución
- Solo setea `discovered_at` la primera vez

### Lógica de UPSERT

```sql
INSERT INTO ops.source_registry (...)
VALUES (...)
ON CONFLICT (schema_name, object_name) DO UPDATE SET
    -- Campos que siempre se actualizan
    object_type = EXCLUDED.object_type,
    layer = EXCLUDED.layer,
    role = EXCLUDED.role,
    usage_context = EXCLUDED.usage_context,
    depends_on = EXCLUDED.depends_on,
    last_verified_at = EXCLUDED.last_verified_at,
    
    -- Campos que respetan overrides manuales
    criticality = CASE 
        WHEN ops.source_registry.is_critical IS NOT NULL 
        THEN ops.source_registry.criticality
        ELSE EXCLUDED.criticality
    END,
    should_monitor = CASE
        WHEN ops.source_registry.health_enabled IS NOT NULL
        THEN ops.source_registry.should_monitor
        ELSE EXCLUDED.should_monitor
    END,
    
    -- discovered_at solo se setea si es NULL
    discovered_at = COALESCE(ops.source_registry.discovered_at, EXCLUDED.discovered_at)
```

## Uso

### Poblar Registry

```bash
# 1. Ejecutar discovery scripts primero
python backend/scripts/discovery_objects.py
python backend/scripts/discovery_dependencies.py
python backend/scripts/discovery_usage_backend.py

# 2. Poblar registry
python backend/scripts/populate_source_registry.py
```

### Consultar Registry

```sql
-- Ver todos los objetos críticos
SELECT schema_name, object_name, criticality, usage_context
FROM ops.source_registry
WHERE criticality = 'critical'
ORDER BY schema_name, object_name;

-- Ver objetos con overrides manuales
SELECT schema_name, object_name, is_critical, health_enabled, notes
FROM ops.source_registry
WHERE is_critical IS NOT NULL
   OR health_enabled IS NOT NULL
   OR notes IS NOT NULL;

-- Ver dependencias de un objeto
SELECT schema_name, object_name, depends_on
FROM ops.source_registry
WHERE depends_on IS NOT NULL
  AND jsonb_array_length(depends_on) > 0;
```

### API Endpoint

```bash
# Consultar registry vía API
curl "http://localhost:8000/api/v1/ops/source-registry?limit=10&offset=0"

# Con filtros
curl "http://localhost:8000/api/v1/ops/source-registry?layer=RAW&criticality=critical&limit=50"
```

## Integración con Health Checks

El registry es usado por `ops.v_health_checks` para:
- Detectar objetos esperados que no existen (`expected_source_missing`)
- Detectar objetos usados pero no registrados (`unregistered_used_object`)
- Detectar objetos monitoreados no cubiertos (`monitored_not_in_health_views`)
- Detectar fuentes RAW stale que afectan MVs críticas (`raw_source_stale_affecting_critical`)

## Mantenimiento

### Agregar Nuevo Objeto Manualmente

```sql
INSERT INTO ops.source_registry (
    schema_name, object_name, object_type,
    layer, role, criticality, should_monitor,
    description, notes
)
VALUES (
    'ops', 'v_new_view', 'view',
    'DERIVED', 'SECONDARY', 'important', true,
    'Nueva vista para reportes', 'Agregada manualmente el 2025-01-27'
);
```

### Actualizar Override Manual

```sql
UPDATE ops.source_registry
SET is_critical = true,
    notes = 'Marcado como crítico por requerimiento de negocio'
WHERE schema_name = 'ops' AND object_name = 'v_important_view';
```

### Limpiar Override (permitir auto-población)

```sql
UPDATE ops.source_registry
SET is_critical = NULL,
    health_enabled = NULL,
    notes = NULL
WHERE schema_name = 'ops' AND object_name = 'v_view_to_reset';
```

## Validación

```bash
# Verificar que el registry tiene datos
psql -h 168.119.226.236 -p 5432 -U yego_user -d yego_integral \
  -c "SELECT count(*) FROM ops.source_registry;"

# Verificar objetos críticos
psql -h 168.119.226.236 -p 5432 -U yego_user -d yego_integral \
  -c "SELECT schema_name, object_name, criticality FROM ops.source_registry WHERE criticality = 'critical';"

# Verificar overrides manuales
psql -h 168.119.226.236 -p 5432 -U yego_user -d yego_integral \
  -c "SELECT schema_name, object_name, is_critical, health_enabled, notes FROM ops.source_registry WHERE is_critical IS NOT NULL OR health_enabled IS NOT NULL OR notes IS NOT NULL;"
```

## Notas Importantes

1. **Idempotencia**: El script puede ejecutarse múltiples veces sin efectos secundarios
2. **Overrides**: Los valores manuales en `is_expected`, `is_critical`, `health_enabled`, `notes` se respetan
3. **Dependencias**: Se actualizan automáticamente desde `discovery_dependencies.csv`
4. **Usage Context**: Se actualiza desde `discovery_usage_backend.csv`
5. **Timestamps**: `discovered_at` solo se setea la primera vez; `last_verified_at` siempre se actualiza



