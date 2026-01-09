# Modelo Financiero CABINET - Fuente de Verdad 14 Días

## Propósito

La vista `ops.v_cabinet_financial_14d` es la **fuente de verdad financiera** para CABINET que permite determinar con exactitud qué conductores generan pago de Yango y detectar deudas por milestones no pagados.

**Objetivo principal:** Responder sin ambigüedad: *"Yango nos debe X soles por estos drivers y estos hitos"*.

## Contexto de Negocio

### Origen
- **Origen:** `cabinet` (origin_tag = 'cabinet')
- **Ventana financiera:** 14 días desde `lead_date`
- **Fuente operativa de viajes:** `public.summary_daily` (count_orders_completed)
- **Fuente de claims/pagos:** `ops.v_claims_payment_status_cabinet`

### Reglas Yango (Acumulativo)

Los pagos de Yango son **acumulativos** según los milestones alcanzados dentro de la ventana de 14 días:

| Milestone | Viajes Requeridos | Monto Adicional | Monto Acumulado |
|-----------|-------------------|-----------------|-----------------|
| M1        | 1 viaje en 14d    | S/ 25           | S/ 25           |
| M5        | 5 viajes en 14d   | +S/ 35          | S/ 60 (25+35)   |
| M25       | 25 viajes en 14d  | +S/ 100         | S/ 160 (25+35+100) |

**Ejemplo:**
- Driver con 30 viajes en 14d → Alcanza M1, M5 y M25 → Debe recibir S/ 160 total
- Driver con 10 viajes en 14d → Alcanza M1 y M5 → Debe recibir S/ 60 total
- Driver con 3 viajes en 14d → Alcanza solo M1 → Debe recibir S/ 25 total

### Reglas Clave

1. **Un milestone solo existe financieramente si se alcanza dentro de los 14 días.**
   - Si un driver alcanza M1 en el día 15, NO genera pago de Yango.
   - La ventana es estricta: desde `lead_date` hasta `lead_date + 14 días`.

2. **NO usar achieved histórico sin ventana.**
   - Solo se consideran viajes dentro de la ventana de 14 días.
   - Viajes fuera de la ventana no cuentan para milestones financieros.

3. **summary_daily es la única fuente de viajes.**
   - No se usan otras fuentes de viajes.
   - Solo `count_orders_completed` desde `public.summary_daily`.

4. **Claim ≠ Pago**
   - Un claim puede ser `PAID`, `UNPAID` o `MISAPPLIED`.
   - La vista distingue entre existencia de claim y estado de pago.

## Estructura de la Vista

### Grano
**1 fila por driver_id** (GARANTIZADO)

### Campos Principales

#### 1. Información Base
- `driver_id`: ID del conductor
- `lead_date`: Fecha de lead desde `observational.v_conversion_metrics`
- `connected_flag`: Flag indicando si el driver se conectó
- `connected_date`: Primera fecha de conexión

#### 2. Viajes y Milestones
- `total_trips_14d`: Total de viajes completados dentro de la ventana de 14 días
- `reached_m1_14d`: Flag indicando si alcanzó M1 dentro de la ventana
- `reached_m5_14d`: Flag indicando si alcanzó M5 dentro de la ventana
- `reached_m25_14d`: Flag indicando si alcanzó M25 dentro de la ventana

#### 3. Montos Esperados
- `expected_amount_m1`: Monto esperado para M1 (S/ 25 si alcanzado, 0 si no)
- `expected_amount_m5`: Monto esperado para M5 (S/ 35 si alcanzado, 0 si no)
- `expected_amount_m25`: Monto esperado para M25 (S/ 100 si alcanzado, 0 si no)
- `expected_total_yango`: Total esperado acumulativo (suma de M1 + M5 + M25)

#### 4. Estado de Claims
- `claim_m1_exists`: Flag indicando si existe claim M1
- `claim_m1_paid`: Flag indicando si claim M1 está pagado
- `claim_m5_exists`: Flag indicando si existe claim M5
- `claim_m5_paid`: Flag indicando si claim M5 está pagado
- `claim_m25_exists`: Flag indicando si existe claim M25
- `claim_m25_paid`: Flag indicando si claim M25 está pagado

#### 5. Montos Pagados
- `paid_amount_m1`: Monto pagado para M1
- `paid_amount_m5`: Monto pagado para M5
- `paid_amount_m25`: Monto pagado para M25
- `total_paid_yango`: Total pagado por Yango (suma de M1 + M5 + M25)

#### 6. Deuda Pendiente
- `amount_due_yango`: Monto faltante por cobrar a Yango
  - Cálculo: `expected_total_yango - total_paid_yango`
  - Valor positivo indica deuda pendiente

## Cálculo de Milestones

### Lógica de Cálculo

Los milestones se calculan **determinísticamente** desde `summary_daily` dentro de la ventana de 14 días:

```sql
-- M1 alcanzado si total_trips_14d >= 1
reached_m1_14d = (total_trips_14d >= 1)

-- M5 alcanzado si total_trips_14d >= 5
reached_m5_14d = (total_trips_14d >= 5)

-- M25 alcanzado si total_trips_14d >= 25
reached_m25_14d = (total_trips_14d >= 25)
```

### Coherencia Acumulativa

La vista **garantiza coherencia acumulativa**:
- Si `reached_m5_14d = true`, entonces `reached_m1_14d = true`
- Si `reached_m25_14d = true`, entonces `reached_m5_14d = true` y `reached_m1_14d = true`

Esto se logra mediante la lógica de cálculo basada en `total_trips_14d`.

## Cálculo de Montos

### Montos Esperados

Los montos esperados se calculan según los milestones alcanzados:

```sql
expected_amount_m1 = CASE 
    WHEN total_trips_14d >= 1 THEN 25 
    ELSE 0 
END

expected_amount_m5 = CASE 
    WHEN total_trips_14d >= 5 THEN 35 
    ELSE 0 
END

expected_amount_m25 = CASE 
    WHEN total_trips_14d >= 25 THEN 100 
    ELSE 0 
END

expected_total_yango = CASE 
    WHEN total_trips_14d >= 25 THEN (25 + 35 + 100)  -- 160
    WHEN total_trips_14d >= 5 THEN (25 + 35)         -- 60
    WHEN total_trips_14d >= 1 THEN 25               -- 25
    ELSE 0
END
```

### Montos Pagados

Los montos pagados provienen de `ops.v_claims_payment_status_cabinet`:
- Solo se consideran claims con `paid_flag = true`
- Si no hay claim o el claim no está pagado, el monto pagado es 0

### Deuda Pendiente

```sql
amount_due_yango = expected_total_yango - total_paid_yango
```

**Interpretación:**
- `amount_due_yango > 0`: Yango debe dinero (deuda pendiente)
- `amount_due_yango = 0`: Pagado completamente
- `amount_due_yango < 0`: Sobrepago (caso excepcional, requiere investigación)

## Fuentes de Datos

### 1. lead_date y connected_date
- **Fuente:** `observational.v_conversion_metrics`
- **Filtro:** `origin_tag = 'cabinet'`
- **Deduplicación:** `DISTINCT ON (driver_id) ORDER BY lead_date DESC`

### 2. Viajes (summary_daily)
- **Fuente:** `public.summary_daily`
- **Campo:** `count_orders_completed`
- **Fecha:** `to_date(date_file, 'DD-MM-YYYY')`
- **Ventana:** `prod_date >= lead_date AND prod_date < lead_date + 14 días`

### 3. Claims y Pagos
- **Fuente:** `ops.v_claims_payment_status_cabinet`
- **Filtro:** `milestone_value IN (1, 5, 25)`
- **Estado de pago:** `paid_flag = true`

## Casos de Uso

### 1. Detectar Deudas Pendientes

```sql
SELECT 
    driver_id,
    lead_date,
    total_trips_14d,
    expected_total_yango,
    total_paid_yango,
    amount_due_yango
FROM ops.v_cabinet_financial_14d
WHERE amount_due_yango > 0
ORDER BY amount_due_yango DESC;
```

### 2. Drivers con Milestones Alcanzados sin Claim

```sql
SELECT 
    driver_id,
    lead_date,
    total_trips_14d,
    reached_m1_14d,
    reached_m5_14d,
    reached_m25_14d,
    expected_total_yango,
    claim_m1_exists,
    claim_m5_exists,
    claim_m25_exists
FROM ops.v_cabinet_financial_14d
WHERE (reached_m1_14d = true AND claim_m1_exists = false)
    OR (reached_m5_14d = true AND claim_m5_exists = false)
    OR (reached_m25_14d = true AND claim_m25_exists = false);
```

### 3. Resumen Ejecutivo de Cobranza

```sql
SELECT 
    COUNT(*) AS total_drivers,
    SUM(expected_total_yango) AS total_esperado,
    SUM(total_paid_yango) AS total_pagado,
    SUM(amount_due_yango) AS total_deuda,
    ROUND((SUM(total_paid_yango) / NULLIF(SUM(expected_total_yango), 0)) * 100, 2) AS porcentaje_cobranza
FROM ops.v_cabinet_financial_14d
WHERE expected_total_yango > 0;
```

## Validación y Verificación

### Script de Verificación

El script `backend/scripts/sql/verify_cabinet_financial_14d.sql` incluye los siguientes checks:

1. **CHECK 1:** Drivers con viajes >= hito sin claim
   - Detecta drivers que alcanzaron milestones pero no tienen claim registrado

2. **CHECK 2:** Drivers con claim sin cumplir viajes
   - Detecta drivers con claims pero que no alcanzaron el milestone dentro de la ventana

3. **CHECK 3:** Total esperado vs total pagado
   - Compara montos esperados vs pagados para detectar discrepancias

4. **CHECK 4:** Coherencia de milestones acumulativos
   - Verifica que si M5 está alcanzado, M1 también lo esté

### Ejecutar Verificación

```sql
\i backend/scripts/sql/verify_cabinet_financial_14d.sql
```

## Limitaciones y Consideraciones

### 1. Ventana Estricta de 14 Días
- Solo se consideran viajes dentro de la ventana de 14 días desde `lead_date`
- Viajes fuera de la ventana no generan pago de Yango

### 2. Fuente Única de Viajes
- Solo se usa `summary_daily` como fuente de viajes
- No se consideran otras fuentes de datos de viajes

### 3. Claim vs Pago
- La vista distingue entre existencia de claim y estado de pago
- Un claim puede existir pero no estar pagado (`UNPAID`)
- Un claim puede estar pagado pero no corresponder al milestone (`MISAPPLIED`)

### 4. Ventana de Tiempo
- La vista calcula milestones basándose en la ventana de 14 días desde `lead_date`
- No considera milestones alcanzados fuera de esta ventana

## Mantenimiento

### Actualización de la Vista

La vista se actualiza automáticamente cuando se ejecutan las vistas base:
- `observational.v_conversion_metrics` (lead_date, connected_date)
- `public.summary_daily` (viajes)
- `ops.v_claims_payment_status_cabinet` (claims y pagos)

### Monitoreo

Se recomienda ejecutar el script de verificación periódicamente para detectar inconsistencias:
- Semanalmente para monitoreo de cobranza
- Antes de reportes financieros a Yango
- Después de cambios en las vistas base

## Relación con Otras Vistas

### Vistas Base
- `observational.v_conversion_metrics`: lead_date, connected_date
- `public.summary_daily`: viajes operativos
- `ops.v_claims_payment_status_cabinet`: claims y pagos

### Vistas Relacionadas
- `ops.v_cabinet_ops_14d_sanity`: Sanity check operativo (similar pero sin lógica financiera)
- `ops.v_payments_driver_matrix_cabinet`: Vista de presentación (UI)

## Ejemplos de Consultas

### Ejemplo 1: Total de Deuda Pendiente

```sql
SELECT 
    SUM(amount_due_yango) AS total_deuda_yango,
    COUNT(CASE WHEN amount_due_yango > 0 THEN 1 END) AS drivers_con_deuda
FROM ops.v_cabinet_financial_14d
WHERE amount_due_yango > 0;
```

### Ejemplo 2: Drivers por Milestone Alcanzado

```sql
SELECT 
    COUNT(CASE WHEN reached_m1_14d = true THEN 1 END) AS drivers_m1,
    COUNT(CASE WHEN reached_m5_14d = true THEN 1 END) AS drivers_m5,
    COUNT(CASE WHEN reached_m25_14d = true THEN 1 END) AS drivers_m25
FROM ops.v_cabinet_financial_14d;
```

### Ejemplo 3: Análisis de Cobranza por Milestone

```sql
SELECT 
    'M1' AS milestone,
    COUNT(CASE WHEN reached_m1_14d = true THEN 1 END) AS alcanzados,
    COUNT(CASE WHEN claim_m1_paid = true THEN 1 END) AS pagados,
    SUM(expected_amount_m1) AS total_esperado,
    SUM(paid_amount_m1) AS total_pagado,
    SUM(expected_amount_m1 - paid_amount_m1) AS total_deuda
FROM ops.v_cabinet_financial_14d
WHERE reached_m1_14d = true;
```

## Conclusión

La vista `ops.v_cabinet_financial_14d` proporciona una **fuente de verdad financiera** clara y determinística para CABINET, permitiendo:

1. **Determinar exactamente** qué conductores generan pago de Yango
2. **Detectar deudas** por milestones no pagados
3. **Validar coherencia** entre viajes, milestones y claims
4. **Responder sin ambigüedad** a la pregunta: "Yango nos debe X soles por estos drivers y estos hitos"

La vista está diseñada para ser **read-only** y **determinística**, basándose únicamente en datos operativos reales (`summary_daily`) dentro de la ventana financiera de 14 días.




