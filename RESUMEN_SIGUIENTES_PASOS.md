# Resumen: Siguientes Pasos - Capa Operativa 14d

## ✅ Completado

1. ✅ Vista `ops.v_cabinet_ops_14d_sanity` creada
2. ✅ Vista `ops.v_payments_driver_matrix_cabinet` enriquecida
3. ✅ Schema Pydantic actualizado con columnas operativas
4. ✅ Scripts de verificación funcionando

## 🎯 Próximos Pasos Inmediatos

### 1. Reiniciar Servidor FastAPI
**Acción:** Reiniciar el servidor para que el schema actualizado surta efecto.

```bash
# Si está corriendo con uvicorn
# Detener y reiniciar:
uvicorn app.main:app --reload
```

### 2. Verificar Endpoint Expone Columnas
**Comando:**
```bash
curl "http://localhost:8000/api/v1/ops/payments/driver-matrix?origin_tag=cabinet&limit=1" | jq '.data[0] | {connection_within_14d_flag, trips_completed_14d_from_lead}'
```

**Resultado esperado:**
```json
{
  "connection_within_14d_flag": true,
  "trips_completed_14d_from_lead": 17
}
```

### 3. Actualizar Tipos TypeScript
**Archivo:** `frontend/lib/types.ts`

**Agregar a `DriverMatrixRow`:**
```typescript
connection_within_14d_flag?: boolean;
connection_date_within_14d?: string;
trips_completed_14d_from_lead?: number;
first_trip_date_within_14d?: string;
```

## 📋 Checklist de Implementación

- [x] Schema Pydantic actualizado
- [ ] Servidor FastAPI reiniciado
- [ ] Endpoint verificado (retorna columnas)
- [ ] Tipos TypeScript actualizados
- [ ] UI muestra columnas (opcional)
- [ ] CSV export actualizado (opcional)

## 📚 Documentación

- `SIGUIENTES_PASOS.md` - Guía detallada de pasos
- `OPS_14D_SANITY_AND_DRIVER_MATRIX.md` - Documentación técnica
- `ESTADO_OPERATIVO_FINAL.md` - Estado actual del sistema

## 🚀 Estado Actual

**Backend:** ✅ Listo (schema actualizado, requiere reinicio)
**Frontend:** ⏳ Pendiente (actualizar tipos TypeScript)
**UI:** ⏳ Opcional (mostrar columnas en sección expandida)

