# Fix Completo: Funnel C1 + Claims Fix + Origin Tag + Frontend Unificado

## Resumen

Implementación completa de:
1. Vista canónica C1 (Funnel) con estados operativos
2. Fix de claims sin milestone achieved (violación canónica)
3. Origin tag NO NULL y filtro funcional
4. Driver Matrix con columna "Estado" y tabs Tabla/KPIs
5. Unificación Driver Matrix + Resumen por Conductor

## Archivos Modificados

### SQL (Backend)

1. **`backend/sql/ops/v_cabinet_funnel_status.sql`** (NUEVO)
   - Vista canónica C1: 1 fila por driver_id
   - Estados: registered_incomplete, registered_complete, connected_no_trips, reached_m1, reached_m5, reached_m25
   - Fuentes: identity_links, v_conversion_metrics, v_cabinet_milestones_achieved_from_trips

2. **`backend/sql/ops/v_claims_payment_status_cabinet.sql`**
   - Agregado `INNER JOIN` con `v_cabinet_milestones_achieved_from_trips`
   - Solo genera claims si existe milestone determinístico

3. **`backend/sql/ops/v_payments_driver_matrix_cabinet.sql`**
   - Agregado `funnel_status` y `highest_milestone` desde `v_cabinet_funnel_status`
   - Protección: payment info solo si `achieved_flag = true`
   - Origin tag nunca NULL (prioridad: cabinet > fleet_migration > unknown)

### Backend (Python)

4. **`backend/app/schemas/payments.py`**
   - Agregado `funnel_status` y `highest_milestone` a `DriverMatrixRow`

5. **`backend/app/api/v1/ops_payments.py`**
   - Agregado filtro `funnel_status` en query params
   - Validación de valores permitidos

6. **`backend/app/api/v1/payments.py`**
   - Agregado filtro `funnel_status` en query params
   - Validación de valores permitidos

### Frontend (TypeScript/React)

7. **`frontend/lib/types.ts`**
   - Agregado `funnel_status` y `highest_milestone` a `DriverMatrixRow`

8. **`frontend/lib/api.ts`**
   - Agregado `funnel_status` a `getOpsDriverMatrix`

9. **`frontend/app/pagos/driver-matrix/page.tsx`**
   - Agregada columna "Estado" con badge
   - Agregado filtro "Estado" en dropdown
   - Agregados tabs "Tabla" y "KPIs"
   - Tab KPIs muestra: Funnel (C1), Claims (C3/C4), Achieved sin Claim

### Scripts de Verificación

10. **`backend/scripts/sql/verify_funnel_and_claims_fix.sql`** (NUEVO)
    - 8 verificaciones: duplicados, claims inválidos, consistencia, origin_tag null, payment sin achieved, distribución funnel_status, etc.

## Comandos para Aplicar

### 1. Aplicar Vistas SQL

```bash
# 1. Crear vista funnel status
psql $DATABASE_URL -f backend/sql/ops/v_cabinet_funnel_status.sql

# 2. Aplicar fix en claims (ya aplicado anteriormente)
psql $DATABASE_URL -f backend/sql/ops/v_claims_payment_status_cabinet.sql

# 3. Aplicar fix en driver matrix
psql $DATABASE_URL -f backend/sql/ops/v_payments_driver_matrix_cabinet.sql
```

### 2. Reiniciar Backend

```bash
cd backend
# Si usas uvicorn directamente:
uvicorn app.main:app --reload

# O si usas otro método de despliegue, reiniciar el servicio
```

### 3. Reiniciar Frontend

```bash
cd frontend
npm run dev
```

### 4. Verificar

```bash
# Ejecutar script de verificación
psql $DATABASE_URL -f backend/scripts/sql/verify_funnel_and_claims_fix.sql
```

**Resultado esperado:**
- Verificación 1: **0 filas** (no hay duplicados)
- Verificación 2: **0 filas** (no hay claims sin milestone achieved)
- Verificación 3: **0 filas** (no hay M5 sin M1)
- Verificación 4: **0 filas** (no hay origin_tag NULL)
- Verificación 5: **0 filas** (no hay payment_status sin achieved_flag)
- Verificación 6: Distribución de funnel_status (conteos por estado)
- Verificación 7: **0 filas** (no hay funnel_status NULL)
- Verificación 8: Puede haber highest_milestone NULL (válido si no hay milestones)

## Checklist de Verificación (UI)

### Filtros
- [ ] Filtro "Origin Tag" funciona (cabinet, fleet_migration, unknown, All)
- [ ] Filtro "Estado" funciona (registered_incomplete, registered_complete, connected_no_trips, reached_m1, reached_m5, reached_m25, All)
- [ ] Ambos filtros se combinan correctamente

### Columna "Estado"
- [ ] Aparece como badge al lado de "Origin"
- [ ] Muestra estados correctos con colores:
  - Reg. Incompleto (warning)
  - Reg. Completo (info)
  - Conectado (default)
  - M1/M5/M25 (success)

### Tabs
- [ ] Tab "Tabla" muestra la tabla actual
- [ ] Tab "KPIs" muestra:
  - Funnel (C1): conteos por estado
  - Claims (C3/C4): Expected, Paid, Receivable
  - Achieved sin Claim: M1/M5/M25 sin claim

### Validaciones
- [ ] No existe "UNPAID" sin achieved_flag
- [ ] 1 fila por driver garantizada (no hay duplicados)
- [ ] Origin tag nunca muestra "—" (siempre unknown mínimo)

## Notas Importantes

1. **Grano 1 fila por driver**: `v_payments_driver_matrix_cabinet` mantiene EXACTAMENTE 1 fila por driver_id.

2. **Separación de capas canónica**:
   - **C1 Funnel**: actividad/estado operativo (funnel_status, highest_milestone)
   - **C3 Claims**: obligación de pago (expected_amount_yango, payment_status)
   - **C4 Pagos**: conciliación/pagos reales (yango_payment_status)

3. **Regla canónica restaurada**: `claim(milestone=N) ⇒ achieved(milestone=N)` se cumple estrictamente.

4. **Doble protección**:
   - Nivel 1: `v_claims_payment_status_cabinet` no genera claims sin milestone determinístico
   - Nivel 2: `v_payments_driver_matrix_cabinet` no muestra payment info si `achieved_flag = false`

5. **No se rompe historia**: Solo se eliminan claims "fantasma" sin milestone real.

## Explicación de la Causa Raíz

El problema de claims sin milestone achieved ocurría porque:
- `v_payment_calculation` calcula `milestone_achieved` basándose en ventanas de tiempo
- `v_claims_payment_status_cabinet` solo verificaba `milestone_achieved = true` pero no milestone determinístico
- Resultado: claims generados por ventanas sin milestone determinístico real

**Solución**: Agregar `INNER JOIN` con `v_cabinet_milestones_achieved_from_trips` para exigir milestone determinístico antes de generar claim.


