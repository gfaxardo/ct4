# Mapeo Claro de Granos: Vistas Yango Cabinet

## Propósito

Este documento explica claramente el grano (grain) de cada vista clave en el sistema de pagos Yango Cabinet, cómo se relacionan entre sí, y cuáles son las claves reales (no asumir nombres genéricos como `claim_id`).

## 1. Grano de `ops.v_yango_receivable_payable_detail`

### Clave Única
**`(driver_id, milestone_value, lead_date)`**

**Nota importante:** Puede haber múltiples filas por `(driver_id, milestone_value)` si hay múltiples `lead_date` diferentes. Esto ocurre cuando un mismo driver alcanza el mismo milestone en diferentes fechas.

### Propósito
Lista todos los receivables elegibles (expected payments) que Yango debe pagar a YEGO por leads cabinet.

### Filtros Aplicados
- `is_payable = true`
- `amount > 0`
- `lead_origin = 'cabinet'`
- `milestone_value IN (1, 5, 25)`

### Campos Clave
- `pay_week_start_monday`: Semana de pago (lunes de la semana)
- `pay_iso_year_week`: Semana ISO (formato IYYY-IW)
- `payable_date`: Fecha en que el pago es exigible
- `achieved_date`: Fecha en que se alcanzó el milestone
- `lead_date`: Fecha en que el conductor entró por cabinet
- `driver_id`: ID del conductor
- `person_key`: Person key del conductor
- `milestone_value`: Valor del milestone (1, 5, o 25)
- `amount`: Monto esperado (calculado según milestone: 1=25, 5=35, 25=100)
- `currency`: Moneda (generalmente 'PEN')

### Ejemplo de Múltiples Filas
Un mismo driver puede tener:
- `(driver_id='123', milestone_value=1, lead_date='2024-01-15')` → expected_amount = 25
- `(driver_id='123', milestone_value=1, lead_date='2024-02-20')` → expected_amount = 25

Esto significa que el driver alcanzó el milestone 1 en dos ocasiones diferentes.

### Fuente de Datos
Esta vista se basa en `ops.v_partner_payments_report_ui` filtrada por `lead_origin = 'cabinet'`.

---

## 2. Grano de `ops.mv_yango_cabinet_claims_for_collection`

### Clave Única
**`(driver_id, milestone_value)`**

**Nota importante:** Esta vista está **deduplicada**. Solo hay 1 fila por `(driver_id, milestone_value)`, independientemente de cuántos `lead_date` diferentes existan en `v_yango_receivable_payable_detail`.

### Propósito
Estado de pago de cada claim (PAID/UNPAID/PAID_MISAPPLIED) para gestión de cobranza.

### Deduplicación
La deduplicación se realiza en `ops.v_claims_payment_status_cabinet` usando `DISTINCT ON (driver_id, milestone_value)` quedándose con el `lead_date` más reciente.

### Campos Clave
- `driver_id`: ID del conductor (NOT NULL, requisito para claims)
- `person_key`: Person key del conductor
- `milestone_value`: Valor del milestone (1, 5, o 25)
- `lead_date`: Fecha del lead más reciente (después de deduplicación)
- `expected_amount`: Monto esperado según milestone (1=25, 5=35, 25=100)
- `yango_payment_status`: Estado de pago canónico:
  - `'PAID'`: Pago encontrado en milestone correcto
  - `'PAID_MISAPPLIED'`: Pago encontrado pero en otro milestone (`reason_code = 'payment_found_other_milestone'`)
  - `'UNPAID'`: No se encontró pago
- `payment_key`: Identificador único del pago (si existe)
- `pay_date`: Fecha del pago (si existe)
- `reason_code`: Código de razón detallado:
  - `'paid'`: Pagado correctamente
  - `'payment_found_other_milestone'`: Pago encontrado en otro milestone
  - `'payment_found_person_key_only'`: Pago encontrado solo por person_key
  - `'no_payment_found'`: No se encontró pago
- `identity_status`: Estado de identidad (`'confirmed'`, `'enriched'`, `'ambiguous'`, `'no_match'`)
- `match_rule`: Regla de matching (`'source_upstream'`, `'name_unique'`, `'ambiguous'`, `'no_match'`)
- `match_confidence`: Confianza del matching (`'high'`, `'medium'`, `'low'`)
- `is_reconcilable_enriched`: Flag indicando si el claim es reconciliable usando identidad enriquecida

### Fuente de Datos
Esta vista materializada se basa en `ops.v_claims_payment_status_cabinet` con campos adicionales derivados.

---

## 3. Relación entre Vistas

### Flujo de Datos

```
ops.v_yango_receivable_payable_detail (expected payments)
    ↓
    [Deduplicación por (driver_id, milestone_value)]
    ↓
ops.v_claims_payment_status_cabinet (estado de pago base)
    ↓
    [Enriquecimiento con identidad y matching]
    ↓
ops.mv_yango_cabinet_claims_for_collection (estado final)
```

### Matching con Pagos Reales

```
ops.v_yango_payments_ledger_latest_enriched (pagos reales recibidos)
    ↓
    [Matching por driver_id_final + milestone_value]
    ↓
ops.mv_yango_cabinet_claims_for_collection (claims con estado de pago)
```

### Vistas de Resumen

```
ops.mv_yango_cabinet_claims_for_collection
    ↓
    [Filtro: yango_payment_status = 'UNPAID']
    ↓
ops.v_yango_cabinet_claims_exigimos (claims para cobrar)

ops.mv_yango_cabinet_claims_for_collection
    ↓
    [Agregación por milestone y estado]
    ↓
ops.v_yango_cabinet_claims_exec_summary (resumen ejecutivo)
```

---

## 4. Identificación de Claves Reales

### ⚠️ No Usar Nombres Genéricos

**NO existe:**
- `claim_id` (identificador único de claim)
- `payment_id` (identificador único de pago)

### Claves Canónicas

#### Clave Canónica de Claim
**`(driver_id, milestone_value)`**

Esta es la clave única que identifica un claim. Un claim representa: "El conductor `driver_id` alcanzó el milestone `milestone_value` y Yango debe pagar el monto correspondiente."

**Ejemplo:**
- `(driver_id='123', milestone_value=1)` → Claim: Driver 123 alcanzó milestone 1, Yango debe pagar S/25
- `(driver_id='123', milestone_value=5)` → Claim: Driver 123 alcanzó milestone 5, Yango debe pagar S/35 adicionales

#### Identificador Único de Pago
**`payment_key`**

Este es el identificador único de un pago en el ledger. Se calcula como:
```
md5(source_pk || milestone_value || driver_name_normalized)
```

**Nota:** Un mismo `payment_key` puede estar asociado a múltiples claims si:
- El mismo pago se usa para diferentes milestones (caso PAID_MISAPPLIED)
- El mismo pago se asocia a diferentes drivers (error de matching)

#### Clave de Reconciliación
**`(driver_id_final, milestone_value)`** o **`(person_key_final, milestone_value)`**

Estas son las claves usadas para hacer matching entre:
- Claims esperados (`ops.mv_yango_cabinet_claims_for_collection`)
- Pagos reales (`ops.v_yango_payments_ledger_latest_enriched`)

**Prioridad de matching:**
1. Primero intenta por `driver_id_final + milestone_value` (más confiable)
2. Si no hay match, intenta por `person_key_final + milestone_value` (menos confiable)

---

## 5. Ejemplos Prácticos

### Ejemplo 1: Claim Simple (UNPAID)

**En `v_yango_receivable_payable_detail`:**
```
driver_id='123', milestone_value=1, lead_date='2024-01-15', amount=25
```

**En `mv_yango_cabinet_claims_for_collection`:**
```
driver_id='123', milestone_value=1, lead_date='2024-01-15', expected_amount=25, yango_payment_status='UNPAID', reason_code='no_payment_found'
```

**Interpretación:** El driver 123 alcanzó el milestone 1 el 15 de enero, pero no se encontró pago. Yango debe pagar S/25.

### Ejemplo 2: Claim con Pago Correcto (PAID)

**En `v_yango_receivable_payable_detail`:**
```
driver_id='456', milestone_value=5, lead_date='2024-02-10', amount=35
```

**En `v_yango_payments_ledger_latest_enriched`:**
```
payment_key='abc123', driver_id_final='456', milestone_value=5, is_paid=true, pay_date='2024-02-12'
```

**En `mv_yango_cabinet_claims_for_collection`:**
```
driver_id='456', milestone_value=5, lead_date='2024-02-10', expected_amount=35, yango_payment_status='PAID', payment_key='abc123', reason_code='paid'
```

**Interpretación:** El driver 456 alcanzó el milestone 5 el 10 de febrero, y se encontró un pago correcto el 12 de febrero. Claim pagado correctamente.

### Ejemplo 3: Claim con Pago Mal Aplicado (PAID_MISAPPLIED)

**En `v_yango_receivable_payable_detail`:**
```
driver_id='789', milestone_value=25, lead_date='2024-03-01', amount=100
```

**En `v_yango_payments_ledger_latest_enriched`:**
```
payment_key='xyz789', driver_id_final='789', milestone_value=5, is_paid=true, pay_date='2024-03-05'
```

**En `mv_yango_cabinet_claims_for_collection`:**
```
driver_id='789', milestone_value=25, lead_date='2024-03-01', expected_amount=100, yango_payment_status='PAID_MISAPPLIED', payment_key='xyz789', reason_code='payment_found_other_milestone'
```

**Interpretación:** El driver 789 alcanzó el milestone 25 el 1 de marzo, pero se encontró un pago para el milestone 5 (no para el 25). El pago está mal aplicado. Yango debe pagar S/100 adicionales.

---

## 6. Resumen de Granos

| Vista | Clave Única | Propósito | Deduplicación |
|-------|-------------|-----------|---------------|
| `v_yango_receivable_payable_detail` | `(driver_id, milestone_value, lead_date)` | Lista todos los receivables elegibles | No (puede haber múltiples filas por driver+milestone) |
| `mv_yango_cabinet_claims_for_collection` | `(driver_id, milestone_value)` | Estado de pago de cada claim | Sí (1 fila por claim) |
| `v_yango_payments_ledger_latest_enriched` | `payment_key` | Pagos reales recibidos | Sí (1 fila por payment_key) |
| `v_yango_cabinet_claims_exigimos` | `(driver_id, milestone_value)` | Claims NO pagados (UNPAID) | Sí (filtrado desde mv) |
| `v_yango_cabinet_claims_exec_summary` | `(section, category)` | Resumen ejecutivo agregado | Sí (agregación) |

---

## 7. Notas Importantes

1. **No existe `claim_id`:** Usar `(driver_id, milestone_value)` como clave canónica.

2. **Deduplicación:** `mv_yango_cabinet_claims_for_collection` está deduplicada, pero `v_yango_receivable_payable_detail` no lo está.

3. **Múltiples lead_date:** Un mismo driver puede alcanzar el mismo milestone en diferentes fechas. La deduplicación se queda con el `lead_date` más reciente.

4. **Payment_key puede repetirse:** Un mismo `payment_key` puede estar asociado a múltiples claims si hay errores de matching o si el pago se aplica incorrectamente.

5. **Matching por identidad:** El matching entre claims y pagos se hace por `driver_id_final` (preferido) o `person_key_final` (fallback).

---

## 8. Validación

Para validar que el mapeo de granos es correcto:

```sql
-- Verificar que mv_yango_cabinet_claims_for_collection tiene 1 fila por (driver_id, milestone_value)
SELECT 
    driver_id, 
    milestone_value, 
    COUNT(*) AS count_rows
FROM ops.mv_yango_cabinet_claims_for_collection
GROUP BY driver_id, milestone_value
HAVING COUNT(*) > 1;
-- Debe retornar 0 filas

-- Verificar que v_yango_receivable_payable_detail puede tener múltiples filas por (driver_id, milestone_value)
SELECT 
    driver_id, 
    milestone_value, 
    COUNT(*) AS count_rows
FROM ops.v_yango_receivable_payable_detail
GROUP BY driver_id, milestone_value
HAVING COUNT(*) > 1;
-- Puede retornar filas (esto es esperado)
```










