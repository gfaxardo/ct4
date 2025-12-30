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













