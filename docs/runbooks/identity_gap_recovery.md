# Runbook: Identity Gap Recovery

Este runbook describe cómo ejecutar y monitorear el job de recuperación de brechas de identidad.

## Objetivo

Reducir la brecha de "Leads sin Identidad ni Claims" de ~24% a <5% mediante matching automático recurrente.

## Componentes

1. **Vista de análisis**: `ops.v_identity_gap_analysis`
2. **Vista de alertas**: `ops.v_identity_gap_alerts`
3. **Job de matching**: `backend/jobs/retry_identity_matching.py`
4. **Tabla de jobs**: `ops.identity_matching_jobs`

## Ejecución Manual

### Opción 1: Desde Python

```bash
cd backend
python -m jobs.retry_identity_matching [LIMIT]
```

Ejemplo:
```bash
# Procesar 100 leads
python -m jobs.retry_identity_matching 100

# Procesar todos los unresolved
python -m jobs.retry_identity_matching
```

### Opción 2: Desde API (si está implementado)

```bash
POST /api/v1/ops/identity-gaps/retry
```

### Opción 3: Desde Python interactivo

```python
from jobs.retry_identity_matching import run_job
from datetime import date

# Procesar 50 leads de alto riesgo
result = run_job(
    limit=50,
    risk_level="high"
)

print(result)
```

## Programación Diaria (Cron)

### Linux/Mac

Agregar a crontab (`crontab -e`):

```bash
# Ejecutar diariamente a las 2 AM
0 2 * * * cd /path/to/CT4/backend && python -m jobs.retry_identity_matching >> /var/log/identity_gap_recovery.log 2>&1
```

### Windows (Task Scheduler)

1. Abrir Task Scheduler
2. Crear tarea básica
3. Trigger: Diario a las 2:00 AM
4. Acción: Iniciar programa
   - Programa: `python`
   - Argumentos: `-m jobs.retry_identity_matching`
   - Directorio de inicio: `C:\cursor\CT4\backend`

## Verificación de Freshness

### Verificar última ejecución

```sql
SELECT 
    MAX(last_attempt_at) AS last_run,
    COUNT(*) FILTER (WHERE status = 'pending') AS pending,
    COUNT(*) FILTER (WHERE status = 'matched') AS matched,
    COUNT(*) FILTER (WHERE status = 'failed') AS failed
FROM ops.identity_matching_jobs;
```

### Verificar métricas de brecha

```sql
SELECT 
    COUNT(*) AS total_leads,
    COUNT(*) FILTER (WHERE gap_reason != 'resolved') AS unresolved,
    ROUND(100.0 * COUNT(*) FILTER (WHERE gap_reason != 'resolved') / NULLIF(COUNT(*), 0), 2) AS pct_unresolved,
    COUNT(*) FILTER (WHERE risk_level = 'high') AS high_risk
FROM ops.v_identity_gap_analysis;
```

### Verificar alertas activas

```sql
SELECT 
    alert_type,
    severity,
    COUNT(*) AS count,
    AVG(days_open) AS avg_days_open
FROM ops.v_identity_gap_alerts
GROUP BY alert_type, severity
ORDER BY severity DESC, count DESC;
```

## Criterios de Éxito

- **Freshness**: Job ejecutado en últimas 24 horas
- **Tasa de resolución**: >50% de leads procesados se resuelven
- **Brecha total**: <5% de leads sin identidad
- **Alertas críticas**: 0 alertas de tipo `activity_no_identity`

## Troubleshooting

### Job no encuentra leads

1. Verificar que la vista `ops.v_identity_gap_analysis` devuelve filas:
   ```sql
   SELECT COUNT(*) FROM ops.v_identity_gap_analysis WHERE gap_reason != 'resolved';
   ```

2. Verificar que los filtros no son demasiado restrictivos

### Matching falla consistentemente

1. Verificar que `canon.drivers_index` está actualizado:
   ```sql
   SELECT MAX(snapshot_date) FROM canon.drivers_index;
   ```

2. Ejecutar refresh del índice si es necesario:
   ```bash
   POST /api/v1/identity/refresh-drivers-index
   ```

### Jobs quedan en "pending" indefinidamente

1. Verificar `attempt_count`:
   ```sql
   SELECT source_id, attempt_count, fail_reason 
   FROM ops.identity_matching_jobs 
   WHERE status = 'pending' AND attempt_count >= 5;
   ```

2. Si hay muchos con `attempt_count >= 5`, pueden necesitar revisión manual

## Monitoreo

### Dashboard de métricas

Acceder a la UI en: `/pagos/cobranza-yango` → Sección "Brechas de Identidad (Recovery)"

### Alertas

Las alertas se generan automáticamente en `ops.v_identity_gap_alerts`:
- `over_24h_no_identity`: Lead sin identidad por >24h
- `over_7d_unresolved`: Lead sin resolver por >7 días
- `activity_no_identity`: Lead con actividad pero sin person_key

## Logs

Los logs del job se escriben en:
- Console (si se ejecuta manualmente)
- Archivo de log del sistema (si se ejecuta vía cron)
- Logs de la aplicación (si se ejecuta vía API)

Formato de log:
```
INFO: Encontrados N leads unresolved para procesar
INFO: Lead {lead_id} matcheado exitosamente a person_key {person_key}
DEBUG: Lead {lead_id} no matcheado (intento N): {reason}
ERROR: Error procesando lead {lead_id}: {error}
INFO: Job completado: {stats}
```
