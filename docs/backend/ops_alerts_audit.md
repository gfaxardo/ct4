# Auditoría de Base de Datos: Ops Alerts

## Resumen Ejecutivo

Esta auditoría documenta la estructura de la tabla que almacena alertas del sistema operacional, sus columnas relevantes para UI, enums, índices y recomendaciones de ordenamiento.

**Fecha de Auditoría:** 2024-01-XX  
**Tabla:** `ops.alerts`  
**Modelo SQLAlchemy:** `Alert` (ubicado en `backend/app/models/ops.py`)

---

## 1. Identificación de la Tabla

### Nombre y Esquema

- **Nombre de tabla:** `alerts`
- **Esquema:** `ops`
- **Nombre completo:** `ops.alerts`

### Ubicación en Código

- **Modelo SQLAlchemy:** `backend/app/models/ops.py` (línea 66)
- **Servicio:** `backend/app/services/alerts.py`
- **Migración inicial:** `backend/alembic/versions/009_create_alerts_table.py`

---

## 2. Columnas Relevantes para UI

### Columnas Principales

| Columna | Tipo | Nullable | Default | Descripción |
|---------|------|----------|---------|-------------|
| `id` | `Integer` | NO | `autoincrement` | **Primary Key**. Identificador único de la alerta. |
| `alert_type` | `String` | NO | - | **Tipo de alerta**. Valores conocidos: `scouting_no_echo`, `scouting_high_delay`, `scouting_strong_signal`. No es un enum, es string libre. |
| `severity` | `Enum(AlertSeverity)` | NO | - | **Severidad**. Valores: `info`, `warning`, `error` (ver enums abajo). |
| `week_label` | `String` | NO | - | **Semana ISO**. Formato: `YYYY-WNN` (ej: `2025-W51`). Identifica la semana relacionada con la alerta. |
| `message` | `Text` | NO | - | **Mensaje descriptivo**. Texto legible que describe la alerta. |
| `details` | `JSONB` | YES | `NULL` | **Detalles adicionales**. Objeto JSON con información específica del tipo de alerta. |
| `created_at` | `DateTime(timezone=True)` | NO | `now()` | **Fecha/hora de creación**. Timestamp de cuando se generó la alerta. |
| `acknowledged_at` | `DateTime(timezone=True)` | YES | `NULL` | **Fecha/hora de reconocimiento**. NULL si no ha sido reconocida. |
| `run_id` | `Integer` (FK) | YES | `NULL` | **Referencia a corrida**. FK a `ops.ingestion_runs.id`. Identifica la corrida que generó la alerta. |

### Campos Derivados para UI

Aunque no existen como columnas directas, estos valores pueden calcularse:

- **`acknowledged`** (boolean): `acknowledged_at IS NOT NULL`
  - **Nota:** No existe como columna, pero se puede derivar fácilmente.

- **`source`** (string): Puede derivarse de:
  - `alert_type`: Los tipos conocidos comienzan con `scouting_`, lo que indica el módulo fuente.
  - `run_id`: Si existe, puede consultarse `ops.ingestion_runs.job_type` para identificar el job.

- **`entity_ref`**: No existe en la tabla actual. Si se necesita referenciar una entidad específica (ej: `person_key`, `driver_id`), debería agregarse como columna nueva o incluirse en `details` (JSONB).

- **`acknowledged_by`**: No existe en la tabla actual. Si se necesita rastrear quién reconoció la alerta, debería agregarse como columna nueva.

---

## 3. Enums Existentes

### Enum: AlertSeverity

**Definición:** `backend/app/models/ops.py:60-63`

```python
class AlertSeverity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
```

**Valores en BD:** `info`, `warning`, `error` (lowercase)

**Tipo PostgreSQL:** `alertseverity` (ENUM)

**Uso en UI:**
- `info`: Alertas informativas (color azul)
- `warning`: Alertas de advertencia (color amarillo)
- `error`: Alertas de error (color rojo)

### Enum: alert_type (NO es enum, es String)

**Importante:** `alert_type` NO es un enum en la base de datos, es un campo `String` libre.

**Valores conocidos** (según `backend/app/services/alerts.py`):

1. **`scouting_no_echo`**
   - Severidad: `WARNING`
   - Mensaje: "Scouting sin correlato posterior en fuentes confiables"
   - Condición: `processed > 50 AND candidates == 0` por 2 semanas consecutivas

2. **`scouting_high_delay`**
   - Severidad: `INFO`
   - Mensaje: "Alto delay entre scouting y aparición en Cabinet/Drivers"
   - Condición: `avg_time_to_match_days > 14`

3. **`scouting_strong_signal`**
   - Severidad: `INFO`
   - Mensaje: "Scouting empieza a generar señales fuertes (pre-Fase 2)"
   - Condición: `high_confidence_candidates >= 5`

**Recomendación:** Si se necesita restringir valores, considerar crear un enum PostgreSQL o validar en el código.

---

## 4. Índices Actuales

### Índice #1: week_label

```sql
CREATE INDEX idx_alerts_week_label ON ops.alerts (week_label);
```

**Propósito:** Optimizar consultas filtradas por semana.

**Uso:** Consultas que filtran por `week_label` (ej: alertas de una semana específica).

### Índice #2: acknowledged_at (Parcial)

```sql
CREATE INDEX idx_alerts_acknowledged ON ops.alerts (acknowledged_at)
WHERE acknowledged_at IS NULL;
```

**Propósito:** Índice parcial para alertas no reconocidas (activas).

**Uso:** Consultas que filtran `acknowledged_at IS NULL` (alertas activas).

**Nota:** Este es un índice parcial (PostgreSQL), solo indexa filas donde `acknowledged_at IS NULL`, optimizando consultas de alertas activas.

---

## 5. Recomendaciones de Índices Adicionales

### Índice Recomendado #1: created_at DESC (para UI)

```sql
CREATE INDEX idx_alerts_created_at_desc ON ops.alerts (created_at DESC);
```

**Justificación:** El orden recomendado para UI es mostrar las alertas más recientes primero. Este índice optimiza consultas del tipo:

```sql
SELECT * FROM ops.alerts 
WHERE acknowledged_at IS NULL
ORDER BY created_at DESC 
LIMIT 50;
```

**Impacto:** Medio-Alto para páginas de listado frecuentemente consultadas.

### Índice Recomendado #2: severity + created_at (para filtros)

```sql
CREATE INDEX idx_alerts_severity_created ON ops.alerts (severity, created_at DESC);
```

**Justificación:** Permite filtrar rápidamente por severidad y ordenar por fecha.

**Impacto:** Medio si se implementan filtros por severidad en la UI.

### Índice Recomendado #3: alert_type + created_at (para filtros por tipo)

```sql
CREATE INDEX idx_alerts_type_created ON ops.alerts (alert_type, created_at DESC);
```

**Justificación:** Permite filtrar por tipo de alerta y ordenar por fecha.

**Impacto:** Medio si se implementan filtros por tipo en la UI.

---

## 6. Orden Recomendado para UI

### Orden Principal

**`ORDER BY created_at DESC`**

Mostrar las alertas más recientes primero es el comportamiento estándar esperado por usuarios.

### Orden Alternativo (Alertas Activas Primero)

Si se necesita mostrar alertas no reconocidas al principio:

```sql
ORDER BY 
  CASE WHEN acknowledged_at IS NULL THEN 0 ELSE 1 END,
  created_at DESC
```

Esto coloca primero las alertas activas (no reconocidas), luego las reconocidas ordenadas por fecha descendente.

### Orden por Severidad + Fecha

Si se necesita agrupar por severidad:

```sql
ORDER BY 
  CASE severity 
    WHEN 'error' THEN 0 
    WHEN 'warning' THEN 1 
    WHEN 'info' THEN 2 
  END,
  created_at DESC
```

Esto coloca primero errores, luego warnings, luego info, cada grupo ordenado por fecha descendente.

---

## 7. Consultas SQL de Ejemplo

### Consulta Básica para UI (Listado de Alertas Activas)

```sql
SELECT 
  id,
  alert_type,
  severity,
  week_label,
  message,
  details,
  created_at,
  acknowledged_at,
  run_id,
  CASE WHEN acknowledged_at IS NOT NULL THEN true ELSE false END AS acknowledged
FROM ops.alerts
WHERE acknowledged_at IS NULL
ORDER BY created_at DESC
LIMIT 50;
```

### Consulta con Filtros (Severidad + Tipo)

```sql
SELECT 
  id,
  alert_type,
  severity,
  week_label,
  message,
  created_at,
  acknowledged_at,
  run_id
FROM ops.alerts
WHERE 
  acknowledged_at IS NULL
  AND severity = 'warning'
  AND alert_type = 'scouting_no_echo'
ORDER BY created_at DESC;
```

### Consulta con Información de Run

```sql
SELECT 
  a.id,
  a.alert_type,
  a.severity,
  a.week_label,
  a.message,
  a.created_at,
  a.acknowledged_at,
  a.run_id,
  r.job_type AS source_job_type,
  r.started_at AS run_started_at
FROM ops.alerts a
LEFT JOIN ops.ingestion_runs r ON a.run_id = r.id
WHERE a.acknowledged_at IS NULL
ORDER BY a.created_at DESC;
```

### Consulta con Conteo por Severidad

```sql
SELECT 
  severity,
  COUNT(*) as count
FROM ops.alerts
WHERE acknowledged_at IS NULL
GROUP BY severity
ORDER BY 
  CASE severity 
    WHEN 'error' THEN 0 
    WHEN 'warning' THEN 1 
    WHEN 'info' THEN 2 
  END;
```

---

## 8. Estructura del Campo `details` (JSONB)

El campo `details` contiene información específica según el tipo de alerta:

### Para `scouting_no_echo`:

```json
{
  "current_week": "2025-W51",
  "current_processed": 120,
  "current_candidates": 0,
  "previous_week": "2025-W50",
  "previous_processed": 115,
  "previous_candidates": 0
}
```

### Para `scouting_high_delay`:

```json
{
  "week_label": "2025-W51",
  "avg_time_to_match_days": 16.5
}
```

### Para `scouting_strong_signal`:

```json
{
  "week_label": "2025-W51",
  "high_confidence_candidates": 7
}
```

**Nota:** La estructura puede variar según el tipo de alerta. Se recomienda parsear condicionalmente según `alert_type`.

---

## 9. Relación con Otras Tablas

### Tablas Relacionadas

- **`ops.ingestion_runs`**: 
  - Relación: `alerts.run_id` → `ingestion_runs.id` (FK)
  - Propósito: Identificar la corrida que generó la alerta
  - Uso: Para obtener contexto del job (`job_type`, `started_at`, etc.)

---

## 10. Campos Faltantes / Sugerencias para Futuras Mejoras

### Campos que NO existen pero podrían ser útiles

1. **`acknowledged_by`** (String): Usuario o sistema que reconoció la alerta.
   - **Estado Actual:** No existe.
   - **Recomendación:** Agregar si se necesita auditoría de reconocimientos.

2. **`entity_ref`** (String/UUID): Referencia a una entidad específica relacionada (ej: `person_key`, `driver_id`).
   - **Estado Actual:** No existe.
   - **Recomendación:** Agregar si las alertas necesitan referenciar entidades específicas. Alternativa: incluir en `details` (JSONB).

3. **`source`** (String/Enum): Módulo o job que generó la alerta (ej: `scouting`, `identity`, `payments`).
   - **Estado Actual:** Puede derivarse de `alert_type` (prefijo) o `run_id.job_type`.
   - **Recomendación:** Si se necesita indexar o filtrar frecuentemente, considerar agregar como columna dedicada.

4. **`resolved_at`** (DateTime): Fecha/hora de resolución (diferente de reconocimiento).
   - **Estado Actual:** No existe (solo `acknowledged_at`).
   - **Recomendación:** Agregar si se necesita distinguir entre "reconocida" y "resuelta".

5. **`expires_at`** (DateTime): Fecha/hora de expiración automática.
   - **Estado Actual:** No existe.
   - **Recomendación:** Agregar si se necesita expiración automática de alertas.

---

## 11. Checklist para Implementación de UI

### Endpoint Requerido (sugerido)

- [ ] **GET `/api/v1/ops/alerts`** (Listado de alertas)
  - Parámetros: `limit?`, `offset?`, `severity?`, `alert_type?`, `acknowledged?`, `week_label?`
  - Response: Array de `Alert` con campos calculados (`acknowledged`)

### Campos a Mostrar en UI

- [x] `id` (PK)
- [x] `created_at` (fecha/hora de creación, formateada)
- [x] `alert_type` (tipo de alerta, mostrar como badge o etiqueta)
- [x] `severity` (info/warning/error, mostrar como Badge con colores)
- [x] `message` (mensaje descriptivo)
- [x] `week_label` (semana relacionada)
- [x] `acknowledged` (derivado: `acknowledged_at IS NOT NULL`, mostrar como checkbox o badge)
- [x] `acknowledged_at` (fecha/hora de reconocimiento, si existe)
- [ ] `source` (derivado de `alert_type` o `run_id.job_type`)
- [ ] `entity_ref` (si se agrega en el futuro)
- [ ] `acknowledged_by` (si se agrega en el futuro)
- [x] `details` (expandible/collapsible, mostrar como JSON formateado)

### Filtros Sugeridos

- [ ] Por `severity` (dropdown: info, warning, error, todos)
- [ ] Por `alert_type` (dropdown con valores conocidos)
- [ ] Por `acknowledged` (checkbox: solo activas / todas)
- [ ] Por `week_label` (input de semana ISO)

### Acciones Sugeridas

- [ ] Click en `id` → Ver detalles completos (modal o página)
- [ ] Botón "Reconocer" → Actualizar `acknowledged_at` (requiere endpoint `POST /api/v1/ops/alerts/{id}/acknowledge`)
- [ ] Expandir `details` → Mostrar JSON formateado

---

## 12. Referencias

- Modelo SQLAlchemy: `backend/app/models/ops.py:66-78`
- Servicio de Alertas: `backend/app/services/alerts.py`
- Migración inicial: `backend/alembic/versions/009_create_alerts_table.py:19-52`
- Enum AlertSeverity: `backend/app/models/ops.py:60-63`

---

**Fin del Documento**









