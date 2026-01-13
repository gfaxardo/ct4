# Identity Gap Recovery - Runbook

## Objetivo

Este runbook documenta cómo operar el sistema de recovery de Identity Gap para leads Cabinet. El sistema detecta leads sin identidad (`person_key`) o sin origin, y reintenta matching automáticamente.

## Arquitectura

- **Vista de análisis**: `ops.v_identity_gap_analysis` - Identifica leads con brechas
- **Job de recovery**: `backend/jobs/retry_identity_matching.py` - Procesa leads unresolved
- **Tabla de tracking**: `ops.identity_matching_jobs` - Rastrea intentos de matching por lead
- **Vista KPI**: `ops.v_identity_driver_unlinked_activity` - Drivers con actividad sin identidad (KPI aparte)

## Comando para Ejecutar el Job

### Opción 1: Desde Python (recomendado)

```bash
cd backend
source venv/bin/activate  # o venv\Scripts\activate en Windows
python -m jobs.retry_identity_matching
```

### Opción 2: Con parámetros

```bash
# Procesar solo 1000 leads
python -m jobs.retry_identity_matching 1000

# Procesar solo leads de alta prioridad
python -c "from jobs.retry_identity_matching import run_job; run_job(limit=500, risk_level='high')"

# Procesar solo leads sin identidad
python -c "from jobs.retry_identity_matching import run_job; run_job(limit=1000, gap_reason='no_identity')"
```

### Opción 3: Desde API (si está expuesto)

```bash
# POST /api/v1/ops/identity-gaps/run-recovery
curl -X POST "http://localhost:8000/api/v1/ops/identity-gaps/run-recovery?limit=1000"
```

## Scheduler (Cron)

### Linux/Mac

Agregar a crontab (`crontab -e`):

```bash
# Ejecutar diariamente a las 2 AM
0 2 * * * cd /path/to/ct4/backend && source venv/bin/activate && python -m jobs.retry_identity_matching >> /var/log/identity_gap_recovery.log 2>&1

# Ejecutar cada 6 horas
0 */6 * * * cd /path/to/ct4/backend && source venv/bin/activate && python -m jobs.retry_identity_matching >> /var/log/identity_gap_recovery.log 2>&1
```

### Windows (Task Scheduler)

1. Abrir Task Scheduler
2. Crear nueva tarea básica
3. Trigger: Diariamente a las 2:00 AM
4. Acción: Iniciar programa
   - Programa: `C:\Python311\python.exe`
   - Argumentos: `-m jobs.retry_identity_matching`
   - Directorio de inicio: `C:\path\to\ct4\backend`
5. Guardar

### Docker/Container

Si el backend corre en Docker, agregar al `docker-compose.yml`:

```yaml
services:
  identity-gap-recovery:
    build: ./backend
    command: python -m jobs.retry_identity_matching
    environment:
      - DATABASE_URL=${DATABASE_URL}
    restart: "no"  # No restart automático, solo corre cuando se invoca
    depends_on:
      - db
```

Y ejecutar con cron en el host o usar un scheduler externo (ej: Kubernetes CronJob).

## Verificación de Freshness

### Query SQL

```sql
-- Verificar último run del job
SELECT 
    MAX(last_attempt_at) as last_run,
    COUNT(*) FILTER (WHERE last_attempt_at >= NOW() - INTERVAL '24 hours') as jobs_last_24h,
    COUNT(*) FILTER (WHERE status = 'matched' AND last_attempt_at >= NOW() - INTERVAL '24 hours') as matched_last_24h
FROM ops.identity_matching_jobs;
```

### Script de Verificación

```bash
cd backend
python scripts/diagnose_identity_gap.py
```

Este script imprime:
- Métricas actuales de brecha
- Freshness del job (último run, jobs en 24h)
- Top fail_reasons
- Volumen procesado real
- Verificación de vínculos creados

## Evolución del Gap

### Query: Unresolved hoy vs ayer

```sql
-- Comparar unresolved hoy vs ayer (requiere snapshot diario o usar histórico)
WITH today_gap AS (
    SELECT COUNT(*) FILTER (WHERE gap_reason != 'resolved') as unresolved_today
    FROM ops.v_identity_gap_analysis
),
yesterday_gap AS (
    -- Si tienes tabla histórica, usar eso. Si no, calcular desde jobs
    SELECT COUNT(*) FILTER (WHERE status != 'matched') as unresolved_yesterday
    FROM ops.identity_matching_jobs
    WHERE last_attempt_at < NOW() - INTERVAL '24 hours'
)
SELECT 
    t.unresolved_today,
    y.unresolved_yesterday,
    t.unresolved_today - y.unresolved_yesterday as delta
FROM today_gap t, yesterday_gap y;
```

### Query: Matched en últimas 24h

```sql
SELECT 
    COUNT(*) as matched_last_24h,
    COUNT(DISTINCT matched_person_key) as unique_persons_matched
FROM ops.identity_matching_jobs
WHERE status = 'matched'
  AND last_attempt_at >= NOW() - INTERVAL '24 hours';
```

## Logs

### Ubicación de Logs

- **Aplicación**: Logs de Python (configurar en `logging.conf` o variables de entorno)
- **Cron**: `/var/log/identity_gap_recovery.log` (Linux) o archivo especificado en crontab
- **Docker**: `docker logs <container_name>`

### Niveles de Log

- `INFO`: Progreso del job (batches, stats)
- `WARNING`: Leads que no se pudieron procesar (ej: lead_not_found)
- `ERROR`: Errores críticos (excepciones, problemas de DB)

### Ejemplo de Log Esperado

```
INFO: Encontrados 1500 leads unresolved para procesar (batch_size=500)
INFO: Procesando batch 1/3 (500 leads)
INFO: Batch 1 completado: matched=45, failed=12, pending=443, skipped=0
INFO: Procesando batch 2/3 (500 leads)
INFO: Batch 2 completado: matched=38, failed=8, pending=454, skipped=0
INFO: Procesando batch 3/3 (500 leads)
INFO: Batch 3 completado: matched=52, failed=15, pending=433, skipped=0
INFO: Job completado en 125.3s: processed=1500, matched=135, failed=35, pending=1330, skipped=0
```

## Troubleshooting

### Problema: Job no corre

**Síntomas**: `last_run` es NULL o > 24h

**Solución**:
1. Verificar que el scheduler está configurado
2. Verificar permisos de ejecución del script
3. Verificar variables de entorno (DATABASE_URL)
4. Ejecutar manualmente para ver errores

### Problema: Job corre pero no matchea nada

**Síntomas**: `matched_last_24h = 0` pero hay leads unresolved

**Diagnóstico**:
```bash
python scripts/diagnose_identity_gap.py
```

Revisar:
- Top fail_reasons (¿todos son "no_match_found"?)
- ¿Los leads tienen `park_phone` o nombres?
- ¿`drivers_index` está actualizado?

**Solución**:
1. Refrescar `drivers_index`: `POST /api/v1/identity/drivers-index/refresh`
2. Verificar que los leads tienen datos suficientes para matching
3. Revisar logs para ver qué reglas de matching se están aplicando

### Problema: Job crea jobs pero no crea identity_links

**Síntomas**: `matched > 0` pero no hay nuevos `identity_links`

**Diagnóstico**:
```sql
SELECT COUNT(*) as matched_no_link
FROM ops.identity_matching_jobs j
WHERE j.status = 'matched'
  AND NOT EXISTS (
      SELECT 1
      FROM canon.identity_links il
      WHERE il.source_table = 'module_ct_cabinet_leads'
        AND il.source_pk = j.source_id
  );
```

**Solución**:
1. Revisar logs para errores en `_ensure_identity_link`
2. Verificar constraints de `canon.identity_links` (unique constraint)
3. Verificar que `person_key` existe en `canon.identity_registry`

### Problema: Gap no baja

**Síntomas**: `pct_unresolved` se mantiene en ~24%

**Diagnóstico**:
1. Verificar que el job está corriendo: `diagnose_identity_gap.py`
2. Verificar que está matcheando: `matched_last_24h > 0`
3. Verificar que los vínculos se crean: query arriba
4. Verificar que la vista está actualizada: `SELECT COUNT(*) FROM ops.v_identity_gap_analysis WHERE gap_reason != 'resolved'`

**Posibles causas**:
- Job no está corriendo
- Job corre pero no encuentra matches (datos insuficientes)
- Job matchea pero no crea vínculos (error en código)
- Vista no se actualiza (problema de cache o refresh)

## Métricas de Éxito

- ✅ **Freshness**: Job corre al menos una vez cada 24h
- ✅ **Volumen**: `matched_last_24h > 0` (si hay señal en datos)
- ✅ **Tendencia**: `pct_unresolved` baja con el tiempo (al menos en entorno con data real)
- ✅ **Integridad**: Todos los jobs `matched` tienen `identity_link` correspondiente
- ✅ **Auditabilidad**: `identity_links` e `identity_origin` se actualizan correctamente

## Próximos Pasos

1. **Monitoreo**: Agregar alertas si `last_run > 24h` o `matched_last_24h = 0` por > 48h
2. **Optimización**: Ajustar `BATCH_SIZE` según performance
3. **Métricas**: Exponer métricas en dashboard/UI (ver FASE 3 UI)
