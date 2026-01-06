# Optimización Final: Timeout en Driver Matrix

## Problema Identificado

Aunque el filtro por defecto `origin_tag = 'cabinet'` se aplica correctamente, la vista `ops.v_payments_driver_matrix_cabinet` sigue siendo extremadamente lenta y da timeout incluso con ese filtro.

**Evidencia del log:**
```
INFO: Sin filtros especificados, aplicando filtro por defecto: origin_tag='cabinet'
ERROR: Query principal timeout en driver-matrix: ... WHERE origin_tag = 'cabinet'
```

## Solución Adicional Implementada

### 1. Reducción del Límite por Defecto
- **Antes:** `limit = 200` (default)
- **Ahora:** `limit = 100` (default)
- **Razón:** Reduce la cantidad de datos a procesar y ordenar

### 2. Filtro de Fecha por Defecto
- **Agregado:** `week_start >= (hoy - 90 días)` cuando no hay filtros
- **Razón:** Limita el dataset a los últimos 3 meses, reduciendo significativamente el tamaño
- **Combinado con:** `origin_tag = 'cabinet'`

### 3. Manejo de Errores Mejorado
- El endpoint ya maneja timeouts en query principal
- Retorna HTTP 503 con mensaje claro
- Sugiere agregar filtros más restrictivos

## Cambios en Código

**Archivo:** `backend/app/api/v1/ops_payments.py`

### Cambio 1: Límite Reducido
```python
limit: int = Query(100, ge=1, le=1000, description="...")
```

### Cambio 2: Filtro de Fecha por Defecto
```python
if not where_conditions:
    where_conditions.append("origin_tag = 'cabinet'")
    # Agregar filtro de fecha reciente (últimos 3 meses)
    from datetime import timedelta
    three_months_ago = date.today() - timedelta(days=90)
    where_conditions.append("week_start >= :week_start_from_default")
    params["week_start_from_default"] = three_months_ago
```

## Comportamiento Esperado

### Sin Filtros Especificados
1. Se aplica automáticamente:
   - `origin_tag = 'cabinet'`
   - `week_start >= (hoy - 90 días)`
2. Límite por defecto: 100 (en lugar de 200)
3. Query debería ser más rápida

### Con Filtros Especificados
- Se respetan los filtros del usuario
- Si aún da timeout, se sugiere agregar más filtros

### Timeout Persistente
- Si aún da timeout con filtros por defecto, el endpoint:
  - Retorna HTTP 503
  - Muestra mensaje claro
  - Sugiere agregar filtros más restrictivos

## Próximos Pasos (Si Persiste el Problema)

1. **Optimizar la Vista SQL**
   - Agregar índices en columnas frecuentemente filtradas
   - Materializar la vista si es necesario
   - Simplificar la lógica de la vista

2. **Cachear Resultados**
   - Cachear COUNT para filtros comunes
   - Usar Redis o similar

3. **Paginación Más Eficiente**
   - Usar cursor-based pagination en lugar de OFFSET
   - Reducir aún más el límite por defecto

## Estado

✅ **IMPLEMENTADO** - El endpoint ahora:
- Aplica filtros por defecto más restrictivos (origin_tag + fecha)
- Usa límite más bajo por defecto (100)
- Maneja timeouts gracefully
- Retorna mensajes claros al usuario

