# Fix: KPIs Separados por Capas en Resumen por Conductor

## Objetivo

Separar los KPIs en `/pagos/resumen-conductor` en dos capas:
1. **KPIs de Claims (C3/C4)**: Basados en claims/pagos
2. **KPIs de Actividad (C1)**: Basados en milestones achieved (trips)

## Cambios Implementados

### 1. Backend - SQL de Totals (`backend/app/api/v1/payments.py`)

**ANTES:**
```sql
SELECT 
    COUNT(*) AS drivers,
    COALESCE(SUM(
        COALESCE(m1_expected_amount_yango, 0) +
        COALESCE(m5_expected_amount_yango, 0) +
        COALESCE(m25_expected_amount_yango, 0)
    ), 0) AS expected_yango_sum,
    -- ...
```

**DESPUÉS:**
```sql
SELECT 
    COUNT(*) AS drivers,
    -- KPIs de Claims (C3/C4): Solo donde existe claim
    COALESCE(SUM(
        CASE WHEN m1_expected_amount_yango IS NOT NULL THEN COALESCE(m1_expected_amount_yango, 0) ELSE 0 END +
        CASE WHEN m5_expected_amount_yango IS NOT NULL THEN COALESCE(m5_expected_amount_yango, 0) ELSE 0 END +
        CASE WHEN m25_expected_amount_yango IS NOT NULL THEN COALESCE(m25_expected_amount_yango, 0) ELSE 0 END
    ), 0) AS expected_yango_sum,
    -- ... (paid_sum, receivable_sum, expired_count, in_window_count también filtrados por claim)
    -- KPIs de Actividad (C1): Basados en achieved_flag (trips)
    COUNT(DISTINCT CASE WHEN m1_achieved_flag = true THEN driver_id END) AS achieved_m1_count,
    COUNT(DISTINCT CASE WHEN m5_achieved_flag = true THEN driver_id END) AS achieved_m5_count,
    COUNT(DISTINCT CASE WHEN m25_achieved_flag = true THEN driver_id END) AS achieved_m25_count,
    -- Achieved sin Claim
    COUNT(DISTINCT CASE WHEN m1_achieved_flag = true AND m1_yango_payment_status IS NULL THEN driver_id END) AS achieved_m1_without_claim_count,
    COUNT(DISTINCT CASE WHEN m5_achieved_flag = true AND m5_yango_payment_status IS NULL THEN driver_id END) AS achieved_m5_without_claim_count,
    COUNT(DISTINCT CASE WHEN m25_achieved_flag = true AND m25_yango_payment_status IS NULL THEN driver_id END) AS achieved_m25_without_claim_count
```

**Cambios clave:**
- `expected_yango_sum`: Solo suma donde `expected_amount_yango IS NOT NULL` (existe claim)
- `paid_sum`: Solo suma donde `payment_status IN ('PAID', 'PAID_MISAPPLIED')` y existe claim
- `receivable_sum`: Solo suma donde `payment_status IS NOT NULL` y no es PAID/PAID_MISAPPLIED y existe claim
- `expired_count` / `in_window_count`: Solo cuenta donde existe claim
- Nuevos KPIs de Actividad: Conteo de drivers con `achieved_flag = true` (trips)
- Nuevos KPIs "sin Claim": Conteo de drivers con `achieved_flag = true` pero `payment_status IS NULL`

### 2. Backend - Schema (`backend/app/schemas/payments.py`)

**ANTES:**
```python
class DriverMatrixTotals(BaseModel):
    drivers: int
    expected_yango_sum: Decimal
    paid_sum: Decimal
    receivable_sum: Decimal
    expired_count: int
    in_window_count: int
```

**DESPUÉS:**
```python
class DriverMatrixTotals(BaseModel):
    # KPIs de Claims (C3/C4): Basados en claims/pagos
    drivers: int
    expected_yango_sum: Decimal  # Suma de expected_amount_yango donde existe claim
    paid_sum: Decimal  # Suma donde status=PAID/PAID_MISAPPLIED
    receivable_sum: Decimal  # Expected - Paid
    expired_count: int  # Conteo por window_status='expired' de claims
    in_window_count: int  # Conteo por window_status='in_window' de claims
    # KPIs de Actividad (C1): Basados en milestones achieved (trips)
    achieved_m1_count: int = 0
    achieved_m5_count: int = 0
    achieved_m25_count: int = 0
    achieved_m1_without_claim_count: int = 0
    achieved_m5_without_claim_count: int = 0
    achieved_m25_without_claim_count: int = 0
```

### 3. Frontend - Types (`frontend/lib/types.ts`)

Actualizado `DriverMatrixTotals` para incluir los nuevos campos (opcionales para retrocompatibilidad).

### 4. Frontend - UI (`frontend/app/pagos/resumen-conductor/page.tsx`)

**ANTES:**
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
  <StatCard title="Drivers" value={data.totals.drivers} />
  <StatCard title="Expected Yango" value={`S/ ${...}`} />
  {/* ... */}
</div>
```

**DESPUÉS:**
```tsx
{/* KPIs de Claims (C3/C4) */}
<div className="mb-6">
  <h2 className="text-lg font-semibold text-gray-700 mb-3">📊 KPIs de Claims (C3/C4)</h2>
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
    <StatCard title="Drivers" value={data.totals.drivers} />
    <StatCard title="Expected Yango" value={`S/ ${...}`} subtitle="donde existe claim" />
    {/* ... */}
  </div>
</div>

{/* KPIs de Actividad (C1) */}
<div className="mb-6">
  <h2 className="text-lg font-semibold text-gray-700 mb-3">🚗 KPIs de Actividad (C1 - Trips)</h2>
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
    <StatCard title="Achieved M1" value={data.totals.achieved_m1_count || 0} subtitle="drivers con M1 achieved" />
    <StatCard title="Achieved M5" value={data.totals.achieved_m5_count || 0} subtitle="drivers con M5 achieved" />
    <StatCard title="Achieved M25" value={data.totals.achieved_m25_count || 0} subtitle="drivers con M25 achieved" />
    <StatCard title="M1 sin Claim" value={data.totals.achieved_m1_without_claim_count || 0} subtitle="achieved sin claim" variant="warning" />
    <StatCard title="M5 sin Claim" value={data.totals.achieved_m5_without_claim_count || 0} subtitle="achieved sin claim" variant="warning" />
    <StatCard title="M25 sin Claim" value={data.totals.achieved_m25_without_claim_count || 0} subtitle="achieved sin claim" variant="warning" />
  </div>
</div>
```

### 5. Frontend - StatCard Component (`frontend/components/StatCard.tsx`)

Agregado soporte para `variant` prop para mostrar KPIs "sin claim" con estilo warning (fondo amarillo).

## Reglas de Negocio Implementadas

### KPIs de Claims (C3/C4)
- **Expected Yango**: Suma de `expected_amount_yango` donde existe claim (`expected_amount_yango IS NOT NULL`)
- **Paid**: Suma donde `payment_status IN ('PAID', 'PAID_MISAPPLIED')` y existe claim
- **Receivable**: Expected - Paid (solo donde existe claim)
- **Expired / In Window**: Conteo por `window_status` de claims (solo donde existe claim)

### KPIs de Actividad (C1)
- **Achieved M1/M5/M25**: Conteo de drivers con `achieved_flag = true` (basado en trips)
- **Achieved sin Claim**: Conteo de drivers con `achieved_flag = true` pero `payment_status IS NULL`
  - **NO se suma a Expected**: Estos KPIs son informativos, no afectan los cálculos de claims

## Archivos Modificados

1. **`backend/app/api/v1/payments.py`**
   - Modificado SQL de `totals_sql` para separar KPIs por capas
   - Actualizado constructor de `DriverMatrixTotals` para incluir nuevos campos

2. **`backend/app/schemas/payments.py`**
   - Actualizado `DriverMatrixTotals` schema con nuevos campos y comentarios

3. **`frontend/lib/types.ts`**
   - Actualizado `DriverMatrixTotals` interface con nuevos campos opcionales

4. **`frontend/app/pagos/resumen-conductor/page.tsx`**
   - Separado KPIs en dos secciones visuales
   - Agregado títulos y subtítulos descriptivos

5. **`frontend/components/StatCard.tsx`**
   - Agregado soporte para `variant` prop (default, warning, success, error, info)

## Estado Esperado en UI

### Sección 1: KPIs de Claims (C3/C4)
```
📊 KPIs de Claims (C3/C4)
┌─────────┬─────────────────┬──────────┬─────────────┬──────────┬────────────┐
│ Drivers │ Expected Yango  │ Paid     │ Receivable  │ Expired  │ In Window  │
│   150   │ S/ 12,500.00    │ S/ 8,000 │ S/ 4,500.00 │    25    │    125     │
│         │ (donde existe   │ (PAID/   │ (Expected - │ (claims  │ (claims en │
│         │  claim)         │ PAID_...)│  Paid)      │ vencidos)│ ventana)   │
└─────────┴─────────────────┴──────────┴─────────────┴──────────┴────────────┘
```

### Sección 2: KPIs de Actividad (C1 - Trips)
```
🚗 KPIs de Actividad (C1 - Trips)
┌─────────────┬─────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
│ Achieved M1 │ Achieved M5 │ Achieved M25 │ M1 sin Claim │ M5 sin Claim │ M25 sin Claim│
│     120     │     80      │     30       │      15      │      10      │      5       │
│ (drivers con│ (drivers con│ (drivers con │ (achieved sin│ (achieved sin│ (achieved sin│
│  M1 achieved│  M5 achieved│  M25 achieved│  claim)      │  claim)      │  claim)      │
└─────────────┴─────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
```

Los KPIs "sin Claim" se muestran con fondo amarillo (variant="warning") para indicar que son informativos.

## Verificación

1. **Backend**: Verificar que el endpoint `/api/v1/payments/driver-matrix` retorna los nuevos campos en `totals`
2. **Frontend**: Verificar que `/pagos/resumen-conductor` muestra las dos secciones de KPIs
3. **Lógica**: Verificar que:
   - Expected Yango solo suma donde existe claim
   - Achieved counts cuentan drivers con `achieved_flag = true`
   - "Achieved sin Claim" cuenta drivers con `achieved_flag = true` pero `payment_status IS NULL`

## Notas Importantes

1. **Retrocompatibilidad**: Los nuevos campos en `DriverMatrixTotals` son opcionales (con valores por defecto) para mantener compatibilidad con código existente.

2. **No se modificaron**:
   - Vistas canónicas (`ops.v_payments_driver_matrix_cabinet`)
   - Exports (siguen funcionando igual)
   - Otros endpoints

3. **Separación de responsabilidades**:
   - **Claims (C3/C4)**: Basados en reglas de negocio y ventanas de pago
   - **Actividad (C1)**: Basados en viajes reales (trips)

4. **"Achieved sin Claim"**:
   - Son KPIs informativos (no se suman a Expected)
   - Indican drivers que alcanzaron milestones por trips pero no tienen claim asociado
   - Útiles para identificar gaps en el proceso de claims


