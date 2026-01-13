# PASO 2 - FIX CLAIMS GAP (expected_amount) - COMPLETADO

**Fecha:** 2024-12-19  
**Estado:** ✅ COMPLETADO

---

## PROBLEMA IDENTIFICADO

- **Error:** 500 al acceder a `/api/v1/ops/payments/cabinet-financial-14d/claims-gap`
- **Causa:** Inconsistencia de nombres de columna
  - Vista SQL expone: `amount_expected`
  - Endpoint/UI espera: `expected_amount`

---

## SOLUCIÓN IMPLEMENTADA

### 1. Vista SQL actualizada
- **Archivo:** `backend/sql/ops/v_cabinet_claims_gap_14d.sql`
- **Cambio:** Alias `amount_expected AS expected_amount` en línea 145
- **Resultado:** Vista ahora expone `expected_amount` para mantener contrato claro

### 2. Endpoint actualizado
- **Archivo:** `backend/app/api/v1/ops_payments.py`
- **Cambios:**
  - Línea 2451: `amount_expected` → `expected_amount` en SELECT
  - Línea 2480: `row.amount_expected` → `row.expected_amount` en mapeo
  - Línea 2497: `SUM(amount_expected)` → `SUM(expected_amount)` en summary
  - Línea 2576-2577: `SUM(amount_expected)` → `SUM(expected_amount)` en export
  - Línea 2669: `amount_expected` → `expected_amount` en export CSV
  - Línea 2706: `row.amount_expected` → `row.expected_amount` en export CSV

### 3. Job de reconciliación actualizado
- **Archivo:** `backend/jobs/reconcile_cabinet_claims_14d.py`
- **Cambios:**
  - Línea 88: `amount_expected` → `expected_amount` en SELECT
  - Línea 113: Simplificado fallback (ya no necesita verificar ambos nombres)

### 4. Migración Alembic creada
- **Archivo:** `backend/alembic/versions/019_fix_claims_gap_expected_amount.py`
- **Propósito:** Desplegar cambio de vista en base de datos
- **Revisión:** `019_fix_claims_gap_expected_amount`
- **Revisión anterior:** `018_claims_cabinet_14d`

---

## VALIDACIÓN REQUERIDA

### Script de validación
Crear `backend/scripts/validate_claims_gap_before_after.py` que:
1. Consulta conteos por `gap_reason`
2. Valida que no haya error 500
3. Valida que `expected_amount` siempre tenga valor cuando `claim_expected=true`

### Ejecutar migración
```bash
cd backend
alembic upgrade head
```

### Probar endpoint
```bash
curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d/claims-gap?limit=10"
```

---

## ARCHIVOS MODIFICADOS

1. ✅ `backend/sql/ops/v_cabinet_claims_gap_14d.sql` (alias expected_amount)
2. ✅ `backend/app/api/v1/ops_payments.py` (actualizado a expected_amount)
3. ✅ `backend/jobs/reconcile_cabinet_claims_14d.py` (actualizado a expected_amount)
4. ✅ `backend/alembic/versions/019_fix_claims_gap_expected_amount.py` (nueva migración)

---

## PRÓXIMOS PASOS

- PASO 3: Verificar que Limbo funciona correctamente (ya existe, solo validar)
- PASO 4: Ajustar jobs si es necesario
- PASO 5: Crear scheduler y alertas
