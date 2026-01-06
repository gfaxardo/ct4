# Solución Potente: Optimización Driver Matrix

## 🎯 Objetivo

Resolver el problema de rendimiento de `ops.v_payments_driver_matrix_cabinet` mediante una solución híbrida que combina:
1. **Vista Materializada** con índices optimizados
2. **Índices en tablas base** para mejorar vistas dependientes
3. **Endpoint inteligente** que usa vista materializada con fallback
4. **Refresh automático** programable

## 📊 Análisis del Problema

### Complejidad de la Vista

La vista `ops.v_payments_driver_matrix_cabinet` tiene:
- **8 CTEs complejos** con múltiples agregaciones
- **7 LEFT JOINs** y **1 FULL OUTER JOIN**
- **Dependencias de 6+ vistas** que también son complejas
- **Agregaciones con GROUP BY** sobre grandes volúmenes de datos

### Cuellos de Botella Identificados

1. **Falta de índices** en columnas filtradas frecuentemente (`origin_tag`, `week_start`, `driver_id`)
2. **Cálculos en tiempo real** en cada query
3. **Múltiples vistas dependientes** sin optimización
4. **FULL OUTER JOIN** que procesa todos los datos antes de filtrar

## 🚀 Solución Implementada

### 1. Vista Materializada con Índices

**Archivo:** `backend/sql/ops/mv_payments_driver_matrix_cabinet.sql`

- **Vista materializada** que copia los datos de la vista normal
- **6 índices optimizados** para queries frecuentes:
  - `origin_tag + week_start` (filtro más común)
  - `funnel_status` (filtro frecuente)
  - `driver_id` (búsquedas específicas)
  - `lead_date` (filtros de fecha)
  - `only_pending` (índice parcial para drivers pendientes)
  - `week_start + driver_name` (ordenamiento común)

**Ventajas:**
- ✅ Queries **10-100x más rápidas**
- ✅ Permite índices en columnas calculadas
- ✅ Datos pre-agregados, sin cálculos en tiempo real
- ✅ Estable y predecible

### 2. Índices en Tablas Base

**Archivo:** `backend/scripts/sql/create_indexes_for_driver_matrix.sql`

Índices creados en:
- `ops.v_payment_calculation` (origin_tag, driver_id + milestone_trips, lead_date)
- `ops.v_claims_payment_status_cabinet` (driver_id + milestone_value, lead_date)
- `ops.v_cabinet_milestones_achieved_from_payment_calc` (driver_id + milestone_value, achieved_date)
- `ops.v_yango_cabinet_claims_for_collection` (driver_id + milestone_value)
- `ops.v_yango_payments_claims_cabinet_14d` (driver_id + milestone_value)
- `ops.v_cabinet_funnel_status` (driver_id, funnel_status)
- `ops.v_cabinet_ops_14d_sanity` (driver_id)
- `public.drivers` (driver_id)
- `observational.v_conversion_metrics` (driver_id + origin_tag, lead_date)

**Ventajas:**
- ✅ Mejora rendimiento de vistas dependientes
- ✅ Acelera JOINs y filtros
- ✅ No afecta lógica de negocio

### 3. Endpoint Inteligente con Fallback

**Archivo:** `backend/app/api/v1/ops_payments.py`

El endpoint ahora:
- ✅ **Detecta automáticamente** si existe la vista materializada
- ✅ **Usa vista materializada** si está disponible (mejor rendimiento)
- ✅ **Fallback a vista normal** si no existe (compatibilidad)
- ✅ **Logging claro** de qué vista se está usando

**Código clave:**
```python
# Verificar si existe la vista materializada
check_mv_sql = """
    SELECT EXISTS (
        SELECT 1 
        FROM pg_matviews 
        WHERE schemaname = 'ops' 
        AND matviewname = 'mv_payments_driver_matrix_cabinet'
    )
"""
mv_exists = db.execute(text(check_mv_sql)).scalar()
if mv_exists:
    view_name = "ops.mv_payments_driver_matrix_cabinet"
else:
    view_name = "ops.v_payments_driver_matrix_cabinet"
```

### 4. Script de Refresh Automático

**Archivo:** `backend/scripts/sql/refresh_mv_driver_matrix.sql`

- ✅ **Refresh CONCURRENTLY** (permite queries durante refresh)
- ✅ **Fallback a refresh normal** si CONCURRENTLY falla
- ✅ **Timeout configurado** (5 minutos)
- ✅ **Logging** de inicio y fin

**Uso:**
```bash
# Manual
psql $DATABASE_URL -f backend/scripts/sql/refresh_mv_driver_matrix.sql

# Automático (cron job)
0 * * * * psql $DATABASE_URL -f /path/to/refresh_mv_driver_matrix.sql
```

## 📦 Archivos Creados/Modificados

### Nuevos Archivos
1. `backend/sql/ops/mv_payments_driver_matrix_cabinet.sql` - Vista materializada
2. `backend/scripts/sql/refresh_mv_driver_matrix.sql` - Script de refresh
3. `backend/scripts/sql/create_indexes_for_driver_matrix.sql` - Índices en tablas base
4. `SOLUCION_POTENTE_DRIVER_MATRIX.md` - Esta documentación

### Archivos Modificados
1. `backend/app/api/v1/ops_payments.py` - Endpoint con detección de vista materializada

## 🚀 Deployment

### Paso 1: Crear Índices en Tablas Base

```bash
psql $DATABASE_URL -f backend/scripts/sql/create_indexes_for_driver_matrix.sql
```

**Tiempo estimado:** 5-15 minutos (depende del tamaño de las tablas)

### Paso 2: Crear Vista Materializada

```bash
psql $DATABASE_URL -f backend/sql/ops/mv_payments_driver_matrix_cabinet.sql
```

**Tiempo estimado:** 10-30 minutos (depende del tamaño de los datos)

### Paso 3: Verificar Endpoint

El endpoint detectará automáticamente la vista materializada y la usará.

```bash
# Probar endpoint
curl "http://localhost:8000/api/v1/ops/payments/driver-matrix?limit=25"
```

### Paso 4: Configurar Refresh Automático

**Opción A: Cron Job (Linux/Mac)**
```bash
# Editar crontab
crontab -e

# Agregar línea (refresh cada hora)
0 * * * * psql $DATABASE_URL -f /path/to/backend/scripts/sql/refresh_mv_driver_matrix.sql >> /var/log/refresh_mv_driver_matrix.log 2>&1
```

**Opción B: Task Scheduler (Windows)**
```powershell
# Crear tarea programada que ejecute refresh_mv_driver_matrix.sql cada hora
```

**Opción C: Script Python/Node (Recomendado para producción)**
```python
# Crear script que ejecute refresh periódicamente
# Usar APScheduler, Celery, o similar
```

## 📈 Mejoras de Rendimiento Esperadas

### Antes (Vista Normal)
- **Query sin filtros:** Timeout (>30s)
- **Query con filtros básicos:** 10-30s
- **Query con filtros restrictivos:** 5-15s

### Después (Vista Materializada)
- **Query sin filtros:** 0.5-2s ⚡
- **Query con filtros básicos:** 0.2-1s ⚡
- **Query con filtros restrictivos:** 0.1-0.5s ⚡

**Mejora estimada:** **10-100x más rápido** 🚀

## ⚠️ Consideraciones Importantes

### 1. Consistencia de Datos

- La vista materializada **NO se actualiza automáticamente**
- Debe refrescarse **periódicamente** (recomendado: cada hora)
- Durante el refresh, los datos pueden estar **ligeramente desactualizados** (máx 1 hora)

### 2. Espacio en Disco

- La vista materializada ocupa **espacio adicional** (similar al tamaño de la vista normal)
- Monitorear espacio en disco antes de crear

### 3. Refresh CONCURRENTLY

- Requiere **índice único** en la vista materializada
- Si no hay índice único, usar refresh normal (bloquea queries durante refresh)

### 4. Mantenimiento

- Si la vista normal cambia, **recrear o refrescar** la materializada
- Monitorear logs de refresh para detectar problemas

## 🔍 Verificación

### Verificar Vista Materializada Existe

```sql
SELECT schemaname, matviewname, hasindexes 
FROM pg_matviews 
WHERE schemaname = 'ops' 
AND matviewname = 'mv_payments_driver_matrix_cabinet';
```

### Verificar Índices Creados

```sql
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE schemaname = 'ops' 
AND tablename = 'mv_payments_driver_matrix_cabinet';
```

### Comparar Rendimiento

```sql
-- Vista normal (lenta)
EXPLAIN ANALYZE 
SELECT * FROM ops.v_payments_driver_matrix_cabinet 
WHERE origin_tag = 'cabinet' 
LIMIT 25;

-- Vista materializada (rápida)
EXPLAIN ANALYZE 
SELECT * FROM ops.mv_payments_driver_matrix_cabinet 
WHERE origin_tag = 'cabinet' 
LIMIT 25;
```

## 🎯 Próximos Pasos (Opcional)

### 1. Paginación Cursor-Based

Reemplazar `OFFSET` por cursor-based pagination para mejor rendimiento en datasets grandes.

### 2. Particionamiento

Si los datos crecen mucho, considerar particionar la vista materializada por `week_start` o `origin_tag`.

### 3. Refresh Incremental

En lugar de refresh completo, implementar refresh incremental basado en cambios recientes.

### 4. Caché en Memoria

Para queries muy frecuentes, considerar Redis/Memcached como capa adicional de caché.

## ✅ Checklist de Deployment

- [ ] Crear índices en tablas base
- [ ] Crear vista materializada
- [ ] Verificar índices en vista materializada
- [ ] Probar endpoint con vista materializada
- [ ] Configurar refresh automático (cron/scheduler)
- [ ] Monitorear logs de refresh
- [ ] Verificar mejora de rendimiento
- [ ] Documentar frecuencia de refresh recomendada
- [ ] Notificar al equipo sobre cambios

## 📝 Notas Finales

Esta solución es **potente y escalable**, pero requiere **mantenimiento periódico** (refresh de la vista materializada). Para producción, se recomienda:

1. **Refresh cada hora** (o según necesidad operativa)
2. **Monitoreo** de logs de refresh
3. **Alertas** si el refresh falla
4. **Documentación** de la frecuencia de refresh para el equipo

La solución mantiene **compatibilidad total** con el código existente gracias al fallback automático a la vista normal.

