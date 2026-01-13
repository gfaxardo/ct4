# Enriquecimiento de Identidad - Yango Payments

## Resumen

Este documento explica el sistema de enriquecimiento de identidad para pagos Yango, que permite identificar conductores cuando la fuente upstream no proporciona `driver_id` o `person_key`.

## Arquitectura

### Fuentes de Identidad

1. **Upstream (Original)**
   - `driver_id` y/o `person_key` provienen directamente de `public.module_ct_cabinet_payments`
   - **Confianza**: `high`
   - **Estado**: `confirmed`
   - **Uso contable**: ✅ SÍ cuenta como pago real

2. **Enriquecido por Nombre (Fallback)**
   - Matching determinístico por nombre contra `public.drivers`
   - **Confianza**: `medium`
   - **Estado**: `enriched`
   - **Uso contable**: ⚠️ Informativo, requiere confirmación

3. **Sin Identidad**
   - `ambiguous`: Múltiples matches posibles
   - `no_match`: No se encontró match
   - **Confianza**: `low`
   - **Estado**: `ambiguous` o `no_match`
   - **Uso contable**: ❌ NO contable hasta resolver

## Matching por Nombre (Determinístico)

### Funciones de Normalización

1. **`ops.normalize_name_basic(text)`**
   - Convierte a mayúsculas
   - Quita tildes (á → A, é → E, etc.)
   - Remueve puntuación y caracteres especiales
   - Colapsa espacios múltiples
   - Ejemplo: "María José" → "MARIA JOSE"

2. **`ops.normalize_name_tokens_sorted(text)`**
   - Aplica normalización básica
   - Tokeniza por espacios
   - Remueve stopwords: 'de', 'del', 'la', 'los', 'y'
   - Ordena tokens alfabéticamente
   - Reúne con espacios
   - Ejemplo: "García López, Juan" → "GARCIA JUAN LOPEZ"

### Reglas de Seguridad

- **Match único requerido**: Solo se asigna identidad si `count = 1` para la llave normalizada
- **Prioridad**:
  1. Match por nombre completo normalizado (si único)
  2. Match por tokens ordenados (si único)
  3. Si ambos métodos matchean a drivers distintos → `ambiguous` (no se asigna)
  4. Si count > 1 en cualquier método → `ambiguous` (no se asigna)
  5. Si no hay match → `no_match`

### Match Rules

- `source_upstream`: Identidad desde upstream (original)
- `name_full_unique`: Match único por nombre completo normalizado
- `name_tokens_unique`: Match único por tokens ordenados
- `ambiguous`: Múltiples matches o conflictos
- `no_match`: Sin match encontrado

### Match Confidence

- `high`: Identidad desde upstream
- `medium`: Match único por nombre (enriched)
- `low`: Ambiguous o no_match

## Vista SQL: `ops.v_yango_payments_ledger_latest_enriched`

Enriquece `ops.v_yango_payments_ledger_latest` con identidad usando matching por nombre.

### Campos Expuestos

- `driver_id_original`: Driver ID desde ledger (puede ser NULL)
- `driver_id_enriched`: Driver ID derivado por matching (solo si único)
- `driver_id_final`: `COALESCE(original, enriched)`
- `identity_status`: `'confirmed'` | `'enriched'` | `'ambiguous'` | `'no_match'`
- `match_rule`: `'source_upstream'` | `'name_full_unique'` | `'name_tokens_unique'` | `'ambiguous'` | `'no_match'`
- `match_confidence`: `'high'` | `'medium'` | `'low'`
- `identity_enriched`: `boolean` (TRUE si fue enriquecido)

## Vista SQL: `ops.v_yango_payments_claims_cabinet_14d`

Vista de claims que separa `paid_confirmed` vs `paid_enriched`.

### Paid Status

- `paid_confirmed`: Pago con `identity_status='confirmed'` (upstream)
- `paid_enriched`: Pago con `identity_status='enriched'` (match por nombre)
- `pending_active`: No pagado, dentro de ventana (14 días)
- `pending_expired`: No pagado, fuera de ventana (reclamo)

### Campos Clave

- `paid_payment_key_confirmed`: Payment key del pago confirmado
- `paid_payment_key_enriched`: Payment key del pago enriquecido
- `is_paid_confirmed`: Boolean
- `is_paid_enriched`: Boolean
- `is_paid_effective`: Solo `paid_confirmed` cuenta como "paid real" para contabilidad

## Backend API

### Endpoint: `/api/v1/yango/payments/reconciliation/summary`

Expone:
- `amount_paid_confirmed_sum`: Suma de pagos confirmados
- `amount_paid_enriched_sum`: Suma de pagos enriquecidos
- `amount_paid_total_visible`: `confirmed + enriched`
- `_validation.ledger_is_paid_true_confirmed`: Count de pagos confirmados
- `_validation.ledger_is_paid_true_enriched`: Count de pagos enriquecidos
- `_validation.ledger_is_paid_true_ambiguous`: Count de pagos ambiguous
- `_validation.ledger_is_paid_true_no_match`: Count de pagos sin match

### Endpoint: `/api/v1/yango/payments/reconciliation/items`

Expone campos de identity enrichment:
- `identity_status`: `'confirmed'` | `'enriched'` | `'ambiguous'` | `'no_match'`
- `match_rule`: Regla de matching usada
- `match_confidence`: `'high'` | `'medium'` | `'low'`
- `paid_status`: `'paid_confirmed'` | `'paid_enriched'` | `'pending_active'` | `'pending_expired'`

## Frontend

### Dashboard Cards

1. **Paid Confirmado**
   - Monto: `amount_paid_confirmed_sum`
   - Color: Verde
   - Tooltip: "Pagos con identidad confirmada desde upstream (driver_id/person_key original). Fuente de verdad para pagos reales contables."

2. **Paid Enriquecido (Probable)**
   - Monto: `amount_paid_enriched_sum`
   - Color: Amarillo
   - Badge: "Probable"
   - Tooltip: "Pagos con identidad enriquecida por matching determinístico por nombre (match único). Informativo pero requiere confirmación para contabilidad definitiva."

3. **Paid Sin Identidad**
   - Monto: `ledger_is_paid_true - confirmed - enriched`
   - Color: Púrpura
   - Tooltip: "Pagos pagados en ledger pero sin identidad atribuible (ambiguous/no_match). No contable hasta resolver identidad."

### Tablas / Modales

- Columnas mostradas: `identity_status`, `match_rule`, `match_confidence`
- Badges con estilos distintos según `identity_status`
- Filtros disponibles: "Solo enriched", "Solo ambiguous", "Solo no_match"

## Validación SQL

### Scripts de Validación

1. **`backend/sql/ops/validation_ledger_identity.sql`**
   - Distribución de `identity_status` y `match_rule`
   - Count de `is_paid=true` por `identity_status`
   - Muestras de casos `ambiguous` y `no_match`

2. **`backend/sql/ops/validation_paid_reconciliation.sql`**
   - Totales: Expected vs Paid Confirmed vs Paid Enriched
   - Breakdown por semana
   - Comparación: Confirmed vs Enriched

## Interpretación

### ¿Por qué `enriched` no es contable definitivo?

El matching por nombre es determinístico pero no garantiza 100% de precisión:
- Variaciones en nombres (múltiples personas con mismo nombre)
- Errores tipográficos en nombres
- Nombres incompletos

Por lo tanto, `enriched` es **informativo** y debe ser revisado antes de ser contabilizado definitivamente.

### ¿Qué hacer con `ambiguous`?

Casos `ambiguous` requieren intervención manual:
- Revisar el nombre en el ledger
- Verificar contra múltiples candidatos
- Decidir manualmente o solicitar información adicional

### ¿Qué hacer con `no_match`?

Casos `no_match` pueden indicar:
- Nombre no existe en `public.drivers`
- Nombre está muy mal escrito
- Driver no está registrado en el sistema

Requieren investigación y posiblemente corrección en upstream.

## Próximos Pasos

1. **Fix Upstream** (PRIORITARIO)
   - Agregar `driver_id` y/o `person_key` a `public.module_ct_cabinet_payments`
   - Poblarlos en el punto de inserción/ingesta
   - Esto reduce la necesidad de fallback por nombre

2. **Monitoreo**
   - Revisar regularmente casos `enriched` para validar precisión
   - Reducir casos `ambiguous` mediante limpieza de datos
   - Reducir casos `no_match` mediante mejoras en normalización

3. **Auditoría**
   - Mantener logs de decisiones de matching
   - Revisar casos donde `enriched` se convierte en `confirmed`
   - Documentar excepciones y casos especiales









