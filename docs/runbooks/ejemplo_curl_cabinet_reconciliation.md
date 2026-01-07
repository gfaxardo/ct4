# Ejemplo curl: Endpoint Cabinet Reconciliation

## Endpoint

```
GET /api/v1/yango/payments/cabinet/reconciliation
```

## Ejemplos de uso

### 1. Obtener todos los registros (paginado)

```bash
curl -X GET "http://localhost:8000/api/v1/yango/payments/cabinet/reconciliation?limit=100&offset=0"
```

### 2. Filtrar por reconciliation_status

```bash
# Solo casos PAID_WITHOUT_ACHIEVEMENT
curl -X GET "http://localhost:8000/api/v1/yango/payments/cabinet/reconciliation?reconciliation_status=PAID_WITHOUT_ACHIEVEMENT&limit=100"

# Solo casos OK
curl -X GET "http://localhost:8000/api/v1/yango/payments/cabinet/reconciliation?reconciliation_status=OK&limit=100"

# Solo casos ACHIEVED_NOT_PAID
curl -X GET "http://localhost:8000/api/v1/yango/payments/cabinet/reconciliation?reconciliation_status=ACHIEVED_NOT_PAID&limit=100"
```

### 3. Filtrar por milestone_value

```bash
# Solo milestone M5
curl -X GET "http://localhost:8000/api/v1/yango/payments/cabinet/reconciliation?milestone_value=5&limit=100"

# Solo milestone M1
curl -X GET "http://localhost:8000/api/v1/yango/payments/cabinet/reconciliation?milestone_value=1&limit=100"
```

### 4. Filtrar por driver_id

```bash
curl -X GET "http://localhost:8000/api/v1/yango/payments/cabinet/reconciliation?driver_id=DRIVER_ID_AQUI&limit=100"
```

### 5. Filtrar por rango de fechas

```bash
# Filtro por fecha (pay_date si existe, si no achieved_date)
curl -X GET "http://localhost:8000/api/v1/yango/payments/cabinet/reconciliation?date_from=2025-01-01&date_to=2025-01-31&limit=100"
```

### 6. Combinación de filtros

```bash
# PAID_WITHOUT_ACHIEVEMENT en M5 entre fechas
curl -X GET "http://localhost:8000/api/v1/yango/payments/cabinet/reconciliation?reconciliation_status=PAID_WITHOUT_ACHIEVEMENT&milestone_value=5&date_from=2025-01-01&date_to=2025-01-31&limit=100&offset=0"
```

### 7. Con formato JSON (jq)

```bash
curl -X GET "http://localhost:8000/api/v1/yango/payments/cabinet/reconciliation?limit=10" | jq
```

## Respuesta esperada

```json
{
  "status": "ok",
  "count": 10,
  "total": 312,
  "filters": {
    "limit": 100,
    "offset": 0
  },
  "rows": [
    {
      "driver_id": "DRIVER_123",
      "milestone_value": 5,
      "achieved_flag": true,
      "achieved_person_key": "550e8400-e29b-41d4-a716-446655440000",
      "achieved_lead_date": "2025-01-01",
      "achieved_date": "2025-01-05",
      "achieved_trips_in_window": 5,
      "window_days": 30,
      "expected_amount": "35.00",
      "achieved_currency": "PEN",
      "rule_id": 1,
      "paid_flag": true,
      "paid_person_key": "550e8400-e29b-41d4-a716-446655440000",
      "pay_date": "2025-01-10",
      "payment_key": "PAYMENT_KEY_123",
      "identity_status": "confirmed",
      "match_rule": "source_upstream",
      "match_confidence": "high",
      "latest_snapshot_at": "2025-01-10T12:00:00",
      "reconciliation_status": "OK"
    }
  ]
}
```

## Notas

- **Criterio de filtrado por fechas:** Usa `COALESCE(pay_date, achieved_date)` - si `pay_date` existe, filtra por `pay_date`; si no, filtra por `achieved_date`.
- **Valores válidos de reconciliation_status:** `OK`, `ACHIEVED_NOT_PAID`, `PAID_WITHOUT_ACHIEVEMENT`, `NOT_APPLICABLE`
- **Valores válidos de milestone_value:** `1`, `5`, `25`
- **Paginación:** `limit` (default: 100, max: 10000), `offset` (default: 0)
- **READ-ONLY:** Solo SELECT, no modifica datos ni recalcula reglas







