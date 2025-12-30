# Resumen: Integración Cobro Yango en Claims Cabinet

## ✅ Completado

### Backend
1. ✅ **Vista Claim-Level (Fuente Única)**: `ops.v_yango_cabinet_claims_for_collection`
   - Archivo: `backend/sql/ops/v_yango_cabinet_claims_for_collection.sql`
   - **ACCION REQUERIDA**: Ejecutar en la base de datos

2. ✅ **Vista Rollup (Driver-Level)**: `ops.v_claims_cabinet_driver_rollup`
   - Archivo: `backend/sql/ops/v_claims_cabinet_driver_rollup.sql`
   - **ACCION REQUERIDA**: Ejecutar en la base de datos
   - Derivada de la fuente única, garantiza reconciliación

3. ✅ **Endpoint `/payments/cabinet/drivers` actualizado**
   - Usa `ops.v_claims_cabinet_driver_rollup` cuando no hay filtros a nivel claim
   - Filtra primero en `ops.v_yango_cabinet_claims_for_collection` cuando hay filtros
   - Mantiene compatibilidad con schema existente

4. ✅ **Endpoint `/payments/cabinet/driver/{driver_id}/timeline` actualizado**
   - Usa `ops.v_yango_cabinet_claims_for_collection`
   - Mapea `yango_payment_status` a `paid_flag` para compatibilidad

5. ✅ **Endpoints claim-level existentes** (ya estaban creados):
   - `GET /api/v1/yango/payments/yango/cabinet/claims`
   - `GET /api/v1/yango/payments/yango/cabinet/claims.csv`

6. ✅ **Script de Reconciliación**: `backend/sql/ops/validation_rollup_reconciliation.sql`
   - Valida que SUM(rollup) == SUM(claim-level)

### Frontend
1. ✅ **Toggle Modo Driver / Cobranza Yango**
   - Agregado en `/pagos/claims/page.tsx`
   - Permite cambiar entre vistas

2. ✅ **Modo Driver (vista actual mejorada)**
   - Tabla driver-level con rollup
   - KPIs calculados desde drivers
   - Filtros: week, milestone, payment_status, action_priority
   - Botón "Ver Timeline" para drilldown

3. ✅ **Modo Cobranza (nueva funcionalidad)**
   - Tabla claim-level con todos los claims
   - KPIs calculados desde aggregates de claim-level
   - Filtros: payment_status, overdue_bucket, milestone, date_from, date_to, search
   - Botón "Export CSV" que descarga el archivo con filtros actuales
   - Default muestra UNPAID + PAID_MISAPPLIED

4. ✅ **KPIs consistentes**
   - Modo Driver: desde rollup (driver-level)
   - Modo Cobranza: desde claim-level aggregates
   - Ambas fuentes derivan de la misma vista base

## ⚠️ ACCIONES REQUERIDAS ANTES DE PROBAR

### 1. Ejecutar Vistas SQL en Base de Datos

**Conexión**:
```bash
psql -h 168.119.226.236 -U yego_user -d yego_integral
# Password: 37>MNA&-35+
```

**Archivos a ejecutar** (en orden):
1. `backend/sql/ops/v_yango_cabinet_claims_for_collection.sql`
2. `backend/sql/ops/v_claims_cabinet_driver_rollup.sql`

**Validación opcional**:
3. `backend/sql/ops/validation_rollup_reconciliation.sql` (para verificar reconciliación)

### 2. Reiniciar Backend

Después de ejecutar las vistas, reiniciar el servidor backend para que los cambios surtan efecto.

### 3. Probar la Integración

1. **Modo Driver**:
   - Ir a `/pagos/claims`
   - Verificar que la tabla de drivers se carga correctamente
   - Verificar KPIs (Expected, Paid, Not Paid, P0, P1)
   - Probar filtros
   - Probar "Ver Timeline" en un driver

2. **Modo Cobranza**:
   - Cambiar a modo "Cobranza Yango"
   - Verificar que la tabla de claims se carga (default: UNPAID + PAID_MISAPPLIED)
   - Verificar KPIs (Total, Unpaid, Misapplied, Paid)
   - Probar filtros
   - Probar "Export CSV" y verificar que descarga el archivo con los filtros aplicados

3. **Reconciliación**:
   - Ejecutar script de validación
   - Verificar que SUM(rollup) == SUM(claim-level)

## 📋 Pendiente (Opcional)

- Mejorar drilldown timeline para mostrar payment_key, paid_date, reason_code más prominentemente
  - El timeline ya muestra estos campos, pero podría mejorarse la UI

## 🎯 Resultado Esperado

- Una sola experiencia unificada en `/pagos/claims`
- Toggle entre vista Driver (operativa) y vista Cobranza (claim-level)
- KPIs consistentes desde la misma fuente
- Export CSV funcional desde modo cobranza
- Reconciliación garantizada: SUM(rollup) == SUM(claim-level)

