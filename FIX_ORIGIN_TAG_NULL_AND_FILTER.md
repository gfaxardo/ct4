# Fix: Origin Tag NULL y Filtro No Funcional

## Problema Identificado

1. **Columna ORIGIN muestra "—" (NULL)** para muchos drivers
   - Ocurre cuando drivers tienen milestones achieved pero no están en `v_payment_calculation` con `origin_tag IN ('cabinet', 'fleet_migration')`
   - El `LEFT JOIN` con `origin_and_connected_data` deja `origin_tag` como NULL

2. **Filtro "Origin Tag" no funciona completamente**
   - Backend solo aceptaba 'cabinet' o 'fleet_migration'
   - Frontend solo tenía opciones 'cabinet' y 'fleet_migration'
   - No había opción para filtrar 'unknown' o mostrar 'All'

## Solución Implementada

### PASO A — Fix SQL

**Archivo**: `backend/sql/ops/v_payments_driver_matrix_cabinet.sql`

**Cambio**: Asegurar que `origin_tag` nunca sea NULL usando `COALESCE` con prioridad:
- `cabinet` (si existe)
- `fleet_migration` (si existe)
- `unknown` (default)

```sql
-- origin_tag: prioridad: cabinet > fleet_migration > unknown
-- Asegurar que nunca sea NULL
COALESCE(
    MAX(CASE WHEN ocd.origin_tag = 'cabinet' THEN 'cabinet' END),
    MAX(CASE WHEN ocd.origin_tag = 'fleet_migration' THEN 'fleet_migration' END),
    'unknown'
) AS origin_tag,
```

**Resultado**: Todos los drivers ahora tienen `origin_tag` con valor 'cabinet', 'fleet_migration' o 'unknown' (nunca NULL).

### PASO B — Fix Backend

**Archivos**: 
- `backend/app/api/v1/ops_payments.py`
- `backend/app/api/v1/payments.py`

**Cambios**:
1. Aceptar `origin_tag='unknown'` además de 'cabinet' y 'fleet_migration'
2. Aceptar `origin_tag='All'` o vacío para no filtrar
3. Validación actualizada con mensaje de error claro

```python
if origin_tag:
    # Validar que sea uno de los valores permitidos
    # 'All' o vacío => no filtra
    if origin_tag.lower() == 'all' or origin_tag == '':
        # No agregar filtro
        pass
    elif origin_tag in ('cabinet', 'fleet_migration', 'unknown'):
        where_conditions.append("origin_tag = :origin_tag")
        params["origin_tag"] = origin_tag
    else:
        raise HTTPException(
            status_code=400,
            detail=f"origin_tag debe ser 'cabinet', 'fleet_migration', 'unknown' o 'All', recibido: {origin_tag}"
        )
```

**Resultado**: Los endpoints ahora aceptan y filtran correctamente por 'cabinet', 'fleet_migration' y 'unknown'.

### PASO C — Fix Frontend

**Archivos**:
- `frontend/app/pagos/driver-matrix/page.tsx`
- `frontend/lib/api.ts`

**Cambios**:
1. Agregar opción 'unknown' al dropdown de Origin Tag
2. Actualizar validación para aceptar 'unknown'
3. Mostrar 'unknown' con badge warning en lugar de "—"
4. Actualizar API client para enviar 'unknown'

```typescript
// Helper actualizado
const getValidOriginTag = (value: string | null): string => {
  if (value === 'cabinet' || value === 'fleet_migration' || value === 'unknown') return value;
  if (value === 'All' || value === '') return '';
  return '';
};

// Dropdown actualizado
<select>
  <option value="">All</option>
  <option value="cabinet">cabinet</option>
  <option value="fleet_migration">fleet_migration</option>
  <option value="unknown">unknown</option>
</select>

// Render actualizado
render: (row: DriverMatrixRow) =>
  row.origin_tag ? (
    <Badge variant={row.origin_tag === 'cabinet' ? 'info' : row.origin_tag === 'unknown' ? 'warning' : 'default'}>
      {row.origin_tag}
    </Badge>
  ) : (
    <Badge variant="warning">unknown</Badge>
  ),
```

**Resultado**: 
- Dropdown ahora tiene opciones: All, cabinet, fleet_migration, unknown
- Columna ORIGIN muestra badge con 'unknown' en lugar de "—"
- Filtro funciona correctamente para todos los valores

## Archivos Modificados

1. **`backend/sql/ops/v_payments_driver_matrix_cabinet.sql`**
   - Cambio en cálculo de `origin_tag` para usar `COALESCE` con 'unknown' como default

2. **`backend/app/api/v1/ops_payments.py`**
   - Actualización de validación de `origin_tag` para aceptar 'unknown' y 'All'

3. **`backend/app/api/v1/payments.py`**
   - Agregado parámetro `origin_tag` al endpoint
   - Implementado filtro por `origin_tag` con validación

4. **`frontend/app/pagos/driver-matrix/page.tsx`**
   - Actualizado helper `getValidOriginTag` para aceptar 'unknown'
   - Agregada opción 'unknown' al dropdown
   - Actualizado render de columna ORIGIN para mostrar badge 'unknown'

5. **`frontend/lib/api.ts`**
   - Actualizado `getOpsDriverMatrix` para aceptar 'unknown' en `origin_tag`

## Comandos para Aplicar

### 1. Aplicar Vista SQL Modificada

```bash
psql $DATABASE_URL -f backend/sql/ops/v_payments_driver_matrix_cabinet.sql
```

### 2. Reiniciar Backend (si está corriendo)

```bash
# Detener backend (Ctrl+C)
# Reiniciar backend
cd backend
python -m uvicorn app.main:app --reload
```

### 3. Reiniciar Frontend (si está corriendo)

```bash
# Detener frontend (Ctrl+C)
# Reiniciar frontend
cd frontend
npm run dev
```

## Verificación

### API

1. **Sin filtro** (debe devolver mezcla):
```bash
curl "http://localhost:8000/api/v1/ops/payments/driver-matrix?limit=10"
```

2. **Filtro cabinet** (debe devolver solo cabinet):
```bash
curl "http://localhost:8000/api/v1/ops/payments/driver-matrix?origin_tag=cabinet&limit=10"
```

3. **Filtro fleet_migration** (debe devolver solo fleet_migration):
```bash
curl "http://localhost:8000/api/v1/ops/payments/driver-matrix?origin_tag=fleet_migration&limit=10"
```

4. **Filtro unknown** (debe devolver solo unknown):
```bash
curl "http://localhost:8000/api/v1/ops/payments/driver-matrix?origin_tag=unknown&limit=10"
```

### UI

1. **Columna ORIGIN**: No debe mostrar "—", debe mostrar badge con 'cabinet', 'fleet_migration' o 'unknown'
2. **Dropdown Origin Tag**: Debe tener opciones: All, cabinet, fleet_migration, unknown
3. **Filtro**: Al seleccionar cada opción, debe filtrar correctamente:
   - All: muestra todos
   - cabinet: solo drivers con origin_tag='cabinet'
   - fleet_migration: solo drivers con origin_tag='fleet_migration'
   - unknown: solo drivers con origin_tag='unknown'

## Ejemplo de Request URL

**ANTES**:
```
/api/v1/ops/payments/driver-matrix?origin_tag=cabinet
```
(Solo aceptaba 'cabinet' o 'fleet_migration')

**DESPUÉS**:
```
/api/v1/ops/payments/driver-matrix?origin_tag=cabinet
/api/v1/ops/payments/driver-matrix?origin_tag=fleet_migration
/api/v1/ops/payments/driver-matrix?origin_tag=unknown
/api/v1/ops/payments/driver-matrix
```
(Acepta 'cabinet', 'fleet_migration', 'unknown' o sin filtro para 'All')

## Notas Importantes

1. **Grano NO cambió**: La vista sigue teniendo EXACTAMENTE 1 fila por `driver_id`

2. **origin_tag nunca es NULL**: Todos los drivers ahora tienen un valor ('cabinet', 'fleet_migration' o 'unknown')

3. **Prioridad de origen**: Si un driver tiene múltiples orígenes, se prioriza 'cabinet' > 'fleet_migration' > 'unknown'

4. **Compatibilidad**: Los endpoints existentes siguen funcionando, solo se agregó soporte para 'unknown' y 'All'


