# 🚀 Deployment: Solución Potente Driver Matrix

## Resumen Ejecutivo

Solución híbrida que combina:
- ✅ **Vista Materializada** con índices optimizados (10-100x más rápida)
- ✅ **Índices en tablas base** para mejorar vistas dependientes
- ✅ **Endpoint inteligente** con detección automática y fallback
- ✅ **Script de refresh** automático programable

## 📋 Checklist de Deployment

### Paso 1: Crear Índices en Tablas Base ⏱️ 5-15 min

```bash
psql $DATABASE_URL -f backend/scripts/sql/create_indexes_for_driver_matrix.sql
```

**Verificación:**
```sql
-- Verificar índices creados
SELECT schemaname, tablename, indexname 
FROM pg_indexes 
WHERE indexname LIKE 'idx_%driver_matrix%' 
   OR indexname LIKE 'idx_%payment_calc%'
   OR indexname LIKE 'idx_%claims_cabinet%'
   OR indexname LIKE 'idx_%milestones_achieved%'
ORDER BY schemaname, tablename, indexname;
```

### Paso 2: Crear Vista Materializada ⏱️ 10-30 min

```bash
psql $DATABASE_URL -f backend/sql/ops/mv_payments_driver_matrix_cabinet.sql
```

**Verificación:**
```sql
-- Verificar vista materializada existe
SELECT schemaname, matviewname, hasindexes 
FROM pg_matviews 
WHERE schemaname = 'ops' 
AND matviewname = 'mv_payments_driver_matrix_cabinet';

-- Verificar índices en vista materializada
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE schemaname = 'ops' 
AND tablename = 'mv_payments_driver_matrix_cabinet';
```

### Paso 3: Verificar Endpoint

El endpoint detectará automáticamente la vista materializada.

```bash
# Probar endpoint (debería usar vista materializada)
curl "http://localhost:8000/api/v1/ops/payments/driver-matrix?limit=25"

# Verificar logs del servidor (debe mostrar "Usando vista materializada")
```

### Paso 4: Configurar Refresh Automático

**Opción A: Cron Job (Linux/Mac) - RECOMENDADO**

```bash
# Editar crontab
crontab -e

# Agregar línea (refresh cada hora a las :00)
0 * * * * psql $DATABASE_URL -f /path/to/backend/scripts/sql/refresh_mv_driver_matrix.sql >> /var/log/refresh_mv_driver_matrix.log 2>&1
```

**Opción B: Task Scheduler (Windows)**

1. Abrir "Programador de tareas"
2. Crear tarea básica
3. Trigger: Diariamente, repetir cada 1 hora
4. Acción: Iniciar programa
   - Programa: `C:\Program Files\PostgreSQL\18\bin\psql.exe`
   - Argumentos: `$DATABASE_URL -f C:\path\to\backend\scripts\sql\refresh_mv_driver_matrix.sql`

**Opción C: Script Python (Producción)**

```python
# backend/scripts/refresh_mv_driver_matrix.py
import subprocess
import os
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL")
SCRIPT_PATH = "backend/scripts/sql/refresh_mv_driver_matrix.sql"

def refresh_materialized_view():
    try:
        print(f"[{datetime.now()}] Iniciando refresh de vista materializada...")
        result = subprocess.run(
            ["psql", DATABASE_URL, "-f", SCRIPT_PATH],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"[{datetime.now()}] Refresh completado exitosamente")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"[{datetime.now()}] ERROR en refresh: {e}")
        print(e.stderr)
        raise

if __name__ == "__main__":
    refresh_materialized_view()
```

Usar con APScheduler o Celery para ejecutar periódicamente.

## 🔍 Verificación Post-Deployment

### 1. Verificar Vista Materializada

```sql
-- Debe retornar 1 fila
SELECT COUNT(*) 
FROM ops.mv_payments_driver_matrix_cabinet;
```

### 2. Comparar Rendimiento

```sql
-- Vista normal (lenta)
\timing on
SELECT * FROM ops.v_payments_driver_matrix_cabinet 
WHERE origin_tag = 'cabinet' 
LIMIT 25;

-- Vista materializada (rápida)
\timing on
SELECT * FROM ops.mv_payments_driver_matrix_cabinet 
WHERE origin_tag = 'cabinet' 
LIMIT 25;
```

### 3. Verificar Endpoint Usa Vista Materializada

Revisar logs del servidor FastAPI:
```
INFO: Usando vista materializada para mejor rendimiento
```

### 4. Probar Queries con Filtros

```bash
# Query con filtros básicos (debe ser rápida)
curl "http://localhost:8000/api/v1/ops/payments/driver-matrix?origin_tag=cabinet&week_start_from=2025-12-01&limit=50"

# Query sin filtros (debe usar filtros por defecto y ser rápida)
curl "http://localhost:8000/api/v1/ops/payments/driver-matrix?limit=25"
```

## ⚠️ Troubleshooting

### Problema: Vista Materializada No Se Crea

**Error:** `ERROR: relation "ops.mv_payments_driver_matrix_cabinet" already exists`

**Solución:**
```sql
DROP MATERIALIZED VIEW IF EXISTS ops.mv_payments_driver_matrix_cabinet CASCADE;
-- Luego ejecutar nuevamente el script de creación
```

### Problema: Refresh CONCURRENTLY Falla

**Error:** `ERROR: cannot refresh materialized view "ops.mv_payments_driver_matrix_cabinet" concurrently`

**Causa:** Falta índice único en la vista materializada.

**Solución:** El script ya maneja esto con fallback a refresh normal. Si persiste, verificar:
```sql
-- Verificar si hay índice único
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE schemaname = 'ops' 
AND tablename = 'mv_payments_driver_matrix_cabinet'
AND indexdef LIKE '%UNIQUE%';
```

### Problema: Endpoint Sigue Usando Vista Normal

**Verificar:**
1. Vista materializada existe: `SELECT * FROM pg_matviews WHERE matviewname = 'mv_payments_driver_matrix_cabinet';`
2. Logs del servidor muestran detección correcta
3. Si no detecta, revisar permisos de `pg_matviews`

### Problema: Queries Siguen Lentas

**Verificar:**
1. Índices creados correctamente
2. Vista materializada tiene datos (COUNT > 0)
3. EXPLAIN ANALYZE muestra uso de índices
4. Refresh reciente de la vista materializada

## 📊 Monitoreo

### Métricas a Monitorear

1. **Tiempo de Refresh:**
   ```sql
   -- Verificar última actualización (requiere columna de timestamp)
   -- O monitorear logs de refresh
   ```

2. **Tamaño de Vista Materializada:**
   ```sql
   SELECT 
       pg_size_pretty(pg_total_relation_size('ops.mv_payments_driver_matrix_cabinet')) AS total_size,
       pg_size_pretty(pg_relation_size('ops.mv_payments_driver_matrix_cabinet')) AS table_size,
       pg_size_pretty(pg_indexes_size('ops.mv_payments_driver_matrix_cabinet')) AS indexes_size;
   ```

3. **Rendimiento de Queries:**
   - Monitorear tiempos de respuesta del endpoint
   - Alertar si queries > 5s

### Alertas Recomendadas

1. **Refresh Falló:** Monitorear logs de refresh, alertar si falla
2. **Vista Desactualizada:** Alertar si última actualización > 2 horas
3. **Queries Lentas:** Alertar si tiempo de respuesta > 5s

## 🔄 Mantenimiento

### Refresh Manual

```bash
psql $DATABASE_URL -f backend/scripts/sql/refresh_mv_driver_matrix.sql
```

### Recrear Vista Materializada (Si Cambia Vista Normal)

```sql
-- Si la vista normal cambia, recrear la materializada
DROP MATERIALIZED VIEW IF EXISTS ops.mv_payments_driver_matrix_cabinet CASCADE;
-- Luego ejecutar nuevamente: backend/sql/ops/mv_payments_driver_matrix_cabinet.sql
```

### Actualizar Índices

```sql
-- Reindexar si es necesario
REINDEX MATERIALIZED VIEW ops.mv_payments_driver_matrix_cabinet;
```

## ✅ Checklist Final

- [ ] Índices en tablas base creados
- [ ] Vista materializada creada
- [ ] Índices en vista materializada creados
- [ ] Endpoint detecta y usa vista materializada
- [ ] Refresh automático configurado
- [ ] Rendimiento verificado (queries < 2s)
- [ ] Monitoreo configurado
- [ ] Documentación actualizada
- [ ] Equipo notificado

## 📝 Notas

- **Frecuencia de Refresh:** Recomendado cada hora. Ajustar según necesidad operativa.
- **Consistencia:** Datos pueden estar desactualizados hasta 1 hora (máximo).
- **Espacio:** Vista materializada ocupa espacio adicional (similar a vista normal).
- **Compatibilidad:** Solución mantiene compatibilidad total con código existente.

