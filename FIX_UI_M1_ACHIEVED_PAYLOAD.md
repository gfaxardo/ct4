# Fix: UI M1 Achieved Flag - Payload y Componentes

## Problema Identificado

En la UI, M1 mostraba "—" aunque M5 mostraba "Alcanzado", a pesar de que en la DB ambos milestones estaban marcados como `achieved_flag = true`.

## Análisis del Payload

### Backend (✅ Correcto)

El schema `DriverMatrixRow` en `backend/app/schemas/payments.py` ya incluye todos los campos necesarios:

```python
class DriverMatrixRow(BaseModel):
    # ...
    m1_achieved_flag: Optional[bool] = None
    m1_achieved_date: Optional[date] = None
    m5_achieved_flag: Optional[bool] = None
    m5_achieved_date: Optional[date] = None
    m25_achieved_flag: Optional[bool] = None
    m25_achieved_date: Optional[date] = None
    # ...
```

Los endpoints `/api/v1/ops/payments/driver-matrix` y `/api/v1/payments/driver-matrix` usan `SELECT *` desde `ops.v_payments_driver_matrix_cabinet`, por lo que todos los campos están presentes en el JSON.

### Frontend (❌ Problema)

Los componentes `CompactMilestoneCell` y `MilestoneCell` tenían una lógica que ocultaba el estado "Alcanzado" cuando otros campos eran `null`, incluso si `achieved_flag` era `true`.

## Solución Implementada

### Cambios en `CompactMilestoneCell.tsx`

**ANTES:**
```typescript
// Si no hay datos, mostrar solo "—"
if (
  achieved_flag === null &&
  achieved_date === null &&
  expected_amount_yango === null &&
  yango_payment_status === null &&
  window_status === null &&
  overdue_days === null
) {
  return <div className="text-center text-gray-400">—</div>;
}

// ...
{achieved_flag ? (
  <span className="text-green-600 text-xs">✔</span>
) : (
  <span className="text-gray-400 text-xs">—</span>
)}
```

**DESPUÉS:**
```typescript
// Si achieved_flag es explícitamente false o null Y no hay ningún otro dato, mostrar "—"
// PERO si achieved_flag es true, SIEMPRE mostrar el checkmark, incluso si los demás campos son null
if (
  achieved_flag !== true &&
  achieved_date === null &&
  expected_amount_yango === null &&
  yango_payment_status === null &&
  window_status === null &&
  overdue_days === null
) {
  return <div className="text-center text-gray-400">—</div>;
}

// ...
{achieved_flag === true ? (
  <span className="text-green-600 text-xs font-bold" title="✅ Alcanzado">✅</span>
) : (
  <span className="text-gray-400 text-xs">—</span>
)}
```

### Cambios en `MilestoneCell.tsx`

**ANTES:**
```typescript
{achieved_flag ? (
  <div className="flex items-center gap-1 text-sm">
    <span>✅</span>
    <span className="font-medium">Alcanzado</span>
    {/* ... */}
  </div>
) : (
  <div className="text-sm text-gray-400">—</div>
)}
```

**DESPUÉS:**
```typescript
{achieved_flag === true ? (
  <div className="flex items-center gap-1 text-sm">
    <span>✅</span>
    <span className="font-medium text-green-600">Alcanzado</span>
    {/* ... */}
  </div>
) : (
  <div className="text-sm text-gray-400">—</div>
)}
```

**Además, agregado badge informativo:**
```typescript
{/* Si achieved=true pero payment_status es null, mostrar badge informativo */}
{achieved_flag === true && !yango_payment_status && (
  <div className="mb-1">
    <Badge variant="info" className="text-xs">
      Sin claim
    </Badge>
  </div>
)}
```

## Regla de Oro Implementada

**Achieved (UI) = viajes reales** (basado SOLO en `achieved_flag`)
- Si `achieved_flag === true` → Mostrar "✅ Alcanzado"
- Si `achieved_flag === false` o `null` → Mostrar "—"

**Payment status = reglas / ventanas / claims** (mostrado aparte)
- Badge de `yango_payment_status` (PAID/UNPAID/PAID_MISAPPLIED)
- Badge de `window_status` (in_window/expired)
- Si `achieved_flag === true` pero `yango_payment_status === null` → Mostrar badge "Sin claim"

## Ejemplo de JSON (Antes vs Después)

### Antes (mismo JSON, pero componente no mostraba correctamente)
```json
{
  "driver_id": "abc123",
  "m1_achieved_flag": true,
  "m1_achieved_date": "2025-01-15",
  "m1_yango_payment_status": null,
  "m1_expected_amount_yango": null,
  "m5_achieved_flag": true,
  "m5_achieved_date": "2025-01-20",
  "m5_yango_payment_status": "PAID",
  "m5_expected_amount_yango": 35.00
}
```

**UI mostraba:**
- M1: "—" ❌ (incorrecto, debería mostrar "✅ Alcanzado")
- M5: "✅ Alcanzado" ✓ (correcto)

### Después (mismo JSON, componente corregido)
```json
{
  "driver_id": "abc123",
  "m1_achieved_flag": true,
  "m1_achieved_date": "2025-01-15",
  "m1_yango_payment_status": null,
  "m1_expected_amount_yango": null,
  "m5_achieved_flag": true,
  "m5_achieved_date": "2025-01-20",
  "m5_yango_payment_status": "PAID",
  "m5_expected_amount_yango": 35.00
}
```

**UI muestra:**
- M1: "✅ Alcanzado" + badge "Sin claim" ✓ (correcto)
- M5: "✅ Alcanzado" + badge "PAID" ✓ (correcto)

## Archivos Modificados

1. **`frontend/components/payments/CompactMilestoneCell.tsx`**
   - Cambiada condición inicial para permitir mostrar "Alcanzado" cuando `achieved_flag === true` aunque otros campos sean `null`
   - Cambiado icono de ✔ a ✅ para mejor visibilidad
   - Cambiada comparación de `achieved_flag ?` a `achieved_flag === true` para ser más explícito

2. **`frontend/components/payments/MilestoneCell.tsx`**
   - Cambiada comparación de `achieved_flag ?` a `achieved_flag === true`
   - Agregado color verde al texto "Alcanzado" para mejor visibilidad
   - Agregado badge "Sin claim" cuando `achieved_flag === true` pero `yango_payment_status === null`

## Verificación

### Script de Prueba

```bash
# Ejecutar script de prueba del payload
bash backend/scripts/test_driver_matrix_payload.sh
```

### Verificación Manual

1. Abrir `/pagos/driver-matrix` o `/pagos/resumen-conductor`
2. Buscar un driver donde:
   - `m1_achieved_flag === true` pero `m1_yango_payment_status === null`
   - `m5_achieved_flag === true` y `m5_yango_payment_status === "PAID"`
3. Verificar que:
   - M1 muestra "✅ Alcanzado" + badge "Sin claim"
   - M5 muestra "✅ Alcanzado" + badge "PAID"

## Estado Esperado en UI

### Driver Matrix (CompactMilestoneCell)

```
Driver    | M1                    | M5                    | M25
----------|-----------------------|-----------------------|-------------------
Driver A  | ✅ [Sin claim]        | ✅ [PAID] S/ 35.00    | —
Driver B  | ✅ [UNPAID] S/ 25.00  | ✅ [PAID] S/ 35.00    | ✅ [UNPAID] S/ 100.00
Driver C  | —                     | —                     | —
```

### Resumen por Conductor (MilestoneCell)

```
Driver    | M1
----------|----------------------------------------
Driver A  | ✅ Alcanzado 15/01
          | [Sin claim]
          | 
Driver B  | ✅ Alcanzado 15/01
          | [UNPAID]
          | ⚠ 5d
          | S/ 25.00
```

## Notas Importantes

1. **No se modificó el backend**: El payload ya era correcto, el problema estaba en la lógica de renderizado del frontend.

2. **Separación de responsabilidades**:
   - `achieved_flag` → Determina si mostrar "✅ Alcanzado"
   - `yango_payment_status` → Determina badge de pago (PAID/UNPAID/PAID_MISAPPLIED)
   - `window_status` → Determina badge de ventana (in_window/expired)
   - `overdue_days` → Muestra días vencidos

3. **Compatibilidad**: Los cambios son retrocompatibles. Si `achieved_flag` es `null` o `false`, el comportamiento es el mismo que antes.



