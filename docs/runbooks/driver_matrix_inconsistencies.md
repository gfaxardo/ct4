# Driver Matrix - Inconsistencias M5 sin M1

## Contexto

La vista `ops.v_payments_driver_matrix_cabinet` muestra casos donde un driver tiene datos para M5 (milestone 5) pero M1 (milestone 1) aparece vacío (NULL). Este documento describe las 4 causas probables y cómo diagnosticarlas.

## Vista Utilizada

**Endpoint:** `GET /api/v1/ops/payments/driver-matrix`  
**Vista:** `ops.v_payments_driver_matrix_cabinet`  
**Grano:** 1 fila por `driver_id` (con agregación por `GROUP BY bc.driver_id`)

## Causas Probables

### 1. Missing Claim M1

**Descripción:**  
El driver alcanzó M5 pero nunca tuvo un claim M1 registrado en `ops.v_claims_payment_status_cabinet`.

**Por qué ocurre:**
- El driver se registró después de alcanzar M5 directamente
- El claim M1 no se generó por error en el proceso de cálculo
- El driver fue migrado desde otra fuente sin historial completo

**Cómo diagnosticar:**
```sql
-- Verificar si hay drivers con M5 pero sin M1 en claims base
SELECT DISTINCT driver_id
FROM ops.v_claims_payment_status_cabinet
WHERE milestone_value = 5
    AND driver_id NOT IN (
        SELECT DISTINCT driver_id
        FROM ops.v_claims_payment_status_cabinet
        WHERE milestone_value = 1
    );
```

**Impacto:**  
La vista muestra correctamente que M1 no existe, pero puede ser confuso para el usuario ver M5 sin M1.

---

### 2. Mismatch Identidad/Join

**Descripción:**  
El claim M1 existe en `ops.v_claims_payment_status_cabinet` pero no hace match con `ops.v_yango_cabinet_claims_for_collection` debido a diferencias en:
- `driver_id` (diferente formato o valor)
- `lead_date` (fechas no coinciden exactamente)
- `person_key` (mismatch en identidad canónica)

**Por qué ocurre:**
- El `driver_id` cambió entre el cálculo de claims y la reconciliación Yango
- El `lead_date` tiene diferencias de tiempo (horas/minutos) que impiden el join
- Problemas de identidad canónica donde `person_key` no está sincronizado

**Cómo diagnosticar:**
```sql
-- Verificar M1 en claims pero sin match en Yango
SELECT c.driver_id, c.lead_date, c.milestone_value
FROM ops.v_claims_payment_status_cabinet c
WHERE c.milestone_value = 1
    AND NOT EXISTS (
        SELECT 1
        FROM ops.v_yango_cabinet_claims_for_collection y
        WHERE y.driver_id = c.driver_id
            AND y.milestone_value = 1
            AND y.lead_date = c.lead_date
    );
```

**Impacto:**  
El claim M1 existe pero no se enriquece con `yango_payment_status`, resultando en NULL en la vista final.

---

### 3. Split de Semanas por lead_date/week_start

**Descripción:**  
El driver tiene múltiples filas en la vista debido a que M1 y M5 tienen `week_start` diferentes, causando que aparezcan en filas separadas. La vista agrupa por `driver_id` pero si hay múltiples `week_start`, puede haber múltiples filas.

**Por qué ocurre:**
- M1 se alcanzó en una semana (week_start = '2025-01-06')
- M5 se alcanzó en otra semana (week_start = '2025-01-13')
- La vista puede estar generando filas separadas si el GROUP BY no está agrupando correctamente

**Cómo diagnosticar:**
```sql
-- Verificar drivers con múltiples week_start
SELECT 
    driver_id,
    COUNT(DISTINCT week_start) AS num_semanas,
    ARRAY_AGG(DISTINCT week_start ORDER BY week_start) AS semanas
FROM ops.v_payments_driver_matrix_cabinet
WHERE m5_yango_payment_status IS NOT NULL 
    AND m1_yango_payment_status IS NULL
GROUP BY driver_id
HAVING COUNT(DISTINCT week_start) > 1;
```

**Impacto:**  
El driver aparece en múltiples filas, una con M1 y otra con M5, en lugar de una sola fila con ambos milestones.

---

### 4. Múltiples Ciclos por Driver y GROUP BY bc.driver_id

**Descripción:**  
El `GROUP BY bc.driver_id` en la vista está agrupando múltiples claims del mismo driver, y cuando hay múltiples claims M1 o M5, el `MAX()` puede estar seleccionando el claim incorrecto o NULL si los joins no coinciden.

**Por qué ocurre:**
- Un driver puede tener múltiples claims M1 (por ejemplo, en diferentes fechas)
- El `MAX(CASE WHEN bc.milestone_value = 1 THEN ...)` puede estar seleccionando un claim que no tiene match en las tablas de enriquecimiento (Yango, window_status)
- Si hay múltiples claims M5 pero solo uno tiene match en Yango, M5 aparece pero M1 no

**Cómo diagnosticar:**
```sql
-- Verificar múltiples claims por driver
SELECT 
    bc.driver_id,
    bc.milestone_value,
    COUNT(*) AS num_claims,
    ARRAY_AGG(bc.lead_date ORDER BY bc.lead_date) AS lead_dates
FROM ops.v_claims_payment_status_cabinet bc
WHERE bc.milestone_value IN (1, 5)
GROUP BY bc.driver_id, bc.milestone_value
HAVING COUNT(*) > 1;

-- Verificar si el MAX() está seleccionando claims sin match
WITH claims_with_yango AS (
    SELECT 
        c.driver_id,
        c.milestone_value,
        c.lead_date,
        y.yango_payment_status
    FROM ops.v_claims_payment_status_cabinet c
    LEFT JOIN ops.v_yango_cabinet_claims_for_collection y
        ON c.driver_id = y.driver_id
        AND c.milestone_value = y.milestone_value
        AND c.lead_date = y.lead_date
    WHERE c.milestone_value = 1
)
SELECT 
    driver_id,
    COUNT(*) AS total_claims_m1,
    COUNT(yango_payment_status) AS claims_con_yango_status
FROM claims_with_yango
GROUP BY driver_id
HAVING COUNT(*) > COUNT(yango_payment_status);
```

**Impacto:**  
El `MAX()` puede estar seleccionando un claim M1 que no tiene match en las tablas de enriquecimiento, resultando en NULL para `m1_yango_payment_status` mientras que M5 sí tiene match.

---

## Script de Diagnóstico

Ver archivo: `backend/sql/ops/_debug_driver_matrix_m5_without_m1.sql`

Este script incluye:
- Conteo por `origin_tag` de casos M5 sin M1
- Sample de 30 filas con columnas clave
- Queries parametrizables por `driver_id` para revisar:
  - `ops.v_claims_payment_status_cabinet`
  - `ops.v_yango_cabinet_claims_for_collection`
  - Múltiples ciclos/semanas
  - Joins/identidad

## Próximos Pasos

1. **Ejecutar script de diagnóstico** para identificar la causa predominante
2. **Revisar casos específicos** usando las queries parametrizables
3. **Validar la lógica de la vista** `ops.v_payments_driver_matrix_cabinet`:
   - Verificar si el `GROUP BY` está agrupando correctamente
   - Revisar los joins con las tablas de enriquecimiento
   - Considerar si se necesita ajustar la lógica de agregación
4. **Implementar correcciones** según la causa identificada

## Referencias

- Vista: `backend/sql/ops/v_payments_driver_matrix_cabinet.sql`
- Endpoint: `backend/app/api/v1/ops_payments.py` (función `get_driver_matrix`)
- Fuentes:
  - `ops.v_claims_payment_status_cabinet`
  - `ops.v_yango_cabinet_claims_for_collection`
  - `ops.v_yango_payments_claims_cabinet_14d`





