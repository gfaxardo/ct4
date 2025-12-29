# Checklist de Validación - Hardening de Enriquecimiento de Identidad

## Pre-requisitos

1. Backend corriendo en `http://localhost:8000`
2. Frontend corriendo en `http://localhost:3000`
3. Ejecutar SQL en orden:
   ```sql
   -- 1. Vista enriquecida HARDENED
   backend/sql/ops/v_yango_payments_ledger_latest_enriched.sql
   
   -- 2. Vista de claims actualizada
   backend/sql/ops/v_yango_payments_claims_cabinet_14d.sql
   ```

## PASO 1: Validar SQL - Reglas SAFE

### 1.1 Vista Enriquecida Se Ejecuta Sin Errores
- [ ] Ejecutar: `SELECT COUNT(*) FROM ops.v_yango_payments_ledger_latest_enriched;`
- [ ] Debe retornar número igual o mayor al ledger original

### 1.2 Campos Expuestos Correctamente
- [ ] Ejecutar:
  ```sql
  SELECT 
    driver_id_original,
    driver_id_final,
    person_key_original,
    person_key_final,
    identity_source,
    identity_enriched,
    match_rule,
    match_confidence
  FROM ops.v_yango_payments_ledger_latest_enriched
  LIMIT 5;
  ```
- [ ] Todos los campos deben existir
- [ ] `identity_source` debe ser 'original', 'enriched_by_name', o 'none'
- [ ] `match_confidence` debe ser 'high', 'medium', o 'unknown'

### 1.3 Reglas SAFE Funcionan
- [ ] Ejecutar script: `backend/sql/ops/validation_ledger_identity.sql`
- [ ] Verificar query #4 (Resumen de Enriquecimiento):
  - `both_null_count` debe ser menor o igual al original (idealmente 0 si hay matches)
  - `identity_enriched_count` debe ser > 0 si hay nombres que pasan reglas SAFE
- [ ] Verificar query #9 (Distribución de Confidence):
  - Debe haber registros con `match_confidence = 'high'` si hay actividad en summary_daily
  - Debe haber registros con `match_confidence = 'medium'` si hay matches sin actividad

### 1.4 Nombres Placeholder Excluidos
- [ ] Ejecutar:
  ```sql
  SELECT driver_name_normalized, identity_source
  FROM ops.v_yango_payments_ledger_latest_enriched
  WHERE LOWER(driver_name_normalized) IN ('na', 'n/a', 'unknown', 'sin nombre', '-', '')
     OR driver_name_normalized IS NULL;
  ```
- [ ] Todos estos registros deben tener `identity_source = 'none'`

## PASO 2: Validar Claims View

### 2.1 Claims Usa Identidad Final
- [ ] Ejecutar:
  ```sql
  SELECT 
    COUNT(*) AS total_claims,
    COUNT(*) FILTER (WHERE paid_status = 'paid') AS count_paid,
    SUM(expected_amount) FILTER (WHERE paid_status = 'paid') AS amount_paid
  FROM ops.v_yango_payments_claims_cabinet_14d;
  ```
- [ ] Si hay matches con confidence high/medium, debe haber `count_paid > 0`

### 2.2 Solo Usa Confidence High/Medium
- [ ] Ejecutar script: `backend/sql/ops/validation_paid_reconciliation.sql`
- [ ] Verificar query #3 (Comparación Ledger vs Claims):
  - Claims con `paid_status='paid'` deben corresponder a ledger con `match_confidence IN ('high', 'medium')`
- [ ] Verificar query #10 (Resumen Final):
  - `claims_paid_count` debe ser > 0 si hay matches high/medium
  - `claims_paid_amount` debe ser > 0

## PASO 3: Validar Backend - Endpoints

### 3.1 Summary Endpoint - Métricas Extendidas
- [ ] GET `/api/v1/yango/payments/reconciliation/summary`
- [ ] Verificar `filters._validation` contiene:
  - `identity_original_rows`
  - `identity_enriched_rows`
  - `both_identity_null_rows`
  - `distribution_confidence` (objeto con high/medium/unknown)
  - `matched_paid_rows`
- [ ] Verificar que `both_identity_null_rows` <= `ledger_total_rows`

### 3.2 Ledger Unmatched Endpoint
- [ ] GET `/api/v1/yango/payments/reconciliation/ledger/unmatched`
- [ ] Verificar que cada row incluye:
  - `identity_source`
  - `identity_enriched`
  - `match_confidence`
  - `driver_id_final`
  - `person_key_final`

### 3.3 Ledger Matched Endpoint
- [ ] GET `/api/v1/yango/payments/reconciliation/ledger/matched`
- [ ] Verificar que solo incluye registros con `match_confidence IN ('high', 'medium')`
- [ ] Verificar campos: `identity_source`, `match_confidence`, `driver_id_final`, `person_key_final`

### 3.4 Driver Detail Endpoint
- [ ] GET `/api/v1/yango/payments/reconciliation/driver/{driver_id}`
- [ ] Verificar que muestra claims pagados y pendientes correctamente
- [ ] Verificar que usa identidad final del ledger

### 3.5 No 403 Errors
- [ ] Verificar Network tab en navegador
- [ ] Todos los endpoints deben retornar 200 OK (no 403, no 404)
- [ ] Si hay 403, revisar:
  - Headers de autenticación en `frontend/lib/api.ts`
  - Base URL configurado correctamente
  - Middleware de autenticación en backend

## PASO 4: Validar Frontend

### 4.1 Card "Identidad del Ledger"
- [ ] Card muestra breakdown:
  - Pagos pagados
  - Original (con identidad original)
  - Enriquecidos (con identidad enriquecida)
  - Sin identidad
  - Distribución de confianza (High/Med/Unknown)

### 4.2 Banner Warning Mejorado
- [ ] Si `Total Paid = 0` y `ledger_rows_is_paid_true > 0`:
  - Banner muestra todas las métricas de identidad
  - Incluye distribución de confianza
  - Links a modales funcionan

### 4.3 Modales con Nuevas Columnas
- [ ] Modal "Ledger sin match":
  - Columna "Identity Source" con chips de color
  - Columna "Confidence" con chips (high=verde, medium=amarillo, unknown=gris)
  - Columna "Enriquecido" muestra flag

- [ ] Modal "Ledger con match":
  - Mismas columnas que "sin match"
  - Solo muestra registros con confidence high/medium

### 4.4 Toggle Mode (Opcional - si se implementa)
- [ ] Toggle: Real | Real+Enriquecido | Estimado
- [ ] Real: Solo paid_status='paid' con confidence='high'
- [ ] Real+Enriquecido: paid_status='paid' con confidence IN ('high', 'medium')
- [ ] Estimado: pending_active (sin cambios)

## PASO 5: Validación End-to-End

### 5.1 Flujo Completo: Enriquecimiento → Reconciliación
- [ ] Ejecutar queries de validación SQL
- [ ] Verificar que `both_identity_null_rows` disminuyó (o es 0)
- [ ] Verificar que `claims_paid_count > 0` si hay matches high/medium
- [ ] Dashboard muestra `Total Paid > 0` si hay matches

### 5.2 Flujo Completo: Drilldown por Conductor
- [ ] Click en driver_id en tabla de items
- [ ] Modal muestra claims del conductor
- [ ] Claims pagados usan identidad final (puede ser enriquecida)
- [ ] Summary muestra totales correctos

### 5.3 Comparar Valores SQL vs UI
- [ ] Ejecutar:
  ```sql
  SELECT 
    COUNT(*) FILTER (WHERE paid_status = 'paid') AS claims_paid_count,
    SUM(expected_amount) FILTER (WHERE paid_status = 'paid') AS claims_paid_amount
  FROM ops.v_yango_payments_claims_cabinet_14d;
  ```
- [ ] Comparar con valores en dashboard (Total Paid)
- [ ] Deben coincidir (con pequeñas diferencias por redondeo)

## PASO 6: Criterios de Aceptación

### 6.1 SQL
- [ ] `both_identity_null_rows` debe bajar (ideal 0 si SAFE aplica)
- [ ] Aparece `paid_status='paid'` en claims cuando existe match high/medium
- [ ] Scripts de validación ejecutan sin errores

### 6.2 Backend
- [ ] Todos los endpoints retornan 200 OK (no 403)
- [ ] Métricas de validación incluyen distribución de confianza
- [ ] Endpoints exponen campos finales (driver_id_final, person_key_final, identity_source)

### 6.3 Frontend
- [ ] UI muestra breakdown completo de identidad
- [ ] Modales muestran identity_source y confidence
- [ ] Dashboard muestra Paid real > 0 si hay matches
- [ ] No hay errores en consola del navegador

### 6.4 End-to-End
- [ ] Sistema puede responder: qué pagó Yango, qué está pendiente, qué no tiene match
- [ ] Todo está disponible en frontend (no solo backend)
- [ ] Drilldown por conductor funciona correctamente

## Queries de Verificación Final

```sql
-- 1. Resumen de identidad
SELECT 
    identity_source,
    match_confidence,
    COUNT(*) AS count_rows,
    COUNT(*) FILTER (WHERE is_paid = true) AS count_paid
FROM ops.v_yango_payments_ledger_latest_enriched
GROUP BY identity_source, match_confidence
ORDER BY identity_source, match_confidence;

-- 2. Claims pagados
SELECT 
    COUNT(*) AS claims_paid_count,
    SUM(expected_amount) AS claims_paid_amount
FROM ops.v_yango_payments_claims_cabinet_14d
WHERE paid_status = 'paid';

-- 3. Comparación both_null
SELECT 
    (SELECT COUNT(*) FILTER (WHERE driver_id IS NULL AND person_key IS NULL) 
     FROM ops.v_yango_payments_ledger_latest) AS original_both_null,
    (SELECT COUNT(*) FILTER (WHERE driver_id_final IS NULL AND person_key_final IS NULL) 
     FROM ops.v_yango_payments_ledger_latest_enriched) AS enriched_both_null;
```

## Resultado Esperado

✅ `both_identity_null_rows` disminuyó (o es 0 si hay matches)  
✅ `claims_paid_count > 0` si hay matches high/medium  
✅ Dashboard muestra `Total Paid > 0`  
✅ Todos los endpoints funcionan sin 403  
✅ Frontend muestra breakdown completo de identidad  
✅ Drilldown por conductor funciona  
✅ Sistema es auditable (identity_source, match_confidence visibles)



