# Migración Frontend: Driver Matrix CT4

**Fecha:** 2025-01-XX  
**Objetivo:** Migrar consumo de `ops.v_payments_driver_matrix_cabinet` a `ops.v_payments_driver_matrix_ct4` para drivers CT4 (cabinet + fleet_migration).

---

## Cambios Necesarios

### 1. Endpoint Backend

**Archivo:** `backend/app/api/v1/payments.py`

**Cambio:** Modificar endpoint `/api/v1/payments/driver-matrix` para usar `ops.v_payments_driver_matrix_ct4` cuando `origin_tag IN ('cabinet', 'fleet_migration')`.

**Opción A (Recomendada):** Crear endpoint nuevo `/api/v1/payments/driver-matrix-ct4` y migrar consumo del frontend gradualmente.

**Opción B:** Modificar endpoint existente para detectar `origin_tag` y usar vista CT4 automáticamente.

**Código sugerido (Opción A):**

```python
@router.get("/driver-matrix-ct4", response_model=DriverMatrixResponse)
def get_driver_matrix_ct4(
    # ... mismos parámetros que get_driver_matrix
):
    """
    Obtiene la matriz de drivers CT4 con achieved determinístico.
    Similar a /driver-matrix pero usa ops.v_payments_driver_matrix_ct4.
    """
    # Mismo código que get_driver_matrix pero cambiando:
    # FROM ops.v_payments_driver_matrix_cabinet
    # a:
    # FROM ops.v_payments_driver_matrix_ct4
```

---

### 2. Frontend: Cambiar Consumo de API

**Archivo:** `frontend/lib/api.ts`

**Cambio:** Agregar función nueva o modificar existente para usar endpoint CT4.

**Código sugerido:**

```typescript
// Nueva función para CT4
export async function getDriverMatrixCT4(params: {
  week_from?: string;
  week_to?: string;
  search?: string;
  only_pending?: boolean;
  page?: number;
  limit?: number;
}): Promise<DriverMatrixResponse> {
  const query = new URLSearchParams();
  // ... construir query igual que getDriverMatrix
  return fetchApi<DriverMatrixResponse>(`/api/v1/payments/driver-matrix-ct4${query ? `?${query}` : ''}`);
}
```

---

### 3. Frontend: Agregar Badges y Señalización

**Archivo:** `frontend/app/pagos/driver-matrix/page.tsx`

**Cambios:**

#### 3.1. Badge "Achieved por viajes (CT4)"

Agregar badge informativo similar al de reconciliación:

```tsx
<div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
  <div className="flex items-center gap-2">
    <Badge variant="info">Achieved por viajes (CT4)</Badge>
    <span className="text-sm text-gray-700">
      Los milestones achieved se calculan determinísticamente desde viajes reales (summary_daily).
      Garantiza consistencia: si M5=true, entonces M1=true.
    </span>
  </div>
</div>
```

#### 3.2. Badge "Inconsistente (Legacy)"

Mostrar badge cuando `legacy_inconsistency_flag = true`:

```tsx
{row.legacy_inconsistency_flag && (
  <Badge variant="warning" className="ml-2">
    Inconsistente (Legacy)
  </Badge>
)}
```

#### 3.3. Caja Informativa "Cómo interpretar"

Agregar caja gris similar a reconciliación:

```tsx
<div className="mt-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
  <h3 className="font-semibold text-gray-900 mb-2">Cómo interpretar</h3>
  <ul className="text-sm text-gray-700 space-y-1">
    <li>• <strong>Achieved por viajes (CT4):</strong> Milestones calculados determinísticamente desde viajes reales.</li>
    <li>• <strong>Garantiza consistencia:</strong> Si M5=true, entonces M1=true automáticamente.</li>
    <li>• <strong>Inconsistente (Legacy):</strong> Este driver tenía inconsistencias en el sistema legacy (M5 sin M1).</li>
    <li>• <strong>Pagos:</strong> Los estados de pago (PAID, UNPAID) vienen del ledger Yango (sin cambios).</li>
  </ul>
</div>
```

---

### 4. Frontend: Actualizar Tipos TypeScript

**Archivo:** `frontend/lib/types.ts`

**Cambio:** Agregar campos nuevos a `DriverMatrixRow`:

```typescript
export interface DriverMatrixRow {
  // ... campos existentes ...
  
  // Nuevos campos CT4
  achieved_source?: string;  // 'TRIPS_CT4'
  legacy_inconsistency_flag?: boolean;  // true si legacy tenía inconsistencias
}
```

---

## Plan de Migración Gradual

### Fase 1: Preparación (Sin cambios en producción)
1. ✅ Crear vistas SQL nuevas (`v_ct4_driver_achieved_from_trips`, `v_payments_driver_matrix_ct4`)
2. ✅ Validar vistas con runbook
3. ✅ Crear endpoint nuevo `/api/v1/payments/driver-matrix-ct4`

### Fase 2: Pruebas
1. Agregar endpoint CT4 al backend
2. Agregar función `getDriverMatrixCT4` al frontend
3. Crear página de prueba `/pagos/driver-matrix-ct4` (opcional)
4. Validar que datos sean consistentes

### Fase 3: Migración
1. Cambiar consumo en `frontend/app/pagos/driver-matrix/page.tsx` para usar endpoint CT4
2. Agregar badges y señalización
3. Deploy a producción
4. Monitorear por 1 semana

### Fase 4: Limpieza (Opcional)
1. Deprecar endpoint legacy si ya no se usa
2. Remover código legacy si es seguro

---

## Validación Post-Migración

Después de migrar, verificar:

1. ✅ UI muestra badge "Achieved por viajes (CT4)"
2. ✅ No hay inconsistencias M5 sin M1 en la UI
3. ✅ Badge "Inconsistente (Legacy)" aparece solo cuando corresponde
4. ✅ Caja "Cómo interpretar" es visible
5. ✅ Performance: tiempos de carga < 5 segundos

---

## Rollback

Si hay problemas, rollback inmediato:

1. Revertir cambios en `frontend/app/pagos/driver-matrix/page.tsx`
2. Volver a usar endpoint `/api/v1/payments/driver-matrix` (legacy)
3. Las vistas SQL nuevas no afectan el sistema legacy (son read-only)

---

## Referencias

- **Vista CT4:** `backend/sql/ops/v_payments_driver_matrix_ct4.sql`
- **Endpoint Backend:** `backend/app/api/v1/payments.py`
- **Página Frontend:** `frontend/app/pagos/driver-matrix/page.tsx`
- **Runbook Validación:** `docs/runbooks/validacion_driver_matrix_ct4.md`






