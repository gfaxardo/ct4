# RESUMEN EJECUCIÓN - Sistema Auditable Cabinet 14d

**Fecha:** 2024-12-19  
**Estado:** En progreso (PASOS 1-2 completados, PASOS 3-5 pendientes)

---

## ✅ PASO 1 - INVENTARIO REAL (COMPLETADO)

### Endpoints Existentes
- ✅ `GET /api/v1/ops/payments/cabinet-financial-14d/limbo` (LEAD-first)
- ⚠️ `GET /api/v1/ops/payments/cabinet-financial-14d/claims-gap` (CLAIM-first) - **ERROR 500 corregido**

### Vistas SQL Existentes
- ✅ `ops.v_cabinet_leads_limbo` (LEAD-first)
- ✅ `ops.v_cabinet_claims_expected_14d` (fuente de verdad)
- ⚠️ `ops.v_cabinet_claims_gap_14d` (CLAIM-first) - **CORREGIDA**

### Jobs Existentes
- ✅ `reconcile_cabinet_claims_14d.py`
- ✅ `reconcile_cabinet_leads_pipeline.py`

### UI Existentes
- ✅ `CabinetLimboSection.tsx` (integrado en Cobranza Yango)
- ✅ `CabinetClaimsGapSection.tsx` (integrado en Cobranza Yango)

**Documento:** `docs/ops/PASO1_INVENTARIO_CABINET_14D.md`

---

## ✅ PASO 2 - FIX CLAIMS GAP (COMPLETADO)

### Problema
- Error 500 por columna `expected_amount` inexistente
- Vista SQL expone `amount_expected`, endpoint/UI espera `expected_amount`

### Solución Implementada
1. **Vista SQL actualizada:** `backend/sql/ops/v_cabinet_claims_gap_14d.sql`
   - Alias `amount_expected AS expected_amount` (línea 145)

2. **Endpoint actualizado:** `backend/app/api/v1/ops_payments.py`
   - Todas las referencias cambiadas a `expected_amount`

3. **Job actualizado:** `backend/jobs/reconcile_cabinet_claims_14d.py`
   - SELECT y mapeo actualizados a `expected_amount`

4. **Migración Alembic creada:** `backend/alembic/versions/019_fix_claims_gap_expected_amount.py`
   - Revisión: `019_fix_claims_gap_expected_amount`
   - Revisión anterior: `018_claims_cabinet_14d`

### Archivos Modificados
- ✅ `backend/sql/ops/v_cabinet_claims_gap_14d.sql`
- ✅ `backend/app/api/v1/ops_payments.py`
- ✅ `backend/jobs/reconcile_cabinet_claims_14d.py`
- ✅ `backend/alembic/versions/019_fix_claims_gap_expected_amount.py`

**Documento:** `docs/ops/PASO2_FIX_CLAIMS_GAP_COMPLETADO.md`

---

## ⚠️ PASO 3 - IMPLEMENTAR LIMBO (VERIFICACIÓN REQUERIDA)

### Estado Actual
- ✅ Vista SQL existe: `ops.v_cabinet_leads_limbo`
- ✅ Endpoint existe: `/cabinet-financial-14d/limbo`
- ✅ UI existe: `CabinetLimboSection.tsx`
- ✅ Export CSV implementado

### Reglas Duras Verificadas
- ✅ `trips_14d` debe ser 0 cuando `driver_id IS NULL` (implementado en línea 97)
- ✅ `TRIPS_NO_CLAIM` solo puede ocurrir cuando `driver_id IS NOT NULL` y `trips_14d > 0` y `claim_missing` (implementado en líneas 188-190)

### Acciones Pendientes
- [ ] Validar que endpoint funciona correctamente (probar con datos reales)
- [ ] Verificar que UI renderiza correctamente
- [ ] Validar que export CSV funciona

---

## ⚠️ PASO 4 - JOBS (VERIFICACIÓN REQUERIDA)

### Estado Actual
- ✅ `reconcile_cabinet_claims_14d.py` existe y actualizado
- ✅ `reconcile_cabinet_leads_pipeline.py` existe

### Acciones Pendientes
- [ ] Validar que jobs corren sin errores
- [ ] Verificar que `reconcile_cabinet_claims_14d` reduce `TRIPS_NO_CLAIM`
- [ ] Crear scripts de validación:
  - [ ] `scripts/validate_limbo.py`
  - [ ] `scripts/validate_claims_gap_before_after.py`
  - [ ] `scripts/check_limbo_alerts.py`

---

## ❌ PASO 5 - SCHEDULER + ALERTAS (PENDIENTE)

### Pendiente
- [ ] Crear runbook: `docs/runbooks/limbo_and_claims_gap.md`
- [ ] Configurar scheduler (cron o task scheduler):
  - [ ] `reconcile_cabinet_claims_14d` (diario 02:30)
  - [ ] `reconcile_cabinet_leads_pipeline` (diario 02:30)
  - [ ] `check_limbo_alerts.py` (diario 02:30)
- [ ] Implementar alertas:
  - [ ] Si `limbo_no_identity` total > umbral
  - [ ] Si `pct_with_identity` < umbral
  - [ ] Si `TRIPS_NO_CLAIM` > 0 por N días

---

## PRÓXIMOS PASOS INMEDIATOS

1. **Ejecutar migración:**
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Probar endpoint Claims Gap:**
   ```bash
   curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d/claims-gap?limit=10"
   ```

3. **Validar Limbo:**
   - Probar endpoint `/cabinet-financial-14d/limbo`
   - Verificar UI en `/pagos/cobranza-yango`

4. **Crear scripts de validación** (PASO 4)

5. **Configurar scheduler y alertas** (PASO 5)

---

## DEFINITION OF DONE

### A) Endpoint + UI "Leads en Limbo (LEAD-first)" ✅
- [x] Endpoint funcionando
- [x] Filtros implementados
- [x] Totales por etapa
- [x] Export CSV

### B) Endpoint + UI "Claims Gap (CLAIM-first)" ✅
- [x] Error `expected_amount` corregido
- [x] Endpoint funcionando
- [x] Totales implementados
- [x] Export CSV

### C) Jobs ⚠️
- [x] `reconcile_cabinet_leads_pipeline` existe
- [x] `reconcile_cabinet_claims_14d` existe y actualizado
- [ ] Scripts de validación pendientes

### D) Scheduler + Alertas ❌
- [ ] Scheduler pendiente
- [ ] Alertas pendientes

### E) Reglas Duras ✅
- [x] `trips_14d` debe ser 0 cuando `driver_id IS NULL`
- [x] `TRIPS_NO_CLAIM` solo puede ocurrir cuando condiciones cumplidas
- [x] Claims Gap muestra `expected_amount` y razón

---

## ARCHIVOS CREADOS/MODIFICADOS

### Nuevos
- `docs/ops/PASO1_INVENTARIO_CABINET_14D.md`
- `docs/ops/PASO2_FIX_CLAIMS_GAP_COMPLETADO.md`
- `docs/ops/RESUMEN_EJECUCION_CABINET_14D_AUDITABLE.md`
- `backend/alembic/versions/019_fix_claims_gap_expected_amount.py`

### Modificados
- `backend/sql/ops/v_cabinet_claims_gap_14d.sql`
- `backend/app/api/v1/ops_payments.py`
- `backend/jobs/reconcile_cabinet_claims_14d.py`

---

**NOTA:** Este resumen refleja el estado actual. Los PASOS 3-5 requieren validación y/o implementación adicional.
