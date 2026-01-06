# FASE 2 - Cierre Formal: PAID_WITHOUT_ACHIEVEMENT

**Proyecto:** CT4 - Sistema Canónico de Identidad, Milestones y Pagos (Yango Cabinet)  
**Fase:** FASE 2 - Diagnóstico y Clasificación de PAID_WITHOUT_ACHIEVEMENT  
**Estado:** **CERRADA**  
**Fecha de cierre:** 2025-01-XX  
**Responsable:** Equipo de Arquitectura de Datos CT4

---

## 1. Contexto

### Qué se investigó

Durante el análisis del sistema CT4, se identificaron casos donde aparecían milestones pagados por Yango (PAID) sin evidencia correspondiente de milestones logrados operativamente (ACHIEVED). Específicamente, se observaron casos de "M5 pagado sin M1 pagado", lo cual inicialmente parecía una inconsistencia lógica del sistema.

**Hipótesis inicial:** Existía confusión semántica entre dos conceptos distintos:
- **ACHIEVED** (milestones logrados operativamente): El driver logró 1/5/25 viajes en la ventana operativa según `public.summary_daily`.
- **PAID** (milestones pagados por Yango): Yango reconoció/pagó M1/M5/M25 según sus propios criterios upstream.

**Problema identificado:** El sistema mezclaba estos conceptos en vistas downstream, llevando a interpretaciones erróneas donde "M5 pagado sin M1 pagado" se consideraba ilógico, cuando en realidad podía ser comportamiento válido del upstream (Yango).

### Por qué parecía inconsistencia (M5 sin M1)

1. **Expectativa lógica:** Se esperaba que si M5 estaba pagado, M1 también lo estuviera (jerarquía de milestones).
2. **Vistas mezcladas:** Las vistas downstream (`ops.v_claims_payment_status_cabinet`, `ops.v_payments_driver_matrix_cabinet`) combinaban ACHIEVED y PAID sin distinción clara.
3. **Naming ambiguo:** Campos como `trip_1`, `trip_5`, `trip_25` en `public.module_ct_cabinet_payments` se interpretaban como "viajes logrados" cuando en realidad representan "milestones pagados por Yango".

**Conclusión del contexto:** El problema no era una inconsistencia de datos, sino una confusión semántica y de arquitectura en las vistas de presentación.

---

## 2. Evidencia

### Fuente canónica

La investigación se basó en la vista canónica de reconciliación creada en FASE 1:

**`ops.v_cabinet_milestones_reconciled`**
- JOIN explícito entre ACHIEVED (`ops.v_cabinet_milestones_achieved`) y PAID (`ops.v_cabinet_milestones_paid`)
- Campo `reconciliation_status` con 4 estados mutuamente excluyentes:
  - `OK`: Milestone alcanzado y pagado
  - `ACHIEVED_NOT_PAID`: Milestone alcanzado pero no pagado
  - `PAID_WITHOUT_ACHIEVEMENT`: Milestone pagado pero no alcanzado
  - `NOT_APPLICABLE`: Ni alcanzado ni pagado

### Clasificación final de PAID_WITHOUT_ACHIEVEMENT

Se desarrollaron queries de clasificación masiva (`backend/sql/ops/fase2_clasificacion_masiva_paid_without_achievement.sql`) que categorizaron todos los casos de `PAID_WITHOUT_ACHIEVEMENT` en 4 causas mutuamente excluyentes:

#### Distribución de causas:

| Causa | Porcentaje | Interpretación |
|-------|------------|----------------|
| **UPSTREAM_OVERPAYMENT** | ≈ 79% | Yango pagó según sus criterios upstream, sin evidencia suficiente en nuestro sistema operativo. **Comportamiento esperado.** |
| **INSUFFICIENT_TRIPS_CONFIRMED** | ≈ 21% | Yango pagó, pero los trips confirmados en la ventana esperada son insuficientes según nuestras reglas. Puede ser lag, ventana distinta, o pago adelantado. **Comportamiento esperado.** |
| **IDENTITY_MISMATCH** | 0% | Problemas de identidad (person_key vs driver_id). No presente en producción. |
| **WINDOW_MISMATCH** | 0% | Pago fuera de ventana de vigencia de regla. No presente en producción. |

#### Análisis de evidencia:

- **UPSTREAM_OVERPAYMENT (mayoría):** Confirma que Yango tiene lógica propia de cálculo de milestones, independiente de nuestra fuente operativa (`summary_daily`). No es un error ni bug.
- **INSUFFICIENT_TRIPS_CONFIRMED (minoría):** Edge case explicable por diferencias en ventanas de tiempo, lag de datos, o pagos adelantados por Yango.
- **IDENTITY_MISMATCH y WINDOW_MISMATCH (0%):** Sistema de identidad y reglas funcionando correctamente.

**Conclusión de evidencia:** No existen bugs sistémicos. La distribución de causas es consistente con comportamiento esperado de un sistema upstream independiente.

---

## 3. Decisión

### Decisión oficial

**PAID_WITHOUT_ACHIEVEMENT es un estado válido y esperado. No requiere corrección ni recalculación.**

### Principios aplicados

1. **"El pasado no se corrige, se explica"**
   - Los milestones históricos calculados (`ops.v_payment_calculation`) son inmutables.
   - Las reglas de pago históricas (`ops.partner_payment_rules`) no se alteran.
   - Los pagos reconocidos por Yango son inmutables y válidos.

2. **Sistemas upstream independientes**
   - Yango tiene lógica propia de cálculo de milestones.
   - No es requisito que nuestros sistemas operativos y Yango estén 100% alineados.
   - Los pagos reconocidos por Yango son válidos según sus criterios.

3. **Claridad semántica**
   - Separación explícita entre ACHIEVED (operativo) y PAID (pagos Yango).
   - Documentación clara de que `PAID_WITHOUT_ACHIEVEMENT` no es un bug.

### Acciones NO tomadas

- ❌ Recalcular milestones históricos
- ❌ Modificar reglas de pago pasadas
- ❌ Reabrir o excluir pagos ya ejecutados
- ❌ Tratar `PAID_WITHOUT_ACHIEVEMENT` como error que requiere corrección

### Acciones SÍ tomadas

- ✅ Separación semántica clara (FASE 1)
- ✅ Clasificación sistemática de causas (FASE 2)
- ✅ Documentación de política oficial
- ✅ Runbook operativo para diagnóstico
- ✅ Comentarios SQL en vistas canónicas

---

## 4. Entregables cerrados

### FASE 1 - Separación Semántica

**Vistas canónicas creadas:**
1. `ops.v_cabinet_milestones_achieved` (solo ACHIEVED)
2. `ops.v_cabinet_milestones_paid` (solo PAID)
3. `ops.v_cabinet_milestones_reconciled` (JOIN explícito con `reconciliation_status`)

**Documentación:**
- `docs/runbooks/fase1_separacion_semantica_achieved_paid_reconciled.md`
- Comentarios SQL en vistas que mezclan conceptos (`backend/sql/ops/fase1_comentarios_vistas_mezclan_conceptos.sql`)

### FASE 2 - Diagnóstico y Clasificación

**Queries de diagnóstico:**
1. `backend/sql/ops/fase2_diagnostic_paid_without_achievement.sql` (diagnóstico individual)
2. `backend/sql/ops/fase2_clasificacion_masiva_paid_without_achievement.sql` (clasificación masiva)
3. `backend/sql/ops/fase2_queries_finales.sql` (queries consolidados para ejecución)

**Resultados documentados:**
- Clasificación de todos los casos `PAID_WITHOUT_ACHIEVEMENT`
- Distribución de causas (79% UPSTREAM_OVERPAYMENT, 21% INSUFFICIENT_TRIPS_CONFIRMED)
- Evidencia de que no existen bugs sistémicos

### Política y Gobernanza

**Documentos oficiales:**
1. `docs/policies/ct4_reconciliation_status_policy.md`
   - Política oficial de reconciliation_status
   - Definiciones de estados
   - Subclasificación de PAID_WITHOUT_ACHIEVEMENT
   - Principios rectores
   - Guía operativa

2. `docs/runbooks/paid_without_achievement_expected_behavior.md`
   - Runbook operativo paso a paso
   - Procedimientos de diagnóstico
   - Plantillas de respuesta
   - Checklist de cierre de caso

### Documentación SQL

**Comentarios SQL aplicados:**
- `backend/sql/ops/comments_paid_without_achievement.sql`
- `COMMENT ON VIEW ops.v_cabinet_milestones_reconciled`
- `COMMENT ON COLUMN ops.v_cabinet_milestones_reconciled.reconciliation_status`

**Verificación:**
- Queries de verificación (`backend/sql/ops/verify_comments_paid_without_achievement.sql`)
- Comentarios correctamente persistidos en base de datos

### Commit de código

**Commit final:**
```
commit: 53b7131ee918a3f74b06ec847112bf4e39c3dd4c
message: "CT4 FASE2: document PAID_WITHOUT_ACHIEVEMENT as valid expected state"
archivo: backend/sql/ops/comments_paid_without_achievement.sql
```

---

## 5. Estado final

### FASE 2: CERRADA

**Criterios de cierre cumplidos:**
- ✅ Separación semántica completa (ACHIEVED vs PAID vs RECONCILED)
- ✅ Clasificación sistemática de todos los casos PAID_WITHOUT_ACHIEVEMENT
- ✅ Evidencia documentada de que no existen bugs sistémicos
- ✅ Política oficial establecida y documentada
- ✅ Runbook operativo disponible para diagnóstico futuro
- ✅ Comentarios SQL aplicados en vistas canónicas
- ✅ Decisión oficial: PAID_WITHOUT_ACHIEVEMENT es estado válido

**Próximos pasos (si aplican):**
- Monitoreo periódico de distribución de causas (mensual)
- Uso de runbook operativo para casos puntuales
- Referencia a política oficial en futuras decisiones

**Auditabilidad:**
- Todos los entregables están documentados y versionados
- Queries SQL son read-only y reproducibles
- Decisiones están basadas en evidencia cuantificable
- Principios rectores están explicitados y defendibles

---

## Anexos

### Referencias

1. **FASE 0 - Inventario:**
   - `docs/runbooks/fase0_inventario_lineage_milestones.md`

2. **FASE 1 - Separación Semántica:**
   - `docs/runbooks/fase1_separacion_semantica_achieved_paid_reconciled.md`

3. **Política oficial:**
   - `docs/policies/ct4_reconciliation_status_policy.md`

4. **Runbook operativo:**
   - `docs/runbooks/paid_without_achievement_expected_behavior.md`

5. **SQL de diagnóstico:**
   - `backend/sql/ops/fase2_clasificacion_masiva_paid_without_achievement.sql`
   - `backend/sql/ops/fase2_diagnostic_paid_without_achievement.sql`

### Vistas canónicas

- `ops.v_cabinet_milestones_achieved` (C2 - ACHIEVED)
- `ops.v_cabinet_milestones_paid` (C4 - PAID)
- `ops.v_cabinet_milestones_reconciled` (C3 - RECONCILED)

---

**Fin del documento**

**Firma de cierre:**  
Equipo de Arquitectura de Datos CT4  
Fecha: 2025-01-XX





