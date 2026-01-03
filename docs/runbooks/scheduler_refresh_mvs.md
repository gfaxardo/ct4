# Runbook: Refresh de Materialized Views - Yango Cabinet Claims

## Objetivo

Mantener actualizada la vista materializada `ops.mv_yango_cabinet_claims_for_collection` que alimenta los endpoints de Yango Cabinet Claims.

## MV Crítica

- **Nombre completo**: `ops.mv_yango_cabinet_claims_for_collection`
- **Propósito**: Vista materializada de claims para cobranza Yango
- **Frecuencia recomendada**: Cada hora o cuando hay nuevos claims
- **Dependencias**: 
  - `ops.mv_yango_payments_raw_current`
  - `ops.mv_yango_payments_ledger_latest`
  - `ops.mv_yango_payments_ledger_latest_enriched`
  - `ops.mv_yango_receivable_payable_detail`
  - `ops.mv_claims_payment_status_cabinet`

## Prerequisito para CONCURRENTLY (Yango Cabinet Claims)

Para habilitar `REFRESH MATERIALIZED VIEW CONCURRENTLY` en `ops.mv_yango_cabinet_claims_for_collection`, se requiere un índice único en el grano canónico.

### Paso 1: Verificar que NO hay duplicados

Ejecutar Query 2 de `docs/ops/yango_cabinet_claims_mv_duplicates.sql`:

```bash
psql -d database -f docs/ops/yango_cabinet_claims_mv_duplicates.sql
```

O ejecutar solo Query 2:

```sql
SELECT 
    driver_id,
    milestone_value,
    COUNT(*) AS count_duplicates
FROM ops.mv_yango_cabinet_claims_for_collection
GROUP BY driver_id, milestone_value
HAVING COUNT(*) > 1
ORDER BY count_duplicates DESC
LIMIT 200;
```

**Resultado esperado:** 0 filas. Si hay filas, resolver duplicados antes de continuar.

### Paso 2: Crear índice único

**IMPORTANTE:** Este comando NO puede ejecutarse dentro de una transacción (por ser `CONCURRENTLY`).

```bash
psql -d database -f backend/sql/ops/mv_yango_cabinet_claims_unique_index.sql
```

O ejecutar directamente:

```bash
psql -d database -c "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS ux_mv_yango_cabinet_claims_for_collection_grain ON ops.mv_yango_cabinet_claims_for_collection (driver_id, milestone_value);"
```

### Paso 3: Verificar que el índice existe

```sql
SELECT 
    schemaname,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'ops'
  AND tablename = 'mv_yango_cabinet_claims_for_collection'
  AND indexname = 'ux_mv_yango_cabinet_claims_for_collection_grain';
```

**Resultado esperado:** 1 fila con el índice definido.

### Notas

- El índice se crea con `CONCURRENTLY` para no bloquear la MV durante la creación
- Una vez creado, el script `refresh_yango_cabinet_claims_mv.py` puede usar `REFRESH CONCURRENTLY`
- Si el índice ya existe, el comando es idempotente (no falla)

---

## Refresh Manual

### Opción 1: Script Específico (Recomendado)

```bash
cd backend
python scripts/refresh_yango_cabinet_claims_mv.py
```

Este script:
- Registra el inicio del refresh en `ops.mv_refresh_log` (status=RUNNING)
- Refresca la MV (intenta CONCURRENTLY, fallback a normal si falla)
- Obtiene el conteo de filas después del refresh
- Actualiza el log con status=OK o ERROR
- Retorna exit code 0 si exitoso, != 0 si falló

### Opción 2: Script General (Todas las MVs)

```bash
cd backend
python scripts/refresh_ops_mvs.py
```

Este script refresca todas las MVs en orden canónico (incluye `mv_yango_cabinet_claims_for_collection`).

### Opción 3: SQL Directo

```sql
-- Con CONCURRENTLY (requiere índice único)
REFRESH MATERIALIZED VIEW CONCURRENTLY ops.mv_yango_cabinet_claims_for_collection;

-- Sin CONCURRENTLY (bloquea la MV durante el refresh)
REFRESH MATERIALIZED VIEW ops.mv_yango_cabinet_claims_for_collection;
```

**Nota**: CONCURRENTLY permite consultas durante el refresh pero requiere un índice único en la MV.

## Programación Automática

### Docker Compose

Si usas Docker Compose, agregar servicio cron:

```yaml
services:
  mv-refresh-cron:
    image: postgres:15
    volumes:
      - ./backend:/app
    command: >
      sh -c "
        apt-get update && apt-get install -y cron python3 python3-pip &&
        pip3 install -r /app/requirements.txt &&
        echo '0 * * * * cd /app && python3 scripts/refresh_yango_cabinet_claims_mv.py >> /var/log/mv-refresh.log 2>&1' | crontab - &&
        cron -f
      "
    environment:
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - postgres
```

### Cron (Linux/Mac)

```bash
# Editar crontab
crontab -e

# Agregar línea para refresh cada hora
0 * * * * cd /path/to/CT4/backend && /path/to/venv/bin/python scripts/refresh_yango_cabinet_claims_mv.py >> /var/log/mv-refresh.log 2>&1
```

### Task Scheduler (Windows)

1. Abrir "Programador de tareas"
2. Crear tarea básica
3. Trigger: Diariamente, cada hora
4. Acción: Iniciar programa
   - Programa: `C:\path\to\venv\Scripts\python.exe`
   - Argumentos: `C:\path\to\CT4\backend\scripts\refresh_yango_cabinet_claims_mv.py`
   - Directorio: `C:\path\to\CT4\backend`

## Health Check

### Query SQL

```sql
SELECT * FROM ops.v_yango_cabinet_claims_mv_health;
```

Devuelve:
- `last_ok_refresh_finished_at`: Último refresh exitoso
- `hours_since_ok_refresh`: Horas desde último refresh exitoso
- `status_bucket`: OK (<24h), WARN (24-48h), CRIT (>48h), NO_REFRESH
- `last_status`: Último status (OK, ERROR, RUNNING)
- `last_error`: Último mensaje de error si existe
- `rows_after_refresh`: Número de filas después del último refresh exitoso

### Script Python

```bash
cd backend
python -c "
from app.db import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT * FROM ops.v_yango_cabinet_claims_mv_health'))
    row = result.fetchone()
    print(f'Status: {row[2]}')
    print(f'Hours since OK: {row[1]:.2f}')
    print(f'Last error: {row[4]}')
"
```

### Integración con Health Audit

El script `backend/scripts/run_ops_health_audit.py` incluye validación automática de MVs críticas.

Ejecutar:
```bash
cd backend
python scripts/run_ops_health_audit.py
```

## Troubleshooting

### Status = ERROR

1. **Verificar último error**:
   ```sql
   SELECT error_message, refresh_started_at 
   FROM ops.mv_refresh_log 
   WHERE schema_name = 'ops' 
     AND mv_name = 'mv_yango_cabinet_claims_for_collection'
   ORDER BY refresh_started_at DESC 
   LIMIT 1;
   ```

2. **Verificar dependencias**:
   ```sql
   -- Verificar que las MVs dependientes estén actualizadas
   SELECT schema_name, mv_name, MAX(refreshed_at) as last_refresh
   FROM ops.mv_refresh_log
   WHERE mv_name IN (
     'mv_yango_payments_raw_current',
     'mv_yango_payments_ledger_latest',
     'mv_yango_payments_ledger_latest_enriched',
     'mv_yango_receivable_payable_detail',
     'mv_claims_payment_status_cabinet'
   )
   GROUP BY schema_name, mv_name;
   ```

3. **Reintentar refresh manual**:
   ```bash
   cd backend
   python scripts/refresh_yango_cabinet_claims_mv.py
   ```

### Atraso > 24 horas

1. **Verificar health**:
   ```sql
   SELECT * FROM ops.v_yango_cabinet_claims_mv_health;
   ```

2. **Verificar si hay refresh en progreso**:
   ```sql
   SELECT * FROM ops.mv_refresh_log 
   WHERE schema_name = 'ops' 
     AND mv_name = 'mv_yango_cabinet_claims_for_collection'
     AND status = 'RUNNING'
   ORDER BY refresh_started_at DESC;
   ```

3. **Si hay refresh RUNNING colgado**:
   - Verificar procesos de PostgreSQL bloqueando la MV
   - Si es necesario, cancelar el proceso y reintentar

4. **Ejecutar refresh manual**:
   ```bash
   cd backend
   python scripts/refresh_yango_cabinet_claims_mv.py
   ```

### MV No Poblada

```sql
-- Verificar si la MV está poblada
SELECT schemaname, matviewname, ispopulated 
FROM pg_matviews 
WHERE schemaname = 'ops' 
  AND matviewname = 'mv_yango_cabinet_claims_for_collection';
```

Si `ispopulated = false`, ejecutar refresh manual.

### Performance Lenta

1. **Verificar índices**:
   ```sql
   SELECT indexname, indexdef 
   FROM pg_indexes 
   WHERE schemaname = 'ops' 
     AND tablename = 'mv_yango_cabinet_claims_for_collection';
   ```

2. **Verificar estadísticas**:
   ```sql
   ANALYZE ops.mv_yango_cabinet_claims_for_collection;
   ```

3. **Considerar refresh sin CONCURRENTLY** si el refresh es muy lento con CONCURRENTLY

## Monitoreo Recomendado

1. **Alertas automáticas**: Configurar alerta si `hours_since_ok_refresh > 24`
2. **Dashboard**: Incluir `ops.v_yango_cabinet_claims_mv_health` en dashboard de ops
3. **Logs**: Revisar logs de refresh semanalmente para detectar patrones de error

## Referencias

- SQL de health check: `docs/ops/yango_cabinet_claims_mv_health.sql`
- Script de refresh: `backend/scripts/refresh_yango_cabinet_claims_mv.py`
- Tabla de log: `ops.mv_refresh_log`
- Vista de health: `ops.v_yango_cabinet_claims_mv_health`

