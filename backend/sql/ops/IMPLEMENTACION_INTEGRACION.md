# Implementación: Integración Cobro Yango en Claims Cabinet

## Arquitectura

### Fuente Única de Verdad (Claim-Level)
- **Vista**: `ops.v_yango_cabinet_claims_for_collection`
- **Granularidad**: 1 fila por claim (driver_id + milestone_value + lead_date)
- **Campos clave**: yango_payment_status (PAID/UNPAID/PAID_MISAPPLIED), expected_amount, yango_due_date, days_overdue_yango, etc.

### Vista Agregada (Driver-Level)
- **Vista**: `ops.v_claims_cabinet_driver_rollup`
- **Granularidad**: 1 fila por driver_id + período
- **Derivada de**: `ops.v_yango_cabinet_claims_for_collection`
- **Garantía**: SUM(rollup) == SUM(claim-level)

## Mapeo de Campos

### Vista Rollup → Schema CabinetDriverRow

```sql
-- Rollup tiene:
expected_total_yango          → expected_total
paid_total_yango              → paid_total
unpaid_total_yango + misapplied_total_yango  → not_paid_total
status                        → payment_status_driver
priority                      → action_priority_driver
milestones_hit                → milestones_reached
milestones_paid               → milestones_paid
claims_total, claims_paid, claims_unpaid, claims_misapplied → counts
```

**Nota crítica**: `not_paid_total` en el schema actual incluye tanto UNPAID como PAID_MISAPPLIED porque ambos son "lo que Yango debe pagar".

## Cambios Requeridos

### 1. Backend
- ✅ Crear `ops.v_claims_cabinet_driver_rollup` (HECHO)
- ⏳ Actualizar endpoint `/payments/cabinet/drivers` para usar rollup
- ⏳ Actualizar endpoint `/payments/cabinet/driver/{driver_id}/timeline` para usar `ops.v_yango_cabinet_claims_for_collection`
- ✅ Endpoint `/payments/yango/cabinet/claims` (claim-level) ya existe
- ✅ Endpoint `/payments/yango/cabinet/claims.csv` ya existe

### 2. Frontend
- ⏳ Modificar `/pagos/claims/page.tsx` para agregar toggle "Driver" / "Cobranza Yango"
- ⏳ Modo Driver: usar endpoint `/payments/cabinet/drivers` (con rollup)
- ⏳ Modo Cobranza: usar endpoint `/payments/yango/cabinet/claims` (claim-level)
- ⏳ KPIs: calcular desde la misma fuente según el modo
- ⏳ Export CSV: desde modo cobranza
- ⏳ Drilldown: mejorar para mostrar payment_key, paid_date, reason_code desde claim-level

### 3. Validación
- ✅ Script de reconciliación creado (`validation_rollup_reconciliation.sql`)

## Orden de Ejecución

1. **Ejecutar vistas SQL en BD**:
   - `v_yango_cabinet_claims_for_collection.sql` (ya creada, necesita ejecutarse)
   - `v_claims_cabinet_driver_rollup.sql` (nueva, necesita ejecutarse)

2. **Actualizar endpoints backend**

3. **Actualizar frontend**

4. **Validar reconciliación**

## Notas Importantes

- Los KPIs deben calcularse desde la MISMA FUENTE en ambos modos
- Modo Driver: KPIs desde rollup (SUM de expected_total_yango, paid_total_yango, etc.)
- Modo Cobranza: KPIs desde claim-level (SUM de expected_amount por status)
- Reconciliación: rollup_total debe igualar claim_level_total







