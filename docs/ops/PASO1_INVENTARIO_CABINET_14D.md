# PASO 1 - INVENTARIO REAL (Cabinet 14d)

**Fecha:** 2024-12-19  
**Objetivo:** Inventariar endpoints, vistas SQL y columnas reales en DB para sistema auditable Cabinet 14d.

---

## 1. ENDPOINTS EXISTENTES

### 1.1 Endpoint Limbo (LEAD-first)
- **Ruta:** `GET /api/v1/ops/payments/cabinet-financial-14d/limbo`
- **Archivo:** `backend/app/api/v1/ops_payments.py` (línea 2041)
- **Estado:** ✅ EXISTE
- **Funcionalidad:**
  - Filtros: `limbo_stage`, `week_start`, `lead_date_from`, `lead_date_to`
  - Paginación: `limit`, `offset`
  - Export CSV: `/cabinet-financial-14d/limbo/export`
- **Vista SQL:** `ops.v_cabinet_leads_limbo`

### 1.2 Endpoint Claims Gap (CLAIM-first)
- **Ruta:** `GET /api/v1/ops/payments/cabinet-financial-14d/claims-gap`
- **Archivo:** `backend/app/api/v1/ops_payments.py` (línea 2361)
- **Estado:** ⚠️ EXISTE PERO CON ERROR
- **Problema:** Error 500 por columna `expected_amount` inexistente
- **Funcionalidad:**
  - Filtros: `gap_reason`, `week_start`, `lead_date_from`, `lead_date_to`, `milestone_value`
  - Paginación: `limit`, `offset`
  - Export CSV: `/cabinet-financial-14d/claims-gap/export`
- **Vista SQL:** `ops.v_cabinet_claims_gap_14d`

---

## 2. VISTAS SQL EXISTENTES

### 2.1 `ops.v_cabinet_leads_limbo`
- **Archivo:** `backend/sql/ops/v_cabinet_leads_limbo.sql`
- **Estado:** ✅ EXISTE
- **Propósito:** Vista LEAD-FIRST que muestra TODOS los leads de cabinet con su etapa exacta en el embudo
- **Grano:** 1 fila por lead (source_pk canónico)
- **Columnas principales:**
  - `lead_id`, `lead_source_pk`, `lead_date`, `week_start`
  - `person_key`, `driver_id`
  - `trips_14d`, `window_end_14d`
  - `reached_m1_14d`, `reached_m5_14d`, `reached_m25_14d`
  - `expected_amount_14d` (acumulativo)
  - `has_claim_m1`, `has_claim_m5`, `has_claim_m25`
  - `limbo_stage` (NO_IDENTITY, NO_DRIVER, NO_TRIPS_14D, TRIPS_NO_CLAIM, OK)
  - `limbo_reason_detail`

### 2.2 `ops.v_cabinet_claims_expected_14d`
- **Archivo:** `backend/sql/ops/v_cabinet_claims_expected_14d.sql`
- **Estado:** ✅ EXISTE
- **Propósito:** Vista FUENTE DE VERDAD que calcula qué claims DEBEN existir
- **Grano:** 1 fila por (lead_source_pk, milestone)
- **Columnas principales:**
  - `lead_id`, `lead_source_pk`, `lead_date_canonico`, `week_start`
  - `person_key`, `driver_id`
  - `milestone` (1, 5, 25)
  - `trips_in_window`, `milestone_reached`
  - `claim_expected` (boolean)
  - `amount_expected` (M1=25, M5=35, M25=100)
  - `expected_reason_detail`

### 2.3 `ops.v_cabinet_claims_gap_14d`
- **Archivo:** `backend/sql/ops/v_cabinet_claims_gap_14d.sql`
- **Estado:** ⚠️ EXISTE PERO CON PROBLEMA
- **Propósito:** Vista CLAIM-FIRST que identifica gaps: "debería existir claim y no existe"
- **Grano:** 1 fila por (lead_source_pk, milestone) donde hay gap
- **Columnas principales:**
  - `lead_id`, `lead_source_pk`, `lead_date`, `week_start`
  - `person_key`, `driver_id`
  - `milestone_value`, `trips_14d`, `milestone_achieved`
  - `claim_expected`, `claim_exists`, `claim_status`
  - `gap_reason`, `gap_detail`
  - **`amount_expected`** ← PROBLEMA: endpoint espera `expected_amount`

---

## 3. PROBLEMA IDENTIFICADO

### 3.1 Error en Claims Gap
- **Síntoma:** Error 500 al acceder a `/cabinet-financial-14d/claims-gap`
- **Causa:** Inconsistencia de nombres de columna
  - Vista SQL expone: `amount_expected` (línea 145 de `v_cabinet_claims_gap_14d.sql`)
  - Endpoint accede a: `row.amount_expected` (línea 2451, 2480 de `ops_payments.py`)
  - Schema/UI probablemente espera: `expected_amount`
- **Ubicación del problema:**
  - Vista: `backend/sql/ops/v_cabinet_claims_gap_14d.sql` (línea 145)
  - Endpoint: `backend/app/api/v1/ops_payments.py` (líneas 2451, 2480, 2497)

### 3.2 Solución requerida
- **Opción A (Recomendada):** Aliasar `amount_expected` como `expected_amount` en la vista SQL
- **Opción B:** Cambiar endpoint para usar `amount_expected` consistentemente
- **Decisión:** Usar Opción A para mantener contrato claro (`expected_amount` es más descriptivo)

---

## 4. JOBS EXISTENTES

### 4.1 `reconcile_cabinet_claims_14d`
- **Archivo:** `backend/jobs/reconcile_cabinet_claims_14d.py`
- **Estado:** ✅ EXISTE
- **Funcionalidad:**
  - Obtiene gaps desde `v_cabinet_claims_gap_14d`
  - Inserta/actualiza claims en `canon.claims_yango_cabinet_14d`
  - Refresca vistas materializadas
- **Uso:** `python -m jobs.reconcile_cabinet_claims_14d --days-back 21 --limit 1000`

### 4.2 `reconcile_cabinet_leads_pipeline`
- **Archivo:** `backend/jobs/reconcile_cabinet_leads_pipeline.py`
- **Estado:** ✅ EXISTE
- **Funcionalidad:**
  - Procesa leads recientes y en limbo
  - Ejecuta ingestion/matching para crear `identity_links`
  - Verifica resultados
- **Uso:** `python -m jobs.reconcile_cabinet_leads_pipeline --days-back 30 --limit 2000`

---

## 5. TABLAS FÍSICAS

### 5.1 `public.module_ct_cabinet_leads`
- **Estado:** ✅ EXISTE (fuente RAW)
- **Columnas clave:** `id`, `external_id`, `lead_created_at`, `park_phone`, `asset_plate_number`, `first_name`, `middle_name`, `last_name`

### 5.2 `canon.claims_yango_cabinet_14d`
- **Estado:** ✅ EXISTE (tabla física de claims)
- **Columnas clave:** `claim_id`, `person_key`, `driver_id`, `lead_date`, `milestone`, `amount_expected`, `status`, `generated_at`, `paid_at`

### 5.3 `canon.identity_links`
- **Estado:** ✅ EXISTE (tabla de vínculos identity)
- **Columnas clave:** `person_key`, `source_table`, `source_pk`, `match_rule`, `confidence_level`

### 5.4 `public.summary_daily`
- **Estado:** ✅ EXISTE (fuente RAW de viajes)
- **Columnas clave:** `driver_id`, `date_file`, `count_orders_completed`

---

## 6. REGLAS DURAS IDENTIFICADAS

### 6.1 Regla: `trips_14d` debe ser 0 cuando `driver_id IS NULL`
- **Ubicación:** `v_cabinet_leads_limbo.sql` (línea 97)
- **Estado:** ✅ IMPLEMENTADA (usa `COALESCE(SUM(...), 0)` y solo suma si `driver_id` existe)

### 6.2 Regla: `TRIPS_NO_CLAIM` solo puede ocurrir cuando `driver_id IS NOT NULL` y `trips_14d > 0` y `claim_missing`
- **Ubicación:** `v_cabinet_leads_limbo.sql` (líneas 188-190)
- **Estado:** ✅ IMPLEMENTADA (lógica en `limbo_stage`)

### 6.3 Regla: Claims Gap debe mostrar `expected_amount` y razón, no depender de "paid"
- **Ubicación:** `v_cabinet_claims_gap_14d.sql`
- **Estado:** ⚠️ PARCIALMENTE IMPLEMENTADA (falta alias `expected_amount`)

---

## 7. ARCHIVOS TOCADOS (RESUMEN)

### Backend
- `backend/app/api/v1/ops_payments.py` (endpoints limbo y claims-gap)
- `backend/sql/ops/v_cabinet_leads_limbo.sql` (vista limbo)
- `backend/sql/ops/v_cabinet_claims_gap_14d.sql` (vista claims gap - **NECESITA FIX**)
- `backend/sql/ops/v_cabinet_claims_expected_14d.sql` (vista fuente de verdad)
- `backend/jobs/reconcile_cabinet_claims_14d.py` (job reconciliación claims)
- `backend/jobs/reconcile_cabinet_leads_pipeline.py` (job reconciliación leads)

### Frontend
- (Por verificar si existe UI para limbo y claims-gap)

---

## 8. PRÓXIMOS PASOS

1. **PASO 2:** Arreglar `v_cabinet_claims_gap_14d` para exponer `expected_amount` (alias de `amount_expected`)
2. **PASO 3:** Verificar que Limbo funciona correctamente (ya existe, solo validar)
3. **PASO 4:** Ajustar jobs si es necesario
4. **PASO 5:** Crear scheduler y alertas

---

**NOTA:** Este inventario asume que las vistas SQL están desplegadas en la base de datos. Si hay errores al ejecutar, puede ser que las vistas no estén desplegadas o que haya inconsistencias en los nombres de columnas.
