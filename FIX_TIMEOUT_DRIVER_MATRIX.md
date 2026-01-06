# Fix: Timeout en Driver Matrix COUNT

## Problema

El endpoint `/api/v1/ops/payments/driver-matrix` estaba dando timeout al ejecutar `SELECT COUNT(*)` sobre `ops.v_payments_driver_matrix_cabinet`.

**Error:**
```
canceling statement due to statement timeout
[SQL: SELECT COUNT(*) AS total FROM ops.v_payments_driver_matrix_cabinet]
```

## Solución Implementada

### Estrategia: COUNT Opcional con Aproximación

1. **Ejecutar query principal primero** (más rápida con LIMIT)
   - Permite que el usuario vea resultados aunque el COUNT falle
   - La query con LIMIT es mucho más rápida

2. **COUNT con manejo de errores**
   - Intentar ejecutar el COUNT normalmente
   - Si falla por timeout, usar aproximación inteligente

3. **Aproximación inteligente:**
   - Si `returned >= limit`: Probablemente hay más resultados → `total = offset + returned + 1`
   - Si `returned < limit`: Probablemente es el total real → `total = offset + returned`

### Código Modificado

**Archivo:** `backend/app/api/v1/ops_payments.py`

**Cambios:**
- Reordenado: query principal primero, COUNT después
- Agregado try/except para manejar timeout en COUNT
- Aproximación cuando COUNT falla

## Beneficios

1. **Endpoint siempre responde** - Aunque el COUNT falle, los datos se muestran
2. **Aproximación razonable** - El total estimado es útil para paginación
3. **Logging** - Se registra cuando se usa aproximación para monitoreo
4. **Sin cambios en frontend** - El frontend recibe `total` (exacto o aproximado)

## Notas

- La aproximación es conservadora (mínimo estimado)
- Si hay exactamente `limit` resultados, se asume que hay más
- El total exacto solo se calcula si el COUNT no da timeout
- Para obtener total exacto, se puede optimizar la vista o agregar índices

## Próximos Pasos (Opcional)

1. **Optimizar la vista** - Agregar índices o materializar
2. **Cachear COUNT** - Si los filtros son comunes, cachear resultados
3. **Usar tabla de metadatos** - Mantener contadores actualizados

## Estado

✅ **IMPLEMENTADO** - El endpoint ahora maneja timeouts gracefully

