# SQL Ops - Scripts de Operaciones

Este directorio contiene scripts SQL para operaciones del sistema CT4.

## Pagos Yango - Conciliación

### Setup Inicial

**IMPORTANTE**: Ejecutar `yango_reconciliation_fixes_v4.sql` una vez en la base de datos antes de usar el sistema de conciliación.

```sql
-- Ejecutar en PostgreSQL:
\i backend/sql/ops/yango_reconciliation_fixes_v4.sql
```

Este script:
- Crea el alias VIEW `ops.yango_payment_ledger` (compatibilidad legacy)
- Corrige `ops.v_yango_reconciliation_detail` para que `pay_week_start_monday` NUNCA sea NULL
- Crea las vistas UI-friendly: `ops.v_yango_reconciliation_summary_ui` y `ops.v_yango_reconciliation_items_ui`

### Ingest de Pagos

Después de ejecutar el script de fixes, ejecutar el ingest de pagos:

**Opción 1: Función SQL**
```sql
SELECT ops.ingest_yango_payments_snapshot();
```

**Opción 2: Endpoint API**
```bash
POST /api/v1/yango/payments/ingest_snapshot
```

### Vistas Disponibles

- `ops.v_yango_reconciliation_detail`: Vista detalle completa (expected vs paid)
- `ops.v_yango_reconciliation_summary_ui`: Resumen agregado semanal (para UI)
- `ops.v_yango_reconciliation_items_ui`: Items detallados limpios (para tabla frontend)

### Validación

Ver queries de validación comentadas al final de `yango_reconciliation_fixes_v4.sql`.

## Driver Matrix - Resumen por Conductor

### Vista: `ops.v_payments_driver_matrix_cabinet`

Vista de presentación que muestra 1 fila por driver con columnas para milestones M1/M5/M25 y estados Yango/window.

**Características:**
- Granularidad: 1 fila por `driver_id`
- Columnas por milestone: `achieved_flag`, `achieved_date`, `expected_amount_yango`, `yango_payment_status`, `window_status`, `overdue_days`
- No recalcula reglas: solo SELECT sobre vistas canónicas existentes

### API Endpoint

**GET** `/api/v1/ops/payments/driver-matrix`

Endpoint para consultar la matriz de drivers con paginación y filtros.

**Query Parameters:**
- `week_start_from` (date, opcional): Filtra por `week_start >= week_start_from` (inclusive)
- `week_start_to` (date, opcional): Filtra por `week_start <= week_start_to` (inclusive)
- `origin_tag` (string, opcional): Filtra por origen (`'cabinet'` o `'fleet_migration'`)
- `only_pending` (bool, default: `false`): Si `true`, solo drivers con al menos 1 milestone achieved cuyo `yango_payment_status != 'PAID'`
- `limit` (int, default: 200, max: 1000): Límite de resultados
- `offset` (int, default: 0): Offset para paginación
- `order` (string, default: `'week_start_desc'`): Ordenamiento. Valores permitidos:
  - `week_start_desc`: Ordenar por `week_start DESC`
  - `week_start_asc`: Ordenar por `week_start ASC`
  - `lead_date_desc`: Ordenar por `lead_date DESC`
  - `lead_date_asc`: Ordenar por `lead_date ASC`

**Respuesta JSON:**
```json
{
  "meta": {
    "limit": 200,
    "offset": 0,
    "returned": 50,
    "total": 150
  },
  "data": [
    {
      "driver_id": "...",
      "person_key": "...",
      "driver_name": "...",
      "lead_date": "2025-01-15",
      "week_start": "2025-01-13",
      "origin_tag": "cabinet",
      "connected_flag": true,
      "connected_date": "2025-01-10",
      "m1_achieved_flag": true,
      "m1_achieved_date": "2025-01-15",
      "m1_expected_amount_yango": 25.00,
      "m1_yango_payment_status": "PAID",
      "m1_window_status": "in_window",
      "m1_overdue_days": 0,
      ...
    }
  ]
}
```

**Ejemplos curl:**

Sin filtros:
```bash
curl -X GET "http://localhost:8000/api/v1/ops/payments/driver-matrix?limit=200&offset=0"
```

Con filtros:
```bash
curl -X GET "http://localhost:8000/api/v1/ops/payments/driver-matrix?week_start_from=2025-01-01&week_start_to=2025-12-31&origin_tag=cabinet&only_pending=true&limit=100&offset=0&order=week_start_desc"
```

Solo pendientes:
```bash
curl -X GET "http://localhost:8000/api/v1/ops/payments/driver-matrix?only_pending=true&limit=50&offset=0"
```

**Notas:**
- El endpoint es de solo lectura (presentation layer)
- No recalcula reglas de negocio
- Usa consultas parametrizadas para seguridad
- Maneja errores con HTTPException 500 y logging



























