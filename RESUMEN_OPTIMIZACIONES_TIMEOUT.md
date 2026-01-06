# Resumen: Optimizaciones para Timeout en Driver Matrix

## Problema

La vista `ops.v_payments_driver_matrix_cabinet` es extremadamente lenta, dando timeout incluso con filtros básicos (`origin_tag = 'cabinet'`).

## Optimizaciones Implementadas

### 1. Filtros por Defecto Más Restrictivos ✅
- **Antes:** Solo `origin_tag = 'cabinet'`
- **Ahora:** 
  - `origin_tag = 'cabinet'`
  - `week_start >= (hoy - 30 días)` (último mes, en lugar de 3 meses)
  - Límite automático reducido a 50 si no hay filtros

### 2. Límite por Defecto Reducido ✅
- **Antes:** `limit = 200`
- **Ahora:** `limit = 50`
- **Razón:** Reduce significativamente la cantidad de datos a procesar

### 3. Manejo de Errores Mejorado ✅
- Mensajes de error más informativos
- Muestra qué filtros se aplicaron
- Sugiere acciones concretas (reducir límite a 25-50, agregar filtros)

### 4. Reducción Automática de Límite ✅
- Si no hay filtros y el límite es > 50, se reduce automáticamente a 50

## Estado Actual

**Filtros por Defecto (sin filtros especificados):**
- `origin_tag = 'cabinet'`
- `week_start >= (hoy - 30 días)`
- `limit = 50` (máximo)

**Manejo de Timeout:**
- Retorna HTTP 503 con mensaje claro
- Muestra filtros aplicados
- Sugiere acciones concretas

## Recomendaciones para Usuarios

1. **Siempre usar filtros:**
   - `week_start_from`: Fecha reciente (último mes)
   - `funnel_status`: Filtrar por estado específico
   - `only_pending=true`: Solo pendientes

2. **Límites recomendados:**
   - Sin filtros: 25-50
   - Con filtros básicos: 50-100
   - Con filtros restrictivos: 100-200

3. **Ejemplo de query eficiente:**
   ```
   /api/v1/ops/payments/driver-matrix?origin_tag=cabinet&week_start_from=2025-12-01&funnel_status=reached_m5&only_pending=true&limit=50
   ```

## Próximos Pasos (Si Persiste)

1. **Optimizar la Vista SQL:**
   - Agregar índices en columnas filtradas frecuentemente
   - Materializar la vista si es necesario
   - Simplificar CTEs complejos

2. **Cachear Resultados:**
   - Cachear COUNT para filtros comunes
   - Usar Redis o similar

3. **Paginación Cursor-Based:**
   - Reemplazar OFFSET por cursor-based pagination
   - Más eficiente para datasets grandes

## Estado

✅ **IMPLEMENTADO** - El endpoint ahora:
- Aplica filtros por defecto muy restrictivos
- Usa límite bajo por defecto (50)
- Maneja timeouts con mensajes claros
- Reduce límite automáticamente si no hay filtros

