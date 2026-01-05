# Política: Reconciliation Status en CT4

**Versión:** 1.0  
**Fecha:** 2025-01-XX  
**Estado:** ACTIVO  
**Aplica a:** Sistema CT4 - Capas C2 (ACHIEVED), C4 (PAID), C3 (RECONCILED)

---

## 1. Propósito

Este documento establece la política oficial para interpretar y gestionar los estados de reconciliación entre milestones ACHIEVED (logrados operativamente) y PAID (pagos reconocidos por upstream/Yango).

**Alcance:**
- Define estados válidos de `reconciliation_status` en `ops.v_cabinet_milestones_reconciled`
- Establece principios rectores para no corregir el pasado
- Proporciona guía operativa para auditoría y diagnóstico
- Documenta subclasificación de `PAID_WITHOUT_ACHIEVEMENT`

**Audiencia:**
- Arquitectos de datos
- Analistas operativos
- Desarrolladores que consumen vistas de reconciliación

---

## 2. Definiciones de Estados

### 2.1 Estados Principales (mutuamente excluyentes)

| Estado | Definición | Interpretación |
|--------|------------|----------------|
| **OK** | Milestone alcanzado Y pagado | Estado esperado: el driver logró el milestone y Yango lo reconoció. |
| **ACHIEVED_NOT_PAID** | Milestone alcanzado pero NO pagado | Estado de cobranza: el driver logró el milestone, Yango aún no lo pagó. |
| **PAID_WITHOUT_ACHIEVEMENT** | Milestone pagado pero NO alcanzado | Estado upstream: Yango pagó el milestone sin evidencia suficiente en nuestro sistema operativo. **Es válido y no es un bug.** |
| **NOT_APPLICABLE** | Ni alcanzado ni pagado | No debería aparecer en producción. Si aparece, investigar. |

### 2.2 Fuentes de Verdad

- **ACHIEVED:** `ops.v_cabinet_milestones_achieved` (vista canónica C2)
  - Fuente: `ops.v_payment_calculation`
  - Basado en: `public.summary_daily.count_orders_completed` (viajes reales)
  
- **PAID:** `ops.v_cabinet_milestones_paid` (vista canónica C4)
  - Fuente: `ops.v_yango_payments_ledger_latest_enriched`
  - Basado en: Pagos reconocidos por Yango (upstream)

- **RECONCILED:** `ops.v_cabinet_milestones_reconciled` (vista C3)
  - JOIN explícito: ACHIEVED ⟕ PAID
  - Campo: `reconciliation_status`

---

## 3. Subclasificación de PAID_WITHOUT_ACHIEVEMENT

Cuando `reconciliation_status = 'PAID_WITHOUT_ACHIEVEMENT'`, el sistema clasifica automáticamente la causa en 4 subcategorías (mutuamente excluyentes):

### 3.1 UPSTREAM_OVERPAYMENT (mayoría ~79%)

**Definición:** Yango pagó el milestone según sus reglas/criterios upstream, pero no existe evidencia suficiente en nuestro sistema operativo (`summary_daily`) para confirmar que el milestone fue alcanzado.

**Características:**
- Pago válido reconocido por Yango (upstream)
- No hay suficiente evidencia operativa en nuestra fuente (`summary_daily`)
- No es un error ni bug
- Es comportamiento esperado del upstream

**Causas posibles:**
- Yango tiene lógica propia de cálculo de milestones
- Ventanas de tiempo distintas entre sistemas
- Lag de datos entre sistemas
- Criterios de negocio distintos (Yango paga antes de confirmación operativa)

**Acción requerida:** Ninguna. Es estado final válido.

---

### 3.2 INSUFFICIENT_TRIPS_CONFIRMED (minoría ~21%)

**Definición:** Yango pagó el milestone, pero los trips confirmados en la ventana esperada (`[pay_date - window_days, pay_date]`) son insuficientes para alcanzar el milestone según nuestras reglas.

**Características:**
- Pago válido reconocido por Yango
- Trips en ventana < milestone_value (ej: trips=3 pero milestone=5)
- Puede ser lag de datos, ventana distinta, o pago adelantado

**Causas posibles:**
- Lag entre cuando Yango pagó y cuando se registraron los trips en `summary_daily`
- Yango usa ventana distinta a la nuestra
- Pago adelantado (Yango pagó antes de completar todos los viajes)

**Acción requerida:** Ninguna automática. Monitorear si aumenta el porcentaje.

---

### 3.3 IDENTITY_MISMATCH (0% en producción actual)

**Definición:** Problema de identidad: existe ACHIEVED por `person_key` pero no por `driver_id`, o matching enriquecido problemático.

**Características:**
- Se encontró ACHIEVED por person_key pero no por driver_id
- O `driver_id_enriched` != `driver_id_original` con `match_confidence != 'high'`

**Causas posibles:**
- Problema de matching de identidad
- Cambio de driver_id en el tiempo

**Acción requerida:** Si aparece, investigar caso por caso (no es comportamiento esperado masivo).

---

### 3.4 WINDOW_MISMATCH (0% en producción actual)

**Definición:** El pago ocurrió fuera de la ventana de vigencia de la regla aplicable.

**Características:**
- `pay_date < rule_valid_from` o `pay_date > rule_valid_to`
- La regla no estaba vigente cuando se pagó

**Causas posibles:**
- Cambio de reglas de pago
- Pago antiguo con regla nueva aplicada

**Acción requerida:** Si aparece, verificar que la regla aplicada sea la correcta para la fecha del pago.

---

## 4. Principio Rector

### "El pasado no se corrige, se explica"

**Reglas duras:**

1. **NO recalcular milestones históricos**
   - Los milestones ya calculados (`ops.v_payment_calculation`) son inmutables
   - Si un milestone fue alcanzado en el pasado, no se modifica

2. **NO modificar reglas pasadas**
   - Las reglas de pago históricas (`ops.partner_payment_rules`) no se alteran
   - Cada pago se evalúa con la regla vigente en su momento

3. **NO cambiar pagos ya hechos**
   - Los pagos reconocidos por Yango (`ops.v_cabinet_milestones_paid`) son inmutables
   - Si Yango pagó, se acepta como válido

4. **Todo debe ser defendible con SQL y evidencia**
   - Cada estado debe poder explicarse con queries SQL
   - La evidencia debe estar disponible en las vistas canónicas

5. **Priorizar estabilidad operativa**
   - No romper compatibilidad con sistemas existentes
   - No introducir cambios que afecten pagos en curso

---

## 5. Guía Operativa

### 5.1 Qué NO Hacer

**❌ NO hacer:**
- Recalcular milestones históricos para "corregir" PAID_WITHOUT_ACHIEVEMENT
- Modificar reglas de pago retroactivamente
- Excluir pagos ya reconocidos por Yango
- Cambiar la lógica de cálculo de `ops.v_payment_calculation` por casos PAID_WITHOUT_ACHIEVEMENT
- Generar acciones automáticas (alertas, notificaciones) para UPSTREAM_OVERPAYMENT
- Tratar PAID_WITHOUT_ACHIEVEMENT como un error que requiere corrección

---

### 5.2 Qué SÍ Hacer

**✅ SÍ hacer:**
- **Auditar con queries de diagnóstico:**
  - Usar `backend/sql/ops/fase2_diagnostic_paid_without_achievement.sql` para análisis de casos individuales
  - Usar `backend/sql/ops/fase2_clasificacion_masiva_paid_without_achievement.sql` para clasificación masiva y conteos

- **Documentar hallazgos:**
  - Si se encuentra un patrón inesperado, documentarlo en runbooks
  - Usar las vistas de reconciliación (`ops.v_cabinet_milestones_reconciled`) para reportes

- **Monitorear tendencias:**
  - Ejecutar QUERY 2 (conteos por causa) periódicamente
  - Si INSUFFICIENT_TRIPS_CONFIRMED aumenta significativamente, investigar posibles problemas de datos

- **Usar vistas canónicas:**
  - Para diagnóstico: `ops.v_cabinet_milestones_reconciled`
  - Para milestones logrados: `ops.v_cabinet_milestones_achieved`
  - Para pagos: `ops.v_cabinet_milestones_paid`

---

## 6. Referencias SQL

### 6.1 Diagnóstico de Casos Individuales

**Archivo:** `backend/sql/ops/fase2_diagnostic_paid_without_achievement.sql`

**Propósito:** Analizar UN caso específico de PAID_WITHOUT_ACHIEVEMENT con toda la evidencia disponible.

**Cuándo usar:**
- Necesitas entender por qué un driver específico tiene PAID_WITHOUT_ACHIEVEMENT
- Quieres verificar la evidencia completa (PAID, ACHIEVED, reglas, trips)

**Output:** Evidencia completa del caso (PAID details, ACHIEVED search, payment rules, trips summary)

---

### 6.2 Clasificación Masiva

**Archivo:** `backend/sql/ops/fase2_clasificacion_masiva_paid_without_achievement.sql`

**Contiene 3 queries:**

**QUERY 1: Clasificación Masiva**
- Clasifica TODOS los casos PAID_WITHOUT_ACHIEVEMENT en las 4 subcategorías
- Incluye evidencia: `trips_in_window`, `first_day_in_window`, `last_day_in_window`, `classification_evidence`

**QUERY 2: Conteos por Causa**
- Resumen estadístico: total_rows, distinct_drivers, distribución por milestone (M1/M5/M25), porcentaje del total

**QUERY 3: Ejemplos por Causa**
- Hasta 10 ejemplos de cada causa para análisis detallado
- Ordenados por `pay_date DESC` (más recientes primero)

**Cuándo usar:**
- Monitoreo periódico de distribución de causas
- Auditoría masiva de PAID_WITHOUT_ACHIEVEMENT
- Reportes ejecutivos

---

## 7. Interpretación de Resultados

### 7.1 Distribución Esperada

Basado en análisis de producción:

- **UPSTREAM_OVERPAYMENT:** ~79% (mayoría)
  - **Interpretación:** Normal. Yango paga según sus criterios, no necesariamente alineados con nuestra evidencia operativa.
  - **Acción:** Ninguna. Es comportamiento esperado.

- **INSUFFICIENT_TRIPS_CONFIRMED:** ~21% (minoría)
  - **Interpretación:** Normal con lag/ventanas. Trips insuficientes en ventana pero Yango pagó.
  - **Acción:** Monitorear si aumenta. No requiere acción automática.

- **IDENTITY_MISMATCH:** 0% (no presente)
  - **Interpretación:** Sistema de identidad funcionando correctamente.
  - **Acción:** Si aparece, investigar caso por caso.

- **WINDOW_MISMATCH:** 0% (no presente)
  - **Interpretación:** Reglas aplicadas correctamente según vigencia.
  - **Acción:** Si aparece, verificar regla aplicada.

### 7.2 Señales de Alerta

**⚠️ Investigar si:**
- INSUFFICIENT_TRIPS_CONFIRMED aumenta significativamente (>30%)
- IDENTITY_MISMATCH aparece (no debería en producción estable)
- WINDOW_MISMATCH aparece (no debería en producción estable)
- NOT_APPLICABLE aparece en producción (no debería)

**✅ Normal si:**
- UPSTREAM_OVERPAYMENT es mayoría (70-85%)
- INSUFFICIENT_TRIPS_CONFIRMED es minoría (15-25%)
- IDENTITY_MISMATCH y WINDOW_MISMATCH son 0% o mínimos (<1%)

---

## 8. Workflow Operativo

### 8.1 Monitoreo Regular (Mensual)

1. Ejecutar QUERY 2 (`fase2_clasificacion_masiva_paid_without_achievement.sql`)
2. Verificar distribución de causas
3. Comparar con distribución esperada
4. Si hay desviaciones significativas, investigar con QUERY 3

### 8.2 Auditoría de Caso Específico

1. Identificar driver_id y milestone_value del caso
2. Ejecutar QUERY 1 (`fase2_diagnostic_paid_without_achievement.sql`)
3. Revisar evidencia completa
4. Documentar hallazgo si es inesperado

### 8.3 Reporte Ejecutivo

1. Ejecutar QUERY 2 (conteos)
2. Ejecutar QUERY 3 (ejemplos por causa)
3. Generar reporte con distribución y casos de ejemplo
4. No incluir recomendaciones de "corrección" (los estados son válidos)

---

## 9. Casos de Uso

### 9.1 "¿Por qué este driver tiene M5 pagado pero no M1 logrado?"

**Respuesta:**
1. Verificar `ops.v_cabinet_milestones_reconciled` con `reconciliation_status = 'PAID_WITHOUT_ACHIEVEMENT'`
2. Si existe, ejecutar QUERY 1 para clasificar la causa
3. Explicar que es comportamiento válido de upstream (no es bug)
4. Si es UPSTREAM_OVERPAYMENT, documentar como esperado

### 9.2 "¿Debemos excluir estos pagos de facturación?"

**Respuesta:**
- **NO.** Los pagos ya fueron reconocidos por Yango y son válidos.
- Si se necesita identificar pagos "sospechosos" para revisión manual, usar QUERY 3 con filtro por causa.
- No implementar exclusión automática.

### 9.3 "¿Debemos corregir milestones históricos?"

**Respuesta:**
- **NO.** Viola el principio "el pasado no se corrige, se explica".
- Los milestones históricos son inmutables.
- Usar queries de diagnóstico para explicar, no para corregir.

---

## 10. Conclusión

`PAID_WITHOUT_ACHIEVEMENT` es un **estado válido** que refleja que Yango (upstream) reconoció un pago según sus criterios, sin que exista evidencia suficiente en nuestro sistema operativo para confirmar el milestone.

**No es un bug, es comportamiento esperado.**

Las vistas de reconciliación (`ops.v_cabinet_milestones_reconciled`) y los queries de diagnóstico (FASE 2) proporcionan toda la evidencia necesaria para auditar y explicar estos casos sin necesidad de modificar datos históricos.

**Política oficial:** Aceptar UPSTREAM_OVERPAYMENT e INSUFFICIENT_TRIPS_CONFIRMED como estados finales válidos, documentarlos, y usar queries de diagnóstico para auditoría.

---

**Fin del documento**

