# Preparación para UI: Vistas Yango Cabinet

## Propósito

Este documento evalúa si las vistas existentes son suficientes para el frontend, propone una vista final solo si es estrictamente necesario, documenta los endpoints necesarios y proporciona el mapeo de columnas SQL → UI.

---

## 1. Evaluación de Necesidad de Vista Final

### Vistas Existentes Disponibles

1. **`ops.v_yango_cabinet_claims_exec_summary`**
   - Resumen ejecutivo agregado (EXIGIMOS / REPORTAMOS)
   - Grano: `(section, category)`
   - Uso: Dashboard ejecutivo, resumen general

2. **`ops.mv_yango_cabinet_claims_for_collection`**
   - Estado de pago de cada claim (PAID/UNPAID/PAID_MISAPPLIED)
   - Grano: `(driver_id, milestone_value)`
   - Uso: Lista de claims para cobrar, filtros, búsqueda

3. **`ops.v_yango_cabinet_claims_exigimos`**
   - Claims NO pagados (UNPAID) filtrados
   - Grano: `(driver_id, milestone_value)`
   - Uso: Lista de claims para cobrar (ya filtrada)

4. **`ops.v_yango_cabinet_payments_reportamos`**
   - Pagos recibidos sin mapeo
   - Grano: `payment_key`
   - Uso: Reporte de pagos recibidos que no corresponden a claims

5. **`ops.v_yango_receivable_payable_detail`**
   - Detalle de receivables (expected payments)
   - Grano: `(driver_id, milestone_value, lead_date)`
   - Uso: Detalle de receivables (puede tener múltiples filas por claim)

6. **`ops.v_yango_payments_ledger_latest_enriched`**
   - Pagos reales recibidos con identidad enriquecida
   - Grano: `payment_key`
   - Uso: Detalle de pagos, matching con claims

7. **`ops.v_yango_reconciliation_detail`**
   - Reconciliación expected vs paid
   - Grano: `(driver_id, milestone_value)` o `(person_key, milestone_value)`
   - Uso: Vista de reconciliación, matching detallado

### Análisis de Complejidad de JOINs

**Escenario 1: Dashboard Ejecutivo**
- **Necesidad:** Resumen agregado
- **Vista existente:** `ops.v_yango_cabinet_claims_exec_summary`
- **Complejidad:** Baja (vista ya agregada)
- **Conclusión:** ✅ Vista existente es suficiente

**Escenario 2: Lista de Claims para Cobrar**
- **Necesidad:** Lista filtrada de claims UNPAID
- **Vista existente:** `ops.v_yango_cabinet_claims_exigimos`
- **Complejidad:** Baja (vista ya filtrada)
- **Conclusión:** ✅ Vista existente es suficiente

**Escenario 3: Detalle de un Claim (Drilldown)**
- **Necesidad:** Evidencia completa de un claim específico
- **Vistas necesarias:** 
  - `ops.mv_yango_cabinet_claims_for_collection` (claim base)
  - `ops.v_yango_payments_ledger_latest_enriched` (pagos)
  - `canon.identity_links` (lead cabinet)
  - `ops.v_yango_reconciliation_detail` (reconciliación)
- **Complejidad:** Media (requiere múltiples JOINs)
- **Conclusión:** ⚠️ Podría beneficiarse de una vista consolidada

**Escenario 4: Filtros y Búsqueda**
- **Necesidad:** Filtrar por estado, milestone, días vencidos, etc.
- **Vista existente:** `ops.mv_yango_cabinet_claims_for_collection`
- **Complejidad:** Baja (vista ya tiene todos los campos necesarios)
- **Conclusión:** ✅ Vista existente es suficiente

### Conclusión de Evaluación

**Las vistas existentes son SUFICIENTES para la mayoría de casos de uso.**

**Excepción:** El drilldown de un claim específico requiere múltiples JOINs. Sin embargo, esto puede manejarse en el backend con queries parametrizadas (ver `docs/ops/yango_cabinet_claims_drilldown.sql`).

**Recomendación:** **NO crear una vista final adicional** a menos que:
1. El frontend requiera consultas muy complejas que se repitan frecuentemente
2. El rendimiento de las queries de drilldown sea inaceptable
3. Se necesite pre-calcular campos derivados complejos

---

## 2. Propuesta de Vista Final (Solo si es Necesaria)

### Vista Propuesta: `ops.v_yango_cabinet_claims_ui_ready`

**Solo crear esta vista si se cumplen las condiciones anteriores.**

```sql
CREATE OR REPLACE VIEW ops.v_yango_cabinet_claims_ui_ready AS
SELECT 
    -- Campos base del claim
    c.driver_id,
    c.person_key,
    c.milestone_value,
    c.expected_amount,
    c.lead_date,
    c.yango_due_date,
    c.days_overdue_yango,
    c.overdue_bucket_yango,
    c.yango_payment_status,
    c.reason_code,
    c.identity_status,
    c.match_rule,
    c.match_confidence,
    c.is_reconcilable_enriched,
    c.payment_key,
    c.pay_date,
    
    -- Campos derivados para UI
    CASE 
        WHEN c.yango_payment_status = 'PAID' THEN 'success'
        WHEN c.yango_payment_status = 'PAID_MISAPPLIED' THEN 'warning'
        WHEN c.yango_payment_status = 'UNPAID' THEN 'error'
        ELSE 'info'
    END AS status_badge_color,
    
    CASE 
        WHEN c.days_overdue_yango = 0 THEN 'No vencido'
        WHEN c.days_overdue_yango BETWEEN 1 AND 7 THEN 'Vencido 1-7 días'
        WHEN c.days_overdue_yango BETWEEN 8 AND 14 THEN 'Vencido 8-14 días'
        WHEN c.days_overdue_yango BETWEEN 15 AND 30 THEN 'Vencido 15-30 días'
        ELSE 'Vencido más de 30 días'
    END AS overdue_label,
    
    -- Totales pre-calculados (para evitar agregaciones en frontend)
    COUNT(*) OVER (PARTITION BY c.yango_payment_status) AS total_by_status,
    SUM(c.expected_amount) OVER (PARTITION BY c.yango_payment_status) AS total_amount_by_status,
    COUNT(*) OVER (PARTITION BY c.milestone_value) AS total_by_milestone,
    SUM(c.expected_amount) OVER (PARTITION BY c.milestone_value) AS total_amount_by_milestone
    
FROM ops.mv_yango_cabinet_claims_for_collection c;
```

**Nota:** Esta vista es opcional y solo debe crearse si el frontend realmente la necesita.

---

## 3. Documentación de Endpoints Necesarios

### 3.1 GET /api/v1/pagos/yango/summary

**Propósito:** Resumen ejecutivo (EXIGIMOS / REPORTAMOS)

**Fuente de datos:** `ops.v_yango_cabinet_claims_exec_summary`

**Response:**
```json
{
  "exigimos": {
    "total_claims": 255,
    "total_amount": 10910.00,
    "by_milestone": [
      {
        "milestone_value": 1,
        "count_claims": 100,
        "amount": 2500.00
      },
      {
        "milestone_value": 5,
        "count_claims": 80,
        "amount": 2800.00
      },
      {
        "milestone_value": 25,
        "count_claims": 75,
        "amount": 7500.00
      }
    ]
  },
  "reportamos": {
    "total_claims": 59,
    "total_amount": 2030.00,
    "by_reason": [
      {
        "reason": "NO_IDENTITY",
        "count_claims": 20,
        "amount": 500.00
      },
      {
        "reason": "NOT_CABINET_DRIVER",
        "count_claims": 30,
        "amount": 1000.00
      },
      {
        "reason": "NO_CLAIM_EXISTS",
        "count_claims": 9,
        "amount": 530.00
      }
    ]
  }
}
```

**Query SQL:**
```sql
SELECT * FROM ops.v_yango_cabinet_claims_exec_summary
ORDER BY section, category;
```

---

### 3.2 GET /api/v1/yango/cabinet/claims-to-collect

**Propósito:** Lista de claims exigibles a Yango (EXIGIMOS - filtrada por UNPAID)

**Fuente de datos:** `ops.v_yango_cabinet_claims_exigimos`

**Query Parameters:**
- `limit` (int, default: 50, max: 200)
- `offset` (int, default: 0)
- `date_from` (date, optional): Filtra por fecha lead desde
- `date_to` (date, optional): Filtra por fecha lead hasta
- `milestone_value` (int, optional: 1, 5, 25)
- `search` (string, optional): Búsqueda en driver_name o driver_id

**Orden:** `days_overdue_yango DESC, expected_amount DESC`

**Response:**
```json
{
  "items": [
    {
      "driver_id": "123",
      "driver_name": "Juan Pérez",
      "milestone_value": 1,
      "expected_amount": 25.00,
      "lead_date": "2024-01-15",
      "yango_due_date": "2024-01-29",
      "days_overdue_yango": 45,
      "overdue_bucket_yango": "4_30_plus",
      "yango_payment_status": "UNPAID",
      "reason_code": "no_payment_found",
      "identity_status": "confirmed",
      "match_rule": "source_upstream",
      "match_confidence": "high",
      "is_reconcilable_enriched": true
    }
  ],
  "total": 255,
  "limit": 50,
  "offset": 0
}
```

**Query SQL:**
```sql
SELECT * FROM ops.v_yango_cabinet_claims_exigimos
WHERE 
  (:milestone_value IS NULL OR milestone_value = :milestone_value)
  AND (:overdue_bucket IS NULL OR overdue_bucket_yango = :overdue_bucket)
  AND (:is_reconcilable IS NULL OR is_reconcilable_enriched = :is_reconcilable)
  AND (:identity_status IS NULL OR identity_status = :identity_status)
ORDER BY 
  CASE WHEN :sort_by = 'days_overdue_yango' THEN days_overdue_yango END DESC,
  CASE WHEN :sort_by = 'expected_amount' THEN expected_amount END DESC,
  CASE WHEN :sort_by = 'driver_id' THEN driver_id END ASC
LIMIT :limit OFFSET :offset;
```

---

### 3.3 GET /api/v1/yango/cabinet/claims/{driver_id}/{milestone_value}/drilldown

**Propósito:** Drilldown de un claim específico (evidencia completa para defensa del cobro)

**Fuente de datos:** Múltiples vistas (ver `docs/ops/yango_cabinet_claims_drilldown.sql` QUERY 4.4)

**Path Parameters:**
- `driver_id` (string, required)
- `milestone_value` (int, required: 1, 5, 25)

**Query Parameters:**
- `lead_date` (date, optional): Fecha lead para desambiguar si hay múltiples claims

**Códigos de respuesta:**
- `200`: Drilldown exitoso
- `404`: Claim no encontrado
- `409`: Ambigüedad (múltiples claims para driver_id+milestone_value, requiere lead_date)

**Response:**
```json
{
  "claim": {
    "driver_id": "123",
    "milestone_value": 1,
    "expected_amount": 25.00,
    "yango_payment_status": "UNPAID",
    "reason_code": "no_payment_found",
    "lead_date": "2024-01-15",
    "yango_due_date": "2024-01-29",
    "days_overdue_yango": 45
  },
  "lead_cabinet": {
    "lead_id": "456",
    "lead_external_id": "EXT-123",
    "lead_created_at": "2024-01-15T10:00:00Z",
    "lead_phone": "+51987654321",
    "lead_name": "Juan Pérez"
  },
  "identity": {
    "person_key": "uuid-here",
    "primary_phone": "+51987654321",
    "primary_full_name": "Juan Pérez",
    "confidence_level": "HIGH"
  },
  "payments": [
    {
      "payment_key": "payment-key-123",
      "milestone_value": 5,
      "pay_date": "2024-02-10",
      "is_paid": true,
      "identity_status": "confirmed",
      "match_rule": "source_upstream"
    }
  ],
  "reconciliation": {
    "reconciliation_status": "pending",
    "expected_amount": 25.00,
    "paid_payment_key": null,
    "paid_date": null,
    "match_method": "none"
  }
}
```

**Query SQL:** Ver `docs/ops/yango_cabinet_claims_drilldown.sql` QUERY 4.4

---

### 3.4 GET /api/v1/yango/cabinet/claims/export

**Propósito:** Exportar lista de claims exigibles a CSV

**Fuente de datos:** `ops.v_yango_cabinet_claims_exigimos`

**Query Parameters:**
- `date_from` (date, optional): Filtra por fecha lead desde
- `date_to` (date, optional): Filtra por fecha lead hasta
- `milestone_value` (int, optional: 1, 5, 25)
- `search` (string, optional): Búsqueda en driver_name o driver_id

**Response:** CSV file (UTF-8 con BOM, compatible Excel)
- Content-Type: `text/csv; charset=utf-8-sig`
- Content-Disposition: `attachment; filename="yango_cabinet_claims_YYYYMMDD_HHMM.csv"`
- Hard cap: 200,000 filas máximo (error 413 si excede)
- CSV injection mitigation: celdas que empiezan con (=,+,-,@) se prefijan con '

**Query SQL:** Ver `docs/ops/yango_cabinet_claims_to_collect.sql` QUERY 3.2

**Ejemplo curl:**
```bash
curl -X GET "http://localhost:8000/api/v1/yango/cabinet/claims/export?milestone_value=1" \
  -H "Accept: text/csv" \
  -o yango_claims_export.csv
```

---

## 4. Mapeo de Columnas SQL → UI

### 4.1 Tabla de Claims para Cobrar

| Columna SQL | Label UI | Tipo de Dato | Formato | Notas |
|-------------|----------|--------------|---------|-------|
| `driver_id` | Driver ID | string | Texto | Identificador único del conductor |
| `driver_name` | Nombre Conductor | string | Texto | Nombre completo del conductor |
| `milestone_value` | Milestone | integer | Badge | Valores: 1, 5, 25 |
| `expected_amount` | Monto Exigible | decimal(12,2) | Moneda (S/) | Formato: S/ 25.00 |
| `lead_date` | Fecha Lead | date | Fecha | Formato: DD/MM/YYYY |
| `yango_due_date` | Fecha Vencimiento | date | Fecha | Formato: DD/MM/YYYY |
| `days_overdue_yango` | Días Vencidos | integer | Número | Color: rojo si > 0 |
| `overdue_bucket_yango` | Bucket Vencimiento | string | Badge | Valores: 0_not_due, 1_1_7, 2_8_14, 3_15_30, 4_30_plus |
| `yango_payment_status` | Estado Pago | string | Badge | Valores: PAID, UNPAID, PAID_MISAPPLIED |
| `reason_code` | Razón | string | Texto | Código de razón detallado |
| `identity_status` | Estado Identidad | string | Badge | Valores: confirmed, enriched, ambiguous, no_match |
| `match_rule` | Regla Matching | string | Texto | Regla de matching usada |
| `match_confidence` | Confianza Matching | string | Badge | Valores: high, medium, low |
| `is_reconcilable_enriched` | Reconciliable | boolean | Checkbox | TRUE/FALSE |
| `payment_key` | Payment Key | string | Texto | Identificador único del pago |
| `pay_date` | Fecha Pago | date | Fecha | Formato: DD/MM/YYYY (si existe) |

### 4.2 Resumen Ejecutivo

| Columna SQL | Label UI | Tipo de Dato | Formato | Notas |
|-------------|----------|--------------|---------|-------|
| `section` | Sección | string | Badge | Valores: EXIGIMOS, REPORTAMOS |
| `category` | Categoría | string | Texto | Para EXIGIMOS: milestone (1, 5, 25, TOTAL). Para REPORTAMOS: razón (NO_IDENTITY, NOT_CABINET_DRIVER, NO_CLAIM_EXISTS, TOTAL) |
| `count_claims` | Cantidad Claims | integer | Número | Conteo de claims |
| `amount` | Monto Total | decimal(12,2) | Moneda (S/) | Formato: S/ 10,910.00 |

### 4.3 Drilldown de Claim

| Columna SQL | Label UI | Tipo de Dato | Formato | Notas |
|-------------|----------|--------------|---------|-------|
| `driver_id` | Driver ID | string | Texto | Identificador único |
| `milestone_value` | Milestone | integer | Badge | Valores: 1, 5, 25 |
| `expected_amount` | Monto Esperado | decimal(12,2) | Moneda (S/) | Formato: S/ 25.00 |
| `yango_payment_status` | Estado Pago | string | Badge | Valores: PAID, UNPAID, PAID_MISAPPLIED |
| `reason_code` | Razón | string | Texto | Código de razón |
| `lead_date` | Fecha Lead | date | Fecha | Formato: DD/MM/YYYY |
| `yango_due_date` | Fecha Vencimiento | date | Fecha | Formato: DD/MM/YYYY |
| `days_overdue_yango` | Días Vencidos | integer | Número | Color: rojo si > 0 |
| `payment_key` | Payment Key | string | Texto | Identificador único del pago |
| `pay_date` | Fecha Pago | date | Fecha | Formato: DD/MM/YYYY (si existe) |
| `identity_status` | Estado Identidad | string | Badge | Valores: confirmed, enriched, ambiguous, no_match |
| `match_rule` | Regla Matching | string | Texto | Regla de matching |
| `match_confidence` | Confianza Matching | string | Badge | Valores: high, medium, low |

---

## 5. Recomendaciones Finales

### 5.1 Vistas Existentes Son Suficientes

**Conclusión:** Las vistas existentes son suficientes para la mayoría de casos de uso. No se recomienda crear una vista final adicional a menos que:

1. El rendimiento de las queries de drilldown sea inaceptable
2. El frontend requiera consultas muy complejas que se repitan frecuentemente
3. Se necesite pre-calcular campos derivados complejos

### 5.2 Endpoints Recomendados

1. **GET /api/v1/pagos/yango/summary** → Resumen ejecutivo
2. **GET /api/v1/pagos/yango/claims** → Lista de claims para cobrar
3. **GET /api/v1/pagos/yango/claims/{driver_id}/{milestone_value}** → Drilldown
4. **GET /api/v1/pagos/yango/claims/export** → Exportación a Excel/CSV

### 5.3 Mapeo de Columnas

Usar el mapeo proporcionado en la sección 4 para garantizar consistencia entre SQL y UI.

### 5.4 Validación

Todas las queries deben validarse contra `ops.v_yango_cabinet_claims_exec_summary` para garantizar coherencia de datos.

---

## 6. Próximos Pasos

1. **Implementar endpoints** según la documentación de la sección 3
2. **Validar queries** contra las vistas existentes
3. **Probar rendimiento** de queries de drilldown
4. **Evaluar necesidad** de vista final `ops.v_yango_cabinet_claims_ui_ready` después de implementar endpoints
5. **Crear componentes UI** según el mapeo de columnas de la sección 4

---

## 7. Notas Técnicas

- Todas las queries usan vistas existentes, sin recalcular lógica
- Los endpoints deben manejar errores de base de datos retornando `detail="database_error"`
- Los detalles técnicos deben loguearse en el backend, no exponerse al cliente
- Las queries de drilldown pueden ser costosas; considerar caching si es necesario

