# Runbook: PAID_WITHOUT_ACHIEVEMENT - Comportamiento Esperado

**Versión:** 1.0  
**Fecha:** 2025-01-XX  
**Estado:** ACTIVO  
**Referencia:** Política oficial en `docs/policies/ct4_reconciliation_status_policy.md`

---

## 1. ¿Qué es PAID_WITHOUT_ACHIEVEMENT?

### Definición Corta

`PAID_WITHOUT_ACHIEVEMENT` es un estado de reconciliación que indica que **Yango pagó un milestone**, pero **no existe evidencia suficiente** en nuestro sistema operativo (`summary_daily`) para confirmar que el milestone fue alcanzado según nuestras reglas.

**Vista canónica:** `ops.v_cabinet_milestones_reconciled` (campo: `reconciliation_status = 'PAID_WITHOUT_ACHIEVEMENT'`)

---

### Por Qué Existe

1. **Yango tiene lógica propia de cálculo de milestones**
   - Yango puede calcular milestones según sus propios criterios
   - No necesariamente alineados con nuestra fuente operativa (`summary_daily`)

2. **Ventanas de tiempo distintas**
   - Yango puede usar ventanas distintas a las nuestras (`window_days`)
   - Pagos pueden ocurrir antes de que se registren todos los viajes

3. **Lag entre sistemas**
   - Puede haber delay entre cuando Yango paga y cuando se registran los trips en `summary_daily`
   - Los pagos pueden ser adelantados

4. **Criterios de negocio distintos**
   - Yango puede pagar según criterios propios (no necesariamente los mismos que usamos)

---

### Por Qué NO es un Bug

**❌ NO es un error ni bug del sistema.**

- El pago es **válido** reconocido por Yango (upstream)
- Es **comportamiento esperado** que los sistemas upstream tengan lógica propia
- No requiere **corrección** ni **recalculación**
- No es un **problema operativo** que necesite resolverse

**Política oficial:** Aceptar `PAID_WITHOUT_ACHIEVEMENT` como estado final válido, documentarlo, y usar queries de diagnóstico para auditoría.

---

## 2. Tipos de Casos (Resumen Operativo)

### UPSTREAM_OVERPAYMENT (Mayoría ~79%)

**Definición:** Yango pagó el milestone según sus criterios upstream, pero no existe evidencia suficiente en nuestro sistema operativo para confirmar que el milestone fue alcanzado.

**Características:**
- Caso **esperado** y **mayoritario**
- Pago válido reconocido por Yango
- No hay suficiente evidencia operativa en `summary_daily`
- No es un error

**Acción requerida:** **NINGUNA**. Es estado final válido.

---

### INSUFFICIENT_TRIPS_CONFIRMED (Edge Case ~21%)

**Definición:** Yango pagó el milestone, pero los trips confirmados en la ventana esperada (`[pay_date - window_days, pay_date]`) son insuficientes para alcanzar el milestone según nuestras reglas.

**Características:**
- Edge case minoritario
- Trips en ventana < milestone_value (ej: trips=3 pero milestone=5)
- Puede ser lag de datos, ventana distinta, o pago adelantado

**Acción requerida:** **Ninguna automática**. Monitorear si aumenta el porcentaje (>30%).

---

### IDENTITY_MISMATCH (0% actualmente)

**Definición:** Problema de identidad: existe ACHIEVED por `person_key` pero no por `driver_id`, o matching enriquecido problemático.

**Estado actual:** No presente en producción (0%).

**Acción requerida:** Si aparece, investigar caso por caso (no es comportamiento esperado masivo).

---

### WINDOW_MISMATCH (0% actualmente)

**Definición:** El pago ocurrió fuera de la ventana de vigencia de la regla aplicable.

**Estado actual:** No presente en producción (0%).

**Acción requerida:** Si aparece, verificar que la regla aplicada sea la correcta para la fecha del pago.

---

## 3. Procedimiento Estándar de Diagnóstico

### Paso 1: Ejecutar QUERY 2 (Conteos por Causa)

**Objetivo:** Obtener distribución estadística de causas.

**Archivo:** `backend/sql/ops/fase2_clasificacion_masiva_paid_without_achievement.sql` (QUERY 2)

**Qué revisar:**
- Distribución de causas (esperado: UPSTREAM_OVERPAYMENT ~79%, INSUFFICIENT_TRIPS_CONFIRMED ~21%)
- Distribución por milestone (M1, M5, M25)
- Si INSUFFICIENT_TRIPS_CONFIRMED > 30%, investigar posibles problemas de datos

**SQL Snippet:**

```sql
-- QUERY 2: CONTEOS POR CAUSA
-- (ver archivo completo para contexto)
SELECT 
    classification_cause,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT driver_id) AS distinct_drivers,
    COUNT(*) FILTER (WHERE milestone_value = 1) AS count_m1,
    COUNT(*) FILTER (WHERE milestone_value = 5) AS count_m5,
    COUNT(*) FILTER (WHERE milestone_value = 25) AS count_m25,
    ROUND(100.0 * COUNT(*) / NULLIF((SELECT COUNT(*) FROM classification), 0), 2) AS pct_total
FROM classification
GROUP BY classification_cause
ORDER BY total_rows DESC;
```

---

### Paso 2: Tomar Ejemplos con QUERY 3

**Objetivo:** Obtener ejemplos representativos de cada causa (hasta 10 por causa).

**Archivo:** `backend/sql/ops/fase2_clasificacion_masiva_paid_without_achievement.sql` (QUERY 3)

**Qué revisar:**
- Ejemplos de cada causa
- Evidencia: `trips_in_window`, `first_day_in_window`, `last_day_in_window`, `classification_evidence`
- Ordenados por `pay_date DESC` (más recientes primero)

**SQL Snippet:**

```sql
-- QUERY 3: EJEMPLOS POR CAUSA (limit 10 por causa)
-- (ver archivo completo para contexto)
SELECT 
    classification_cause,
    driver_id,
    milestone_value,
    pay_date,
    payment_key,
    window_days,
    valid_from,
    valid_to,
    trips_in_window,
    first_day_in_window,
    last_day_in_window,
    match_rule,
    match_confidence,
    driver_id_original,
    driver_id_enriched,
    person_key_original,
    classification_evidence
FROM classification
WHERE row_num <= 10
ORDER BY classification_cause, pay_date DESC, driver_id, milestone_value;
```

---

### Paso 3: Para un Driver Puntual, Usar Diagnóstico Individual

**Objetivo:** Analizar UN caso específico con toda la evidencia disponible.

**Archivo:** `backend/sql/ops/fase2_diagnostic_paid_without_achievement.sql`

**Qué revisar:**
- Detalles del PAID (cuándo pagó Yango, cómo se hizo el matching)
- Búsqueda exhaustiva en ACHIEVED (por `driver_id`, por `person_key`)
- Reglas de pago aplicables (`window_days`, `valid_from`, `valid_to`)
- Resumen de trips en ventana (si aplica)

**Uso:**
1. Editar el `WITH sample_case AS (...)` para filtrar por `driver_id` y `milestone_value` específicos
2. Ejecutar el query completo
3. Revisar evidencia: PAID, ACHIEVED_by_driver_id, ACHIEVED_by_person_key, PAYMENT_RULES, TRIPS_SUMMARY

**SQL Snippet (modificar sample_case):**

```sql
-- PASO 1: Seleccionar caso específico
WITH sample_case AS (
    SELECT 
        driver_id,
        milestone_value,
        paid_person_key,
        pay_date
    FROM ops.v_cabinet_milestones_reconciled
    WHERE reconciliation_status = 'PAID_WITHOUT_ACHIEVEMENT'
        AND driver_id = 'DRIVER_ID_AQUI'  -- MODIFICAR
        AND milestone_value = 5            -- MODIFICAR
    LIMIT 1
)
-- ... resto del query (ver archivo completo)
```

---

### Paso 4: Verificar Trips en summary_daily

**Objetivo:** Verificar trips confirmados en la ventana esperada.

**Tabla:** `public.summary_daily`

**Campos importantes:**
- `driver_id`: Identificador del driver
- `date_file`: Fecha del servicio (formato: 'DD-MM-YYYY', VARCHAR)
- `count_orders_completed`: Número de viajes completados

**Conversión de fecha:**
```sql
to_date(sd.date_file, 'DD-MM-YYYY') AS service_date
```

**Filtros importantes:**
- `WHERE sd.date_file IS NOT NULL`
- `WHERE sd.date_file ~ '^\d{2}-\d{2}-\d{4}$'` (validar formato)

**Query de ejemplo:**

```sql
-- Verificar trips en ventana [pay_date - window_days, pay_date]
SELECT 
    sd.driver_id,
    to_date(sd.date_file, 'DD-MM-YYYY') AS service_date,
    sd.count_orders_completed AS trips,
    SUM(sd.count_orders_completed) OVER (
        PARTITION BY sd.driver_id
        ORDER BY to_date(sd.date_file, 'DD-MM-YYYY')
        ROWS UNBOUNDED PRECEDING
    ) AS trips_cumulative
FROM public.summary_daily sd
WHERE sd.driver_id = 'DRIVER_ID_AQUI'  -- MODIFICAR
    AND sd.date_file IS NOT NULL
    AND sd.date_file ~ '^\d{2}-\d{2}-\d{4}$'
    AND to_date(sd.date_file, 'DD-MM-YYYY') >= '2025-01-01'  -- MODIFICAR: first_day_in_window
    AND to_date(sd.date_file, 'DD-MM-YYYY') <= '2025-01-31'  -- MODIFICAR: last_day_in_window (pay_date)
ORDER BY service_date;
```

---

## 4. SQL de Referencia

### 4.1 Conteo por Causa

**Archivo:** `backend/sql/ops/fase2_clasificacion_masiva_paid_without_achievement.sql` (QUERY 2)

**Uso:** Monitoreo periódico (mensual), reportes ejecutivos.

**Output esperado:**
```
classification_cause              | total_rows | distinct_drivers | count_m1 | count_m5 | count_m25 | pct_total
----------------------------------+------------+------------------+----------+----------+-----------+----------
UPSTREAM_OVERPAYMENT              | 41         | 41               | 27       | 10       | 4         | 78.85
INSUFFICIENT_TRIPS_CONFIRMED      | 11         | 11               | 7        | 3        | 1         | 21.15
```

---

### 4.2 Ejemplo por Causa

**Archivo:** `backend/sql/ops/fase2_clasificacion_masiva_paid_without_achievement.sql` (QUERY 3)

**Uso:** Auditoría de casos, análisis detallado.

**Output esperado:** Hasta 10 filas por causa, con evidencia completa (`trips_in_window`, `classification_evidence`, etc.).

---

### 4.3 Diagnóstico de Driver

**Archivo:** `backend/sql/ops/fase2_diagnostic_paid_without_achievement.sql`

**Uso:** Análisis de caso específico, investigación puntual.

**Output esperado:** Múltiples filas por tipo de evidencia (PAID, ACHIEVED_by_driver_id, ACHIEVED_by_person_key, PAYMENT_RULES, TRIPS_SUMMARY).

---

## 5. Cómo Responder a Yango (Plantillas)

### Respuesta Corta Técnica

**Plantilla:**

```
Asunto: Re: Consulta sobre milestone M5 pagado sin evidencia de M1

Hola [Nombre],

Hemos revisado el caso del driver [driver_id] con milestone M5 pagado.

Según nuestro análisis de reconciliación:
- Estado: PAID_WITHOUT_ACHIEVEMENT (UPSTREAM_OVERPAYMENT)
- Pago reconocido: [pay_date] por monto [amount]
- Evidencia en nuestro sistema: [trips_in_window] trips en ventana [first_day_in_window] a [last_day_in_window]
- Clasificación: Pago válido según criterios de Yango, sin evidencia suficiente en nuestro sistema operativo

Este estado es esperado cuando Yango aplica lógica propia de cálculo de milestones. No requiere acción correctiva.

Saludos,
[Tu nombre]
```

---

### Respuesta Ejecutiva

**Plantilla:**

```
Asunto: Re: Reconciliación de milestones - Análisis

Estimado [Nombre],

Hemos completado el análisis de reconciliación de milestones para el período [fecha_inicio] a [fecha_fin].

Resultados:
- Total de casos PAID_WITHOUT_ACHIEVEMENT: [total]
- Distribución: UPSTREAM_OVERPAYMENT [%], INSUFFICIENT_TRIPS_CONFIRMED [%]
- Estado: Comportamiento esperado, no requiere acción correctiva

Conclusión:
Los pagos reconocidos por Yango son válidos según sus criterios. La diferencia con nuestra evidencia operativa se debe a lógica propia de cálculo de milestones (comportamiento esperado).

No se requieren ajustes ni recalculaciones.

Saludos,
[Tu nombre]
```

---

## 6. Qué NO Hacer (Bloque Explícito)

### ❌ NO Recalcular Milestones Históricos

**Razón:** Viola el principio "el pasado no se corrige, se explica". Los milestones históricos son inmutables.

**Ejemplo de lo que NO hacer:**
```sql
-- ❌ NO HACER ESTO
UPDATE ops.v_payment_calculation 
SET milestone_achieved = true 
WHERE driver_id = 'X' AND milestone_trips = 5;
```

---

### ❌ NO Modificar Reglas

**Razón:** Las reglas de pago históricas (`ops.partner_payment_rules`) no se alteran. Cada pago se evalúa con la regla vigente en su momento.

**Ejemplo de lo que NO hacer:**
```sql
-- ❌ NO HACER ESTO
UPDATE ops.partner_payment_rules 
SET window_days = 30 
WHERE milestone_trips = 5;
```

---

### ❌ NO Reabrir Pagos Ya Ejecutados

**Razón:** Los pagos reconocidos por Yango (`ops.v_cabinet_milestones_paid`) son inmutables. Si Yango pagó, se acepta como válido.

**Ejemplo de lo que NO hacer:**
```sql
-- ❌ NO HACER ESTO
DELETE FROM ops.v_yango_payments_ledger_latest_enriched 
WHERE payment_key = 'X';
```

---

### ❌ NO Tratar PAID_WITHOUT_ACHIEVEMENT como Error

**Razón:** No es un error ni bug. Es comportamiento esperado del upstream.

**Ejemplo de lo que NO hacer:**
- Crear alertas automáticas para UPSTREAM_OVERPAYMENT
- Excluir pagos de facturación automáticamente
- Generar notificaciones de "error" para estos casos

---

## 7. Checklist de Cierre de Caso

### ✅ Evidencia Revisada

- [ ] QUERY 2 ejecutado (conteos por causa)
- [ ] QUERY 3 ejecutado (ejemplos por causa)
- [ ] Diagnóstico individual ejecutado (si aplica)
- [ ] Trips en `summary_daily` verificados (si aplica)
- [ ] Distribución de causas documentada

---

### ✅ Clasificación Asignada

- [ ] Causa identificada (UPSTREAM_OVERPAYMENT, INSUFFICIENT_TRIPS_CONFIRMED, etc.)
- [ ] Evidencia revisada (`trips_in_window`, `classification_evidence`, etc.)
- [ ] Clasificación alineada con políticas oficiales

---

### ✅ Conclusión Documentada

- [ ] Estado documentado (PAID_WITHOUT_ACHIEVEMENT + subclasificación)
- [ ] Conclusión clara: "Comportamiento esperado, no requiere acción correctiva"
- [ ] Respuesta a Yango generada (si aplica)
- [ ] Hallazgos documentados en runbook o notas (si aplica)

---

## 8. Referencias

### Documentos Relacionados

- **Política oficial:** `docs/policies/ct4_reconciliation_status_policy.md`
- **FASE 0 (Lineage):** `docs/runbooks/fase0_inventario_lineage_milestones.md`
- **FASE 1 (Separación semántica):** `docs/runbooks/fase1_separacion_semantica_achieved_paid_reconciled.md`

### SQL de Diagnóstico

- **Clasificación masiva:** `backend/sql/ops/fase2_clasificacion_masiva_paid_without_achievement.sql`
- **Diagnóstico individual:** `backend/sql/ops/fase2_diagnostic_paid_without_achievement.sql`
- **Queries finales:** `backend/sql/ops/fase2_queries_finales.sql`

### Vistas Canónicas

- **Reconciliación:** `ops.v_cabinet_milestones_reconciled`
- **Milestones logrados:** `ops.v_cabinet_milestones_achieved`
- **Milestones pagados:** `ops.v_cabinet_milestones_paid`

---

**Fin del runbook**




