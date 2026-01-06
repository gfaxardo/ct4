# Fix Completo: Timeout en Driver Matrix

## Problema

El endpoint `/api/v1/ops/payments/driver-matrix` estaba dando timeout tanto en:
1. `SELECT COUNT(*)` - Query de conteo
2. `SELECT * ... LIMIT 200` - Query principal con datos

**Error:**
```
canceling statement due to statement timeout
```

## Solución Implementada

### 1. Filtro por Defecto
- Si no se especifican filtros, se aplica automáticamente `origin_tag = 'cabinet'`
- Esto reduce significativamente el dataset y previene timeouts
- Se loguea cuando se aplica el filtro por defecto

### 2. Manejo de Timeout en Query Principal
- Try/except alrededor de la query principal
- Si falla por timeout:
  - Si hay pocos filtros: Mensaje sugiriendo agregar filtros más restrictivos
  - Si ya hay filtros: Mensaje sugiriendo reducir límite o agregar más filtros
- Retorna HTTP 503 (Service Unavailable) con mensaje claro

### 3. Manejo de Timeout en COUNT
- Try/except alrededor del COUNT
- Si falla por timeout, usa aproximación inteligente:
  - Si `returned >= limit`: `total = offset + returned + 1` (mínimo estimado)
  - Si `returned < limit`: `total = offset + returned` (total real)

## Cambios en Código

**Archivo:** `backend/app/api/v1/ops_payments.py`

### Cambio 1: Filtro por Defecto
```python
# Si no hay filtros, agregar filtro mínimo por defecto
if not where_conditions:
    where_conditions.append("origin_tag = 'cabinet'")
    params["origin_tag_default"] = 'cabinet'
    logger.info("Sin filtros especificados, aplicando filtro por defecto: origin_tag='cabinet'")
```

### Cambio 2: Manejo de Timeout en Query Principal
```python
try:
    result = db.execute(text(sql), params)
    rows = result.fetchall()
except (ProgrammingError, OperationalError) as e:
    if "timeout" in error_msg.lower():
        # Retornar HTTP 503 con mensaje claro
        raise HTTPException(status_code=503, detail="...")
```

### Cambio 3: Manejo de Timeout en COUNT
```python
try:
    count_result = db.execute(text(count_sql), params)
    total = count_result.scalar() or 0
except (ProgrammingError, OperationalError) as e:
    # Usar aproximación si falla
    if len(rows) >= limit:
        total = offset + len(rows) + 1
    else:
        total = offset + len(rows)
```

## Beneficios

1. **Endpoint más resiliente** - Maneja timeouts gracefully
2. **Filtro por defecto** - Previene queries sobre toda la vista
3. **Mensajes claros** - Usuario sabe qué hacer si hay timeout
4. **Aproximación útil** - COUNT aproximado es mejor que nada
5. **Logging** - Se registra cuando se aplica filtro por defecto o hay timeout

## Comportamiento

### Sin Filtros
- Se aplica automáticamente `origin_tag = 'cabinet'`
- Query es más rápida
- Se loguea la aplicación del filtro

### Con Filtros
- Se respetan los filtros especificados
- Si aún da timeout, se sugiere agregar más filtros

### Timeout en Query Principal
- Retorna HTTP 503 con mensaje claro
- Sugiere agregar filtros más restrictivos

### Timeout en COUNT
- Usa aproximación inteligente
- Endpoint sigue funcionando
- Se loguea el uso de aproximación

## Estado

✅ **IMPLEMENTADO** - El endpoint ahora:
- Aplica filtro por defecto si no hay filtros
- Maneja timeouts en query principal
- Maneja timeouts en COUNT con aproximación
- Retorna mensajes claros al usuario

