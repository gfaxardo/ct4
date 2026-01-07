# API Usage - Cabinet Financial 14d

## Endpoint

```
GET /api/v1/ops/payments/cabinet-financial-14d
```

## Descripción

Obtiene la fuente de verdad financiera para CABINET (ventana de 14 días). Permite determinar con exactitud qué conductores generan pago de Yango y detectar deudas por milestones no pagados.

## Parámetros de Query

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `only_with_debt` | boolean | `false` | Si `true`, solo drivers con deuda pendiente (amount_due_yango > 0) |
| `min_debt` | float | `null` | Filtra por deuda mínima (amount_due_yango >= min_debt) |
| `reached_milestone` | string | `null` | Filtra por milestone alcanzado: `'m1'`, `'m5'`, `'m25'` |
| `limit` | int | `200` | Límite de resultados (máx 1000) |
| `offset` | int | `0` | Offset para paginación |
| `include_summary` | boolean | `true` | Incluir resumen ejecutivo en la respuesta |
| `use_materialized` | boolean | `true` | Usar vista materializada para mejor rendimiento |

## Respuesta

```json
{
  "meta": {
    "limit": 200,
    "offset": 0,
    "returned": 70,
    "total": 70
  },
  "summary": {
    "total_drivers": 518,
    "drivers_with_expected": 116,
    "drivers_with_debt": 70,
    "total_expected_yango": 9865.00,
    "total_paid_yango": 4140.00,
    "total_debt_yango": 5725.00,
    "collection_percentage": 41.97,
    "drivers_m1": 116,
    "drivers_m5": 45,
    "drivers_m25": 12
  },
  "data": [
    {
      "driver_id": "64a4a4c283fe4fe2a9070ec8351214b1",
      "lead_date": "2025-12-12",
      "connected_flag": true,
      "connected_date": "2025-12-13",
      "total_trips_14d": 40,
      "reached_m1_14d": true,
      "reached_m5_14d": true,
      "reached_m25_14d": true,
      "expected_amount_m1": 25.00,
      "expected_amount_m5": 35.00,
      "expected_amount_m25": 100.00,
      "expected_total_yango": 160.00,
      "claim_m1_exists": true,
      "claim_m1_paid": false,
      "claim_m5_exists": true,
      "claim_m5_paid": false,
      "claim_m25_exists": true,
      "claim_m25_paid": false,
      "paid_amount_m1": 0.00,
      "paid_amount_m5": 0.00,
      "paid_amount_m25": 0.00,
      "total_paid_yango": 0.00,
      "amount_due_yango": 160.00
    }
  ]
}
```

## Ejemplos de Uso

### 1. Obtener todos los drivers con deuda pendiente

```bash
curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d?only_with_debt=true&limit=100"
```

### 2. Obtener drivers con deuda mayor a S/ 100

```bash
curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d?only_with_debt=true&min_debt=100&limit=50"
```

### 3. Obtener solo drivers que alcanzaron M25

```bash
curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d?reached_milestone=m25&limit=50"
```

### 4. Obtener resumen ejecutivo sin datos

```bash
curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d?limit=0&include_summary=true"
```

### 5. Usar vista normal (no materializada) para datos en tiempo real

```bash
curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d?use_materialized=false&limit=50"
```

## Casos de Uso

### Reporte de Cobranza

```bash
# Top 10 drivers con mayor deuda
curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d?only_with_debt=true&limit=10" | jq '.data[] | {driver_id, amount_due_yango, expected_total_yango}'
```

### Análisis por Milestone

```bash
# Drivers que alcanzaron M5 pero no tienen claim
curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d?reached_milestone=m5&limit=100" | jq '.data[] | select(.claim_m5_exists == false)'
```

### Resumen Ejecutivo

```bash
# Solo resumen sin datos detallados
curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d?limit=0&include_summary=true" | jq '.summary'
```

## Notas

1. **Vista Materializada vs Vista Normal:**
   - `use_materialized=true` (default): Usa `ops.mv_cabinet_financial_14d` - mejor rendimiento, datos pueden estar desactualizados
   - `use_materialized=false`: Usa `ops.v_cabinet_financial_14d` - datos en tiempo real, puede ser más lento

2. **Paginación:**
   - Usar `limit` y `offset` para paginación
   - El campo `meta.total` indica el total de resultados disponibles

3. **Rendimiento:**
   - Para consultas frecuentes, usar `use_materialized=true`
   - Para datos críticos en tiempo real, usar `use_materialized=false`
   - La vista materializada debe refrescarse periódicamente (diariamente recomendado)

4. **Filtros:**
   - Los filtros se pueden combinar
   - `only_with_debt=true` es útil para reportes de cobranza
   - `reached_milestone` filtra por milestone alcanzado dentro de la ventana de 14 días


