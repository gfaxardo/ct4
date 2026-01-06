# Estado Final: Optimizaciones Timeout Driver Matrix

## Problema Identificado

La vista `ops.v_payments_driver_matrix_cabinet` es **extremadamente lenta** incluso con filtros básicos. El problema es arquitectural: la vista tiene múltiples CTEs complejos y JOINs que hacen que PostgreSQL necesite procesar grandes volúmenes de datos antes de poder aplicar filtros.

## Optimizaciones Finales Implementadas

### 1. Filtros por Defecto MUY Restrictivos ✅
- **origin_tag:** `'cabinet'` (automático)
- **week_start:** `>= (hoy - 7 días)` (última semana, no mes)
- **limit:** Máximo 25 (reducido de 50)

### 2. Límite por Defecto Muy Bajo ✅
- **Default:** `limit = 25` (reducido de 50)
- **Razón:** Reduce significativamente la cantidad de datos a procesar y ordenar

### 3. Reducción Automática de Límite ✅
- Si no hay filtros y `limit > 25`, se reduce automáticamente a 25

### 4. Manejo de Errores Mejorado ✅
- Logging detallado del WHERE clause y params
- Mensajes de error más informativos
- Sugiere límite máximo de 25 y filtros muy restrictivos

## Estado Actual

**Filtros por Defecto (sin filtros especificados):**
- `origin_tag = 'cabinet'`
- `week_start >= (hoy - 7 días)` (última semana)
- `limit = 25` (máximo)

**Manejo de Timeout:**
- Retorna HTTP 503 con mensaje claro
- Muestra filtros aplicados
- Sugiere límite máximo de 25 y filtros muy restrictivos

## Limitaciones Conocidas

La vista `ops.v_payments_driver_matrix_cabinet` es inherentemente lenta debido a:
1. Múltiples CTEs complejos
2. Múltiples JOINs con vistas dependientes
3. Agregaciones complejas (GROUP BY, bool_or, MIN con FILTER)
4. Falta de índices en columnas filtradas frecuentemente

## Recomendaciones para Usuarios

### Query Mínima Recomendada
```
/api/v1/ops/payments/driver-matrix?origin_tag=cabinet&week_start_from=2025-12-30&limit=25
```

### Query Óptima
```
/api/v1/ops/payments/driver-matrix?origin_tag=cabinet&week_start_from=2025-12-30&funnel_status=reached_m5&only_pending=true&limit=25
```

### Filtros Críticos
1. **week_start_from:** Siempre usar fecha muy reciente (última semana)
2. **funnel_status:** Filtrar por estado específico
3. **only_pending:** Usar `true` para reducir dataset
4. **limit:** Máximo 25-50

## Próximos Pasos (Requeridos para Solución Definitiva)

### 1. Optimizar la Vista SQL (CRÍTICO)
- Agregar índices en `origin_tag`, `week_start`, `driver_id`
- Simplificar CTEs si es posible
- Considerar materializar la vista si es necesario

### 2. Crear Vista Materializada
```sql
CREATE MATERIALIZED VIEW ops.mv_payments_driver_matrix_cabinet AS
SELECT * FROM ops.v_payments_driver_matrix_cabinet;

CREATE INDEX ON ops.mv_payments_driver_matrix_cabinet(origin_tag, week_start);
```

### 3. Paginación Cursor-Based
- Reemplazar OFFSET por cursor-based pagination
- Más eficiente para datasets grandes

## Estado

✅ **IMPLEMENTADO** - El endpoint ahora:
- Aplica filtros por defecto muy restrictivos (última semana)
- Usa límite muy bajo por defecto (25)
- Maneja timeouts con mensajes claros
- Reduce límite automáticamente si no hay filtros

⚠️ **LIMITACIÓN CONOCIDA** - La vista requiere optimización arquitectural para ser realmente eficiente.

