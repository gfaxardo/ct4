# FASE 2 - Auditoría UI: Reconciliación de Milestones

**Proyecto:** CT4 - Sistema Canónico de Identidad, Milestones y Pagos (Yango Cabinet)  
**Fase:** FASE 2 - Auditoría de UI/Endpoints  
**Fecha:** 2025-01-XX  
**Objetivo:** Evitar redundancia. Auditar si ya existe UI/endpoint que muestre reconciliación (`ops.v_cabinet_milestones_reconciled`)

---

## 1. Hallazgos: Páginas Frontend para Pagos Cabinet

### Páginas encontradas:

1. **`/pagos/yango-cabinet-claims`** (`frontend/app/pagos/yango-cabinet-claims/page.tsx`)
   - **Objetivo:** "¿Qué claims exigibles tenemos para cobrar a Yango?"
   - **Endpoint:** `GET /api/v1/yango/payments/cabinet/claims/to-collect`
   - **Vista SQL:** `ops.v_yango_cabinet_claims_for_collection`
   - **Campos mostrados:** `driver_id`, `milestone_value`, `yango_payment_status` (PAID, PAID_MISAPPLIED, UNPAID), `expected_amount`, `due_date`
   - **Reconciliación:** Muestra campo `reconciliation` en drilldown, pero viene de vista diferente (`ops.v_claims_payment_status_cabinet`), NO de `ops.v_cabinet_milestones_reconciled`

2. **`/pagos/yango-cabinet`** (`frontend/app/pagos/yango-cabinet/page.tsx`)
   - **Objetivo:** "¿Cuál es el estado de reconciliación de pagos Yango?"
   - **Endpoints:**
     - `GET /api/v1/yango/payments/reconciliation/summary`
     - `GET /api/v1/yango/payments/reconciliation/items`
   - **Vista SQL:** `ops.v_yango_payments_claims_cabinet_14d`
   - **Campos mostrados:** `paid_status` (paid_confirmed, paid_enriched, pending_active, pending_expired), `expected_amount`, `milestone_value`, `pay_week_start_monday`
   - **Reconciliación:** Usa vista de reconciliación antigua (por semanas y `paid_status`), NO usa `ops.v_cabinet_milestones_reconciled`

3. **`/pagos/driver-matrix`** (`frontend/app/pagos/driver-matrix/page.tsx`)
   - **Objetivo:** Vista de presentación de milestones por driver (M1/M5/M25)
   - **Endpoint:** `GET /api/v1/payments/driver-matrix/cabinet`
   - **Vista SQL:** `ops.v_payments_driver_matrix_cabinet`
   - **Campos mostrados:** `m1_achieved_flag`, `m5_achieved_flag`, `m25_achieved_flag`, `m1_yango_payment_status`, `m5_yango_payment_status`, `m25_yango_payment_status`
   - **Reconciliación:** NO muestra `reconciliation_status` de `ops.v_cabinet_milestones_reconciled`

---

## 2. Endpoints Backend Relevantes

### Endpoints actuales:

1. **`GET /api/v1/yango/payments/cabinet/claims/to-collect`**
   - **Archivo:** `backend/app/api/v1/yango_payments.py`
   - **Vista SQL:** `ops.v_yango_cabinet_claims_for_collection`
   - **Propósito:** Claims exigibles para cobrar a Yango
   - **No usa:** `ops.v_cabinet_milestones_reconciled`

2. **`GET /api/v1/yango/payments/reconciliation/summary`**
   - **Archivo:** `backend/app/api/v1/yango_payments.py`
   - **Vista SQL:** `ops.v_yango_payments_claims_cabinet_14d`
   - **Propósito:** Resumen agregado por semana y milestone
   - **No usa:** `ops.v_cabinet_milestones_reconciled`

3. **`GET /api/v1/yango/payments/reconciliation/items`**
   - **Archivo:** `backend/app/api/v1/yango_payments.py`
   - **Vista SQL:** `ops.v_yango_payments_claims_cabinet_14d`
   - **Propósito:** Items detallados de claims
   - **No usa:** `ops.v_cabinet_milestones_reconciled`

4. **`GET /api/v1/payments/driver-matrix/cabinet`**
   - **Archivo:** `backend/app/api/v1/payments.py`
   - **Vista SQL:** `ops.v_payments_driver_matrix_cabinet`
   - **Propósito:** Vista de presentación de milestones por driver
   - **No usa:** `ops.v_cabinet_milestones_reconciled`

---

## 3. Vista SQL Canónica: `ops.v_cabinet_milestones_reconciled`

### Estado actual:

- ✅ **Vista creada:** FASE 1
- ✅ **Comentarios SQL aplicados:** FASE 2
- ✅ **Documentación:** Política y runbook disponibles
- ❌ **UI/Endpoint:** NO existe endpoint ni UI que consuma esta vista

### Campos clave de la vista:

- `driver_id`, `milestone_value`
- `reconciliation_status`: `OK`, `ACHIEVED_NOT_PAID`, `PAID_WITHOUT_ACHIEVEMENT`, `NOT_APPLICABLE`
- Campos de ACHIEVED: `achieved_flag`, `achieved_date`, `achieved_trips_in_window`, `expected_amount`, etc.
- Campos de PAID: `paid_flag`, `pay_date`, `payment_key`, `match_confidence`, etc.

---

## 4. Análisis de Reconciliación Existente

### Páginas que mencionan "reconciliation":

1. **`/pagos/yango-cabinet`** (`frontend/app/pagos/yango-cabinet/page.tsx`)
   - **Tipo:** Reconciliación por semanas (`pay_week_start_monday`)
   - **Vista:** `ops.v_yango_payments_claims_cabinet_14d`
   - **Estado:** `paid_status` (paid_confirmed, paid_enriched, pending_active, pending_expired)
   - **Diferencias con `ops.v_cabinet_milestones_reconciled`:**
     - Agrupa por semanas (no por driver individual)
     - Usa `paid_status` (no `reconciliation_status`)
     - No muestra separación explícita ACHIEVED vs PAID
     - No muestra `PAID_WITHOUT_ACHIEVEMENT` explícitamente

2. **`/pagos/yango-cabinet-claims`** (drilldown)
   - **Campo `reconciliation`:**
     - `reconciliation_status`: String (viene de `ops.v_claims_payment_status_cabinet`)
     - `match_method`: String
     - `expected_amount`: Number
     - `paid_payment_key`: String
   - **Diferencias:**
     - Campo `reconciliation` es limitado (solo en drilldown)
     - NO usa `ops.v_cabinet_milestones_reconciled`
     - NO muestra estados `OK`, `ACHIEVED_NOT_PAID`, `PAID_WITHOUT_ACHIEVEMENT` explícitamente

---

## 5. Conclusión

### Opción B: "No existe reconciliación" basada en `ops.v_cabinet_milestones_reconciled`

**Hallazgo:** Aunque existen páginas que mencionan "reconciliación", **ninguna UI ni endpoint consume la vista canónica `ops.v_cabinet_milestones_reconciled`** creada en FASE 1.

**Razones:**
1. Las vistas existentes (`ops.v_yango_payments_claims_cabinet_14d`, `ops.v_yango_cabinet_claims_for_collection`) son anteriores a FASE 1
2. La reconciliación existente agrupa por semanas y usa `paid_status`, no `reconciliation_status`
3. No hay separación explícita ACHIEVED vs PAID en la UI actual
4. No se muestra `PAID_WITHOUT_ACHIEVEMENT` como estado explícito

---

## 6. Recomendación: Cambio Mínimo

### Opción recomendada: Agregar pestaña dentro de UI existente

**Página target:** `/pagos/yango-cabinet` (`frontend/app/pagos/yango-cabinet/page.tsx`)

**Razón:**
- Ya existe página de "reconciliación" de Yango Cabinet
- Usuarios ya conocen esta ruta
- No requiere nueva página
- Cambio mínimo: agregar pestaña/sección adicional

### Propuesta técnica:

1. **Backend:** Crear endpoint read-only
   - **Ruta:** `GET /api/v1/yango/payments/cabinet/reconciliation`
   - **Vista SQL:** `ops.v_cabinet_milestones_reconciled`
   - **Query:** SELECT con filtros (driver_id, milestone_value, reconciliation_status)
   - **Schema:** Nuevo schema Pydantic (`CabinetMilestonesReconciledRow`, `CabinetMilestonesReconciledResponse`)

2. **Frontend:** Agregar pestaña/sección en página existente
   - **Archivo:** `frontend/app/pagos/yango-cabinet/page.tsx`
   - **Cambio:** Agregar pestaña "Reconciliación de Milestones" (junto a pestañas existentes)
   - **Componente:** Nueva sección que muestra tabla con:
     - `driver_id`, `milestone_value`
     - `reconciliation_status` (con badges: OK, ACHIEVED_NOT_PAID, PAID_WITHOUT_ACHIEVEMENT)
     - `achieved_date`, `pay_date`
     - `expected_amount`, `payment_key`
   - **Filtros:** Por `reconciliation_status`, `milestone_value`

### Archivos a modificar:

**Backend:**
- `backend/app/api/v1/yango_payments.py` (nuevo endpoint)
- `backend/app/schemas/payments.py` (nuevos schemas)

**Frontend:**
- `frontend/app/pagos/yango-cabinet/page.tsx` (agregar pestaña/sección)
- `frontend/lib/api.ts` (nueva función API)
- `frontend/lib/types.ts` (nuevos tipos TypeScript)

### No se requiere:
- Nueva página
- Nueva ruta
- Cambios en vistas SQL existentes
- Cambios en endpoints existentes

---

## 7. Archivos Relevantes

### Frontend:
- `frontend/app/pagos/yango-cabinet/page.tsx` (página target)
- `frontend/app/pagos/yango-cabinet-claims/page.tsx` (referencia)
- `frontend/app/pagos/driver-matrix/page.tsx` (referencia)
- `frontend/lib/api.ts` (función API a agregar)
- `frontend/lib/types.ts` (tipos a agregar)

### Backend:
- `backend/app/api/v1/yango_payments.py` (endpoint a agregar)
- `backend/app/schemas/payments.py` (schemas a agregar)

### SQL:
- `backend/sql/ops/v_cabinet_milestones_reconciled.sql` (vista canónica - ya existe, solo lectura)

---

## 8. Resumen Ejecutivo

**Conclusión:** No existe UI/endpoint que muestre reconciliación basada en `ops.v_cabinet_milestones_reconciled`.

**Recomendación:** Agregar pestaña/sección en página existente `/pagos/yango-cabinet` con endpoint read-only que consume `ops.v_cabinet_milestones_reconciled`.

**Impacto:** Mínimo (no nueva página, no cambios en lógica SQL, solo endpoint + UI incremental).

---

**Fin del informe**






