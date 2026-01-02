# Auditoría de Base de Datos: Identity Runs

## Resumen Ejecutivo

Esta auditoría documenta la estructura de la tabla que almacena las corridas de identidad, sus columnas relevantes para UI, y recomendaciones de índices y ordenamiento.

**Fecha de Auditoría:** 2024-01-XX  
**Tabla:** `ops.ingestion_runs`  
**Modelo SQLAlchemy:** `IngestionRun` (ubicado en `backend/app/models/ops.py`)

---

## 1. Identificación de la Tabla

### Nombre y Esquema

- **Nombre de tabla:** `ingestion_runs`
- **Esquema:** `ops`
- **Nombre completo:** `ops.ingestion_runs`

### Ubicación en Código

- **Modelo SQLAlchemy:** `backend/app/models/ops.py` (línea 44)
- **Schema Pydantic:** `backend/app/schemas/ingestion.py`
- **Migración inicial:** `backend/alembic/versions/001_create_canon_schema.py` (líneas 72-82)
- **Campos adicionales:** `backend/alembic/versions/004_add_ingestion_run_fields.py`

---

## 2. Columnas Relevantes para UI

### Columnas Principales

| Columna | Tipo | Nullable | Default | Descripción |
|---------|------|----------|---------|-------------|
| `id` | `Integer` | NO | `autoincrement` | **Primary Key**. Identificador único de la corrida. |
| `started_at` | `DateTime(timezone=True)` | NO | `now()` | **Timestamps**. Fecha/hora de inicio de la corrida. |
| `completed_at` | `DateTime(timezone=True)` | YES | `NULL` | **Timestamps**. Fecha/hora de finalización (NULL si aún está corriendo). |
| `status` | `Enum(RunStatus)` | NO | `RUNNING` | **Estado**. Valores: `RUNNING`, `COMPLETED`, `FAILED`. |
| `job_type` | `ENUM(jobtype)` | YES | `'identity_run'` | **Tipo de job**. Valores: `identity_run`, `drivers_index_refresh`. |
| `scope_date_from` | `Date` | YES | `NULL` | **Scope**. Fecha de inicio del rango de datos procesados. |
| `scope_date_to` | `Date` | YES | `NULL` | **Scope**. Fecha de fin del rango de datos procesados. |
| `incremental` | `Boolean` | YES | `true` | **Modo**. Indica si la corrida fue incremental o full. |
| `error_message` | `String` | YES | `NULL` | **Errores**. Mensaje de error si `status = FAILED`. |
| `stats` | `JSON` | YES | `NULL` | **Métricas**. Objeto JSON con estadísticas detalladas (ver estructura abajo). |

### Estructura del Campo `stats` (JSON)

El campo `stats` contiene un objeto JSON con la siguiente estructura cuando la corrida es de tipo `identity_run`:

```json
{
  "cabinet_leads": {
    "processed": 0,
    "matched": 0,
    "unmatched": 0,
    "skipped": 0
  },
  "scouting_daily": {
    "processed": 0,
    "matched": 0,
    "unmatched": 0,
    "skipped": 0
  },
  "timings": {
    "process_cabinet_leads": 0.0,
    "process_scouting_daily": 0.0,
    // ... otros tiempos de ejecución
  }
}
```

#### Campos Derivados para UI

Aunque no existen como columnas directas, estos valores pueden extraerse del campo `stats`:

- **Total procesados:** `stats.cabinet_leads.processed + stats.scouting_daily.processed`
- **Total matched:** `stats.cabinet_leads.matched + stats.scouting_daily.matched`
- **Total unmatched:** `stats.cabinet_leads.unmatched + stats.scouting_daily.unmatched`
- **Total skipped:** `stats.cabinet_leads.skipped + stats.scouting_daily.skipped`

**⚠️ Nota:** El frontend **NO debe recalcular** estos valores. Deben venir del backend en el endpoint que lista los runs.

### Duración de Ejecución

No existe una columna directa para la duración. Se calcula como:

- **Si `completed_at` es NULL:** `NOW() - started_at`
- **Si `completed_at` no es NULL:** `completed_at - started_at`

---

## 3. Índices Actuales

### Estado Actual

**No se encontraron índices explícitos** creados en las migraciones de Alembic para la tabla `ops.ingestion_runs`.

Solo existe el índice implícito en la Primary Key (`id`).

### Consultas Comunes en el Código

Analizando el código base, las consultas más comunes son:

1. **Búsqueda por ID:**
   ```python
   db.query(IngestionRun).filter(IngestionRun.id == run_id).first()
   ```
   ✅ Optimizado por PK.

2. **Última corrida completada (para modo incremental):**
   ```python
   db.query(IngestionRun).filter(
       IngestionRun.status == RunStatus.COMPLETED,
       IngestionRun.job_type == JobType.IDENTITY_RUN
   ).order_by(IngestionRun.completed_at.desc()).first()
   ```
   ⚠️ **Recomendado:** Índice compuesto en `(status, job_type, completed_at DESC)`.

3. **Listado de runs ordenados por fecha:**
   ```python
   db.query(IngestionRun).order_by(IngestionRun.id.desc()).limit(3).all()
   ```
   ⚠️ **Nota:** Actualmente ordena por `id DESC`, pero para UI se recomienda `started_at DESC`.

---

## 4. Recomendaciones de Índices

### Índice Recomendado #1: Búsqueda por Status y Job Type (para modo incremental)

```sql
CREATE INDEX idx_ingestion_runs_status_job_completed 
ON ops.ingestion_runs (status, job_type, completed_at DESC)
WHERE status = 'COMPLETED';
```

**Justificación:** Optimiza la consulta que busca la última corrida completada para determinar el punto de inicio en modo incremental.

**Impacto:** Bajo (tabla pequeña), pero mejora performance a medida que crece el historial de runs.

### Índice Recomendado #2: Listado por Fecha de Inicio (para UI)

```sql
CREATE INDEX idx_ingestion_runs_started_at_desc 
ON ops.ingestion_runs (started_at DESC);
```

**Justificación:** El orden recomendado para UI es mostrar las corridas más recientes primero. Este índice optimiza consultas del tipo:

```sql
SELECT * FROM ops.ingestion_runs 
WHERE job_type = 'identity_run'
ORDER BY started_at DESC 
LIMIT 50;
```

**Impacto:** Medio-Alto para páginas de listado frecuentemente consultadas.

### Índice Recomendado #3: Filtrado por Job Type y Status (para listados filtrados)

```sql
CREATE INDEX idx_ingestion_runs_job_type_status 
ON ops.ingestion_runs (job_type, status, started_at DESC);
```

**Justificación:** Permite filtrar rápidamente por tipo de job y estado, ordenando por fecha de inicio.

**Impacto:** Medio si se implementan filtros en la UI.

---

## 5. Orden Recomendado para UI

### Orden Principal

**`ORDER BY started_at DESC`**

Mostrar las corridas más recientes primero es el comportamiento estándar esperado por usuarios.

### Orden Alternativo

Si se necesita mostrar corridas en ejecución al principio:

```sql
ORDER BY 
  CASE WHEN status = 'RUNNING' THEN 0 ELSE 1 END,
  started_at DESC
```

Esto coloca primero las corridas en ejecución, luego las completadas/fallidas ordenadas por fecha descendente.

---

## 6. Consultas SQL de Ejemplo

### Consulta Básica para UI (Listado)

```sql
SELECT 
  id,
  started_at,
  completed_at,
  status,
  job_type,
  scope_date_from,
  scope_date_to,
  incremental,
  error_message,
  stats
FROM ops.ingestion_runs
WHERE job_type = 'identity_run'
ORDER BY started_at DESC
LIMIT 50;
```

### Consulta con Duración Calculada

```sql
SELECT 
  id,
  started_at,
  completed_at,
  status,
  CASE 
    WHEN completed_at IS NOT NULL 
    THEN EXTRACT(EPOCH FROM (completed_at - started_at))
    ELSE EXTRACT(EPOCH FROM (NOW() - started_at))
  END AS duration_seconds,
  stats
FROM ops.ingestion_runs
WHERE job_type = 'identity_run'
ORDER BY started_at DESC;
```

### Consulta con Total Procesados (Requiere Parsing JSON)

```sql
SELECT 
  id,
  started_at,
  completed_at,
  status,
  (stats->>'cabinet_leads')::json->>'processed' AS cabinet_processed,
  (stats->>'scouting_daily')::json->>'processed' AS scouting_processed,
  stats
FROM ops.ingestion_runs
WHERE job_type = 'identity_run'
ORDER BY started_at DESC;
```

**⚠️ Nota:** Se recomienda que estos cálculos se hagan en el backend (servicio/endpoint) y no en el frontend, para mantener la separación de responsabilidades.

---

## 7. Campos Faltantes / Sugerencias para Futuras Mejoras

### Campos que NO existen pero podrían ser útiles

1. **`total_persons`** (Integer): Contador total de personas procesadas (podría calcularse al finalizar).
2. **`total_processed`** (Integer): Contador total de registros procesados (suma de cabinet_leads + scouting_daily processed).
3. **`total_matched`** (Integer): Contador total de matches.
4. **`total_unmatched`** (Integer): Contador total de unmatched.
5. **`error_count`** (Integer): Número de errores no fatales durante la ejecución.
6. **`warnings`** (JSON): Array de warnings generados durante la ejecución.
7. **`duration_seconds`** (Integer): Duración calculada al finalizar (evita recalcular en UI).

**Estado Actual:** Estos valores están dentro del campo `stats` (JSON), pero no como columnas dedicadas.

**Recomendación:** Si se necesita indexar o filtrar por estos valores, considerar agregarlos como columnas separadas en una migración futura. De lo contrario, mantenerlos en `stats` es aceptable para flexibilidad.

---

## 8. Relación con Otras Tablas

### Tablas Relacionadas

- **`canon.identity_links`**: Contiene `run_id` (FK implícito) que referencia `ops.ingestion_runs.id`.
- **`canon.identity_unmatched`**: Contiene `run_id` (FK implícito) que referencia `ops.ingestion_runs.id`.
- **`ops.alerts`**: Contiene `run_id` (FK explícito) que referencia `ops.ingestion_runs.id`.

### Índices en Tablas Relacionadas

- `idx_identity_links_run_id` en `canon.identity_links` (migración 007)
- `idx_identity_unmatched_run_id` en `canon.identity_unmatched` (migración 007)

Estos índices optimizan las consultas que filtran links/unmatched por `run_id`.

---

## 9. Checklist para Implementación de UI

### Endpoint Requerido (según blueprint)

- [ ] **GET `/api/v1/identity/runs`** (Listado de corridas)
  - Parámetros: `job_type?`, `status?`, `limit?`, `offset?`
  - Response: Array de `IngestionRun` con campos calculados (totales, duración)

### Campos a Mostrar en UI

- [x] `id` (run_id)
- [x] `started_at` (fecha/hora de inicio)
- [x] `completed_at` (fecha/hora de finalización, o "En ejecución")
- [x] `status` (RUNNING, COMPLETED, FAILED - mostrar como Badge)
- [x] `scope_date_from` / `scope_date_to` (rango de fechas procesadas)
- [x] `incremental` (indicador de modo incremental vs full)
- [ ] Total procesados (derivado de `stats`)
- [ ] Total matched (derivado de `stats`)
- [ ] Total unmatched (derivado de `stats`)
- [ ] Duración (calculada: `completed_at - started_at` o `NOW() - started_at`)
- [x] `error_message` (si `status = FAILED`)

### Drilldown

- [ ] Click en `id` → Navegar a `/runs/{run_id}/report` (endpoint existente)

---

## 10. Referencias

- Modelo SQLAlchemy: `backend/app/models/ops.py:44-57`
- Schema Pydantic: `backend/app/schemas/ingestion.py:7-19`
- Servicio de Ingestión: `backend/app/services/ingestion.py:20-195`
- Migración inicial: `backend/alembic/versions/001_create_canon_schema.py:72-82`
- Migración campos adicionales: `backend/alembic/versions/004_add_ingestion_run_fields.py:19-25`
- Endpoint de reporte: `backend/app/api/v1/identity.py:913` (`GET /runs/{run_id}/report`)
- Script de validación: `backend/scripts/validate_run_id.py`

---

**Fin del Documento**


