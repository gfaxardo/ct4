# Auditoría de Estado de Salud de Datos: Sistema de Identidad Canónica

## Resumen Ejecutivo

Esta auditoría identifica tablas, vistas y métricas disponibles para construir una página de "Data Health" enfocada en el sistema de identidad canónica. Se evalúa si usar vistas existentes o crear una nueva vista específica.

**Fecha de Auditoría:** 2024-01-XX  
**Objetivo:** Construir `/ops/data-health` para monitorear salud del sistema de identidad

---

## 1. Tablas/Vistas Existentes Relevantes

### 1.1 Vistas de Data Health Existentes

**Ubicación:** `backend/sql/ops/v_data_health.sql` y `backend/sql/ops/v_data_health_complete.sql`

**Vistas creadas:**
- `ops.v_data_sources_catalog`: Catálogo de fuentes monitoreadas
- `ops.v_data_freshness_status`: Frescura de datos por fuente RAW
- `ops.v_data_health_status`: Estado de salud calculado por fuente RAW
- `ops.v_data_ingestion_daily`: Ingesta diaria por fuente RAW

**Enfoque:** Estas vistas monitorean frescura de **fuentes RAW** (summary_daily, yango_payment_ledger, module_ct_cabinet_leads, module_ct_scouting_daily, etc.), pero **NO incluyen métricas del sistema de identidad canónica**.

**Fuentes monitoreadas:**
- `summary_daily` (activity)
- `yango_payment_ledger` (ledger)
- `module_ct_cabinet_leads` (ct_ingest)
- `module_ct_scouting_daily` (ct_ingest)
- `drivers` (master)
- Y otras fuentes opcionales

**Conclusión:** Las vistas existentes son útiles para monitorear frescura de datos RAW, pero **no cubren métricas del sistema de identidad canónica** (runs, unmatched, alerts, persons).

### 1.2 Tablas del Sistema de Identidad

**Tablas relevantes identificadas:**

1. **`ops.ingestion_runs`**
   - Propósito: Historial de corridas de identidad
   - Columnas clave: `id`, `started_at`, `completed_at`, `status`, `job_type`, `stats` (JSON)
   - Uso: Obtener última corrida, estado, delay

2. **`canon.identity_unmatched`**
   - Propósito: Registros no matcheados
   - Columnas clave: `id`, `status` (OPEN/RESOLVED/IGNORED), `created_at`, `reason_code`
   - Uso: Contar unmatched activos (status = OPEN)

3. **`ops.alerts`**
   - Propósito: Alertas operacionales
   - Columnas clave: `id`, `severity`, `acknowledged_at`, `created_at`, `alert_type`
   - Uso: Contar alertas activas (acknowledged_at IS NULL)

4. **`canon.identity_registry`**
   - Propósito: Registro canónico de personas
   - Columnas clave: `person_key`, `created_at`, `updated_at`
   - Uso: Contar total de personas

5. **`canon.identity_links`**
   - Propósito: Vínculos entre personas y fuentes
   - Columnas clave: `id`, `person_key`, `source_table`, `linked_at`, `run_id`
   - Uso: Contar total de links, links por fuente

---

## 2. Métricas Simples y Confiables Propuestas

### 2.1 Métricas de Corridas de Identidad

| Métrica | Fuente | Query/Expresión | Descripción |
|---------|--------|-----------------|-------------|
| **Última corrida ID** | `ops.ingestion_runs` | `MAX(id) WHERE job_type = 'identity_run'` | ID de la última corrida |
| **Última corrida started_at** | `ops.ingestion_runs` | `MAX(started_at) WHERE job_type = 'identity_run'` | Fecha/hora de inicio de última corrida |
| **Última corrida completed_at** | `ops.ingestion_runs` | `MAX(completed_at) WHERE job_type = 'identity_run' AND status = 'COMPLETED'` | Fecha/hora de finalización de última corrida exitosa |
| **Última corrida status** | `ops.ingestion_runs` | `status WHERE id = (MAX(id) WHERE job_type = 'identity_run')` | Estado de la última corrida (RUNNING/COMPLETED/FAILED) |
| **Delay desde última corrida exitosa (minutos)** | `ops.ingestion_runs` | `EXTRACT(EPOCH FROM (NOW() - MAX(completed_at))) / 60 WHERE job_type = 'identity_run' AND status = 'COMPLETED'` | Minutos transcurridos desde última corrida completada |
| **Delay desde última corrida exitosa (horas)** | `ops.ingestion_runs` | `EXTRACT(EPOCH FROM (NOW() - MAX(completed_at))) / 3600 WHERE job_type = 'identity_run' AND status = 'COMPLETED'` | Horas transcurridas desde última corrida completada |
| **Última corrida error_message** | `ops.ingestion_runs` | `error_message WHERE id = (MAX(id) WHERE job_type = 'identity_run') AND status = 'FAILED'` | Mensaje de error si la última corrida falló |

### 2.2 Métricas de Unmatched

| Métrica | Fuente | Query/Expresión | Descripción |
|---------|--------|-----------------|-------------|
| **Total unmatched (OPEN)** | `canon.identity_unmatched` | `COUNT(*) WHERE status = 'OPEN'` | Cantidad de registros no matcheados pendientes |
| **Unmatched por reason_code** | `canon.identity_unmatched` | `reason_code, COUNT(*) WHERE status = 'OPEN' GROUP BY reason_code` | Breakdown de unmatched por razón |
| **Unmatched más antiguo (días)** | `canon.identity_unmatched` | `MAX(EXTRACT(EPOCH FROM (NOW() - created_at)) / 86400) WHERE status = 'OPEN'` | Días desde el unmatched más antiguo |

### 2.3 Métricas de Alertas

| Métrica | Fuente | Query/Expresión | Descripción |
|---------|--------|-----------------|-------------|
| **Alertas activas (total)** | `ops.alerts` | `COUNT(*) WHERE acknowledged_at IS NULL` | Cantidad de alertas no reconocidas |
| **Alertas por severidad** | `ops.alerts` | `severity, COUNT(*) WHERE acknowledged_at IS NULL GROUP BY severity` | Breakdown de alertas activas por severidad (info/warning/error) |
| **Alertas más antigua (horas)** | `ops.alerts` | `MAX(EXTRACT(EPOCH FROM (NOW() - created_at)) / 3600) WHERE acknowledged_at IS NULL` | Horas desde la alerta activa más antigua |

### 2.4 Métricas de Registro Canónico

| Métrica | Fuente | Query/Expresión | Descripción |
|---------|--------|-----------------|-------------|
| **Total personas** | `canon.identity_registry` | `COUNT(*)` | Total de personas en el registro canónico |
| **Total links** | `canon.identity_links` | `COUNT(*)` | Total de vínculos creados |
| **Links por fuente** | `canon.identity_links` | `source_table, COUNT(*) GROUP BY source_table` | Breakdown de links por tabla fuente |

### 2.5 Métricas Derivadas (Cálculos Simples)

| Métrica | Fuente | Cálculo | Descripción |
|---------|--------|---------|-------------|
| **Última corrida en ejecución** | `ops.ingestion_runs` | `status = 'RUNNING'` | Boolean: ¿Hay una corrida corriendo ahora? |
| **Última corrida falló** | `ops.ingestion_runs` | `status = 'FAILED'` | Boolean: ¿La última corrida falló? |
| **Delay crítico (>24 horas)** | `ops.ingestion_runs` | `delay_hours > 24` | Boolean: ¿La última corrida exitosa fue hace más de 24 horas? |

---

## 3. Análisis: Usar Vistas Existentes vs Crear Nueva Vista

### 3.1 Vistas Existentes (`ops.v_data_health_status`)

**Cobertura:**
- ✅ Frescura de fuentes RAW (summary_daily, yango_payment_ledger, etc.)
- ✅ Health status por fuente RAW
- ❌ **NO incluye métricas de identity runs**
- ❌ **NO incluye métricas de unmatched**
- ❌ **NO incluye métricas de alerts**
- ❌ **NO incluye métricas de registro canónico**

**Conclusión:** Las vistas existentes son útiles para monitorear **frescura de datos RAW**, pero **no cubren el sistema de identidad canónica**.

### 3.2 Recomendación: Crear Vista Nueva

**Vista propuesta:** `ops.v_identity_system_health`

**Justificación:**

1. **Separación de responsabilidades:**
   - `ops.v_data_health_status`: Salud de fuentes RAW (ingestas de datos externos)
   - `ops.v_identity_system_health`: Salud del sistema de identidad canónica (procesamiento interno)

2. **Métricas diferentes:**
   - Data Health RAW: frescura de ingestas, lag de business_date, rows por día
   - Identity System Health: estado de corridas, unmatched pendientes, alertas activas, delay de procesamiento

3. **Fuentes diferentes:**
   - Data Health RAW: `summary_daily`, `yango_payment_ledger`, `module_ct_cabinet_leads`, etc.
   - Identity System Health: `ops.ingestion_runs`, `canon.identity_unmatched`, `ops.alerts`, `canon.identity_registry`

4. **Granularidad diferente:**
   - Data Health RAW: 1 fila por fuente RAW
   - Identity System Health: 1 fila con métricas agregadas del sistema completo

**Estructura propuesta de `ops.v_identity_system_health`:**

```sql
CREATE OR REPLACE VIEW ops.v_identity_system_health AS
SELECT 
    -- Última corrida
    (SELECT id FROM ops.ingestion_runs 
     WHERE job_type = 'identity_run' 
     ORDER BY started_at DESC LIMIT 1) AS last_run_id,
    
    (SELECT started_at FROM ops.ingestion_runs 
     WHERE job_type = 'identity_run' 
     ORDER BY started_at DESC LIMIT 1) AS last_run_started_at,
    
    (SELECT completed_at FROM ops.ingestion_runs 
     WHERE job_type = 'identity_run' AND status = 'COMPLETED' 
     ORDER BY completed_at DESC LIMIT 1) AS last_completed_run_at,
    
    (SELECT status FROM ops.ingestion_runs 
     WHERE job_type = 'identity_run' 
     ORDER BY started_at DESC LIMIT 1) AS last_run_status,
    
    -- Delay
    EXTRACT(EPOCH FROM (NOW() - (SELECT completed_at FROM ops.ingestion_runs 
                                  WHERE job_type = 'identity_run' AND status = 'COMPLETED' 
                                  ORDER BY completed_at DESC LIMIT 1))) / 60 AS delay_minutes,
    
    EXTRACT(EPOCH FROM (NOW() - (SELECT completed_at FROM ops.ingestion_runs 
                                  WHERE job_type = 'identity_run' AND status = 'COMPLETED' 
                                  ORDER BY completed_at DESC LIMIT 1))) / 3600 AS delay_hours,
    
    -- Unmatched
    (SELECT COUNT(*) FROM canon.identity_unmatched WHERE status = 'OPEN') AS unmatched_count,
    
    -- Alertas
    (SELECT COUNT(*) FROM ops.alerts WHERE acknowledged_at IS NULL) AS active_alerts_count,
    (SELECT COUNT(*) FROM ops.alerts WHERE acknowledged_at IS NULL AND severity = 'error') AS active_alerts_error,
    (SELECT COUNT(*) FROM ops.alerts WHERE acknowledged_at IS NULL AND severity = 'warning') AS active_alerts_warning,
    
    -- Registro canónico
    (SELECT COUNT(*) FROM canon.identity_registry) AS total_persons,
    (SELECT COUNT(*) FROM canon.identity_links) AS total_links;
```

**Alternativa más simple (1 fila con todas las métricas):**

```sql
CREATE OR REPLACE VIEW ops.v_identity_system_health AS
WITH last_run AS (
    SELECT id, started_at, completed_at, status, error_message
    FROM ops.ingestion_runs
    WHERE job_type = 'identity_run'
    ORDER BY started_at DESC
    LIMIT 1
),
last_completed_run AS (
    SELECT completed_at
    FROM ops.ingestion_runs
    WHERE job_type = 'identity_run' AND status = 'COMPLETED'
    ORDER BY completed_at DESC
    LIMIT 1
)
SELECT 
    -- Última corrida
    lr.id AS last_run_id,
    lr.started_at AS last_run_started_at,
    lr.completed_at AS last_run_completed_at,
    lr.status AS last_run_status,
    lr.error_message AS last_run_error_message,
    
    -- Delay desde última corrida exitosa
    CASE 
        WHEN lcr.completed_at IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (NOW() - lcr.completed_at)) / 60
        ELSE NULL
    END AS delay_minutes,
    
    CASE 
        WHEN lcr.completed_at IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (NOW() - lcr.completed_at)) / 3600
        ELSE NULL
    END AS delay_hours,
    
    -- Unmatched
    (SELECT COUNT(*) FROM canon.identity_unmatched WHERE status = 'OPEN') AS unmatched_count,
    
    -- Alertas activas
    (SELECT COUNT(*) FROM ops.alerts WHERE acknowledged_at IS NULL) AS active_alerts_count,
    (SELECT COUNT(*) FROM ops.alerts WHERE acknowledged_at IS NULL AND severity = 'error') AS active_alerts_error,
    (SELECT COUNT(*) FROM ops.alerts WHERE acknowledged_at IS NULL AND severity = 'warning') AS active_alerts_warning,
    (SELECT COUNT(*) FROM ops.alerts WHERE acknowledged_at IS NULL AND severity = 'info') AS active_alerts_info,
    
    -- Registro canónico
    (SELECT COUNT(*) FROM canon.identity_registry) AS total_persons,
    (SELECT COUNT(*) FROM canon.identity_links) AS total_links,
    
    -- Timestamp de cálculo
    NOW() AS calculated_at
FROM last_run lr
CROSS JOIN last_completed_run lcr;
```

---

## 4. Métricas Propuestas para UI

### 4.1 Métricas Principales (StatCards)

| Métrica | Fuente | Tipo | Descripción UI |
|---------|--------|------|----------------|
| **Última Corrida** | `ops.ingestion_runs` | Badge | Estado: RUNNING (azul), COMPLETED (verde), FAILED (rojo) |
| **Delay** | `ops.ingestion_runs` | Texto | "Hace X horas" o "Hace X minutos" |
| **Unmatched Pendientes** | `canon.identity_unmatched` | Número | Total de unmatched con status = OPEN |
| **Alertas Activas** | `ops.alerts` | Número | Total de alertas con acknowledged_at IS NULL |
| **Total Personas** | `canon.identity_registry` | Número | Total de personas en el registro canónico |
| **Total Links** | `canon.identity_links` | Número | Total de vínculos creados |

### 4.2 Métricas Secundarias (Tabla o Detalle)

| Métrica | Fuente | Descripción UI |
|---------|--------|----------------|
| **Última corrida ID** | `ops.ingestion_runs` | Link a `/runs/{id}` |
| **Última corrida started_at** | `ops.ingestion_runs` | Fecha/hora formateada |
| **Última corrida completed_at** | `ops.ingestion_runs` | Fecha/hora formateada (si existe) |
| **Última corrida error_message** | `ops.ingestion_runs` | Mensaje de error (si status = FAILED) |
| **Unmatched por reason_code** | `canon.identity_unmatched` | Breakdown por razón (tabla o gráfico) |
| **Alertas por severidad** | `ops.alerts` | Breakdown: error (rojo), warning (amarillo), info (azul) |
| **Links por fuente** | `canon.identity_links` | Breakdown por source_table |

---

## 5. Recomendación Final

### Opción A: Crear Vista Nueva `ops.v_identity_system_health` ✅ **RECOMENDADO**

**Ventajas:**
- ✅ Separación clara de responsabilidades (RAW vs Identity System)
- ✅ Métricas específicas del sistema de identidad en un solo lugar
- ✅ Consulta simple para el endpoint (1 fila con todas las métricas)
- ✅ Fácil de mantener y extender
- ✅ No interfiere con vistas existentes de data health RAW

**Desventajas:**
- ⚠️ Requiere crear y mantener una vista nueva
- ⚠️ Duplica lógica de consulta (pero es mínima y específica)

**Estructura propuesta:**
- 1 fila con todas las métricas agregadas
- Columnas: `last_run_id`, `last_run_started_at`, `last_run_status`, `delay_minutes`, `delay_hours`, `unmatched_count`, `active_alerts_count`, `total_persons`, `total_links`, `calculated_at`

### Opción B: Usar Vistas Existentes + Consultas Adicionales ❌ **NO RECOMENDADO**

**Desventajas:**
- ❌ Las vistas existentes no cubren métricas de identidad
- ❌ Requeriría múltiples consultas (v_data_health_status + consultas ad-hoc)
- ❌ Mezcla conceptos diferentes (frescura RAW vs salud del sistema)
- ❌ Más complejo de mantener

---

## 6. Checklist de Implementación

### Endpoint Requerido

- [ ] **GET `/api/v1/ops/data-health`**
  - Response: Schema con todas las métricas de `ops.v_identity_system_health`
  - Fuente: Consultar `ops.v_identity_system_health` (1 fila)

### Vista SQL Requerida

- [ ] **Crear `ops.v_identity_system_health`**
  - Ubicación: `backend/sql/ops/v_identity_system_health.sql`
  - Estructura: 1 fila con métricas agregadas
  - Dependencias: `ops.ingestion_runs`, `canon.identity_unmatched`, `ops.alerts`, `canon.identity_registry`, `canon.identity_links`

### Schema Pydantic Requerido

- [ ] **Crear `backend/app/schemas/ops_data_health.py`**
  - Schema: `IdentitySystemHealthResponse`
  - Campos: todos los campos de la vista

### Métricas a Mostrar en UI

- [x] Última corrida (status, started_at, completed_at)
- [x] Delay desde última corrida exitosa (horas/minutos)
- [x] Unmatched pendientes (total)
- [x] Alertas activas (total, por severidad)
- [x] Total personas
- [x] Total links

---

## 7. Referencias

- Vistas existentes: `backend/sql/ops/v_data_health.sql`
- Tabla ingestion_runs: `backend/app/models/ops.py:44-57`
- Tabla alerts: `backend/app/models/ops.py:66-78`
- Tabla identity_unmatched: `backend/app/models/canon.py:57-73`
- Tabla identity_registry: `backend/app/models/canon.py:19-35`
- Tabla identity_links: `backend/app/models/canon.py:37-54`
- Auditoría identity_runs: `docs/backend/identity_runs_audit.md`
- Auditoría ops_alerts: `docs/backend/ops_alerts_audit.md`

---

**Fin del Documento**




