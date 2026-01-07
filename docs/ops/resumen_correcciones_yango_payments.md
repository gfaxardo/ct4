# Resumen de Correcciones: Yango Payments y Cabinet Financial 14d

## Problemas Identificados y Resueltos

### 1. ✅ Health Check: `module_ct_cabinet_payments` no aparecía

**Problema:** `module_ct_cabinet_payments` estaba comentado en `v_data_health.sql` porque se asumía que tenía estructura diferente.

**Solución:** 
- Descomentado y corregido para usar columna `date` (no `pay_date`)
- Agregado a `v_data_sources_catalog` y `v_data_freshness_status`
- Ahora aparece en el health check del sistema

### 2. ✅ Ingesta de Pagos: 108 pagos insertados pero no se reflejaban

**Problema:** 
- Se insertaron 108 pagos nuevos (hasta 05/01/2026)
- 97 tienen `driver_id` (90%)
- 11 no tienen `driver_id` (10%)
- Los pagos no se reflejaban en `v_cabinet_financial_14d`

**Solución:**
- Modificado `v_cabinet_financial_14d` para incluir también drivers desde `v_claims_payment_status_cabinet` que tienen `lead_date` pero no están en `v_conversion_metrics`
- Esto asegura que todos los pagos con `driver_id` completo y `lead_date` en claims aparezcan en la vista

### 3. ⏳ Vista Materializada: `mv_cabinet_financial_14d` no existe

**Problema:** El endpoint intenta usar la vista materializada pero no existe, causando error 500.

**Solución Parcial:**
- Modificado el endpoint para verificar si la vista materializada existe antes de usarla
- Si no existe, usa la vista normal `v_cabinet_financial_14d`
- Script creado para crear la vista materializada de forma simple (sin índices primero)

### 4. ⏳ Health Checks: Errores de sintaxis en `v_health_checks.sql`

**Problema:** 
- `v_health_checks.sql` tiene errores de sintaxis con `string_agg` y `ORDER BY` con `DISTINCT`
- `v_health_global` depende de `v_health_checks` que no se puede crear

**Estado:** En proceso de corrección

## Cambios Implementados

### Archivos Modificados:

1. **`backend/sql/ops/v_data_health.sql`**
   - Descomentado `module_ct_cabinet_payments` en catálogo
   - Corregido para usar columna `date` en lugar de `pay_date`
   - Agregado a todas las CTEs y UNION ALL

2. **`backend/sql/ops/v_cabinet_financial_14d.sql`**
   - Agregado `claims_base` CTE para incluir drivers desde `v_claims_payment_status_cabinet`
   - Agregado `all_drivers_base` CTE que combina `conversion_base` y `claims_base`
   - Modificado `trips_14d` para usar `all_drivers_base` en lugar de solo `conversion_base`

3. **`backend/app/api/v1/ops.py`**
   - Agregado endpoint `POST /api/v1/ops/yango-payments/ingest` para ejecutar ingesta manualmente

4. **`backend/app/api/v1/ops_payments.py`**
   - Modificado para verificar si `mv_cabinet_financial_14d` existe antes de usarla
   - Si no existe, usa `v_cabinet_financial_14d` (vista normal)

### Scripts Creados:

1. **`backend/scripts/ingest_yango_payments.py`**
   - Script para ejecutar ingesta de pagos Yango
   - Puede ser programado en cron/task scheduler

2. **`backend/scripts/test_ingest_direct.py`**
   - Script de prueba que muestra registros pendientes antes de ejecutar
   - Muestra resultados detallados

3. **`backend/scripts/backfill_payments_identity.py`**
   - Script para ejecutar backfill de identidad en pagos sin `driver_id`
   - Requiere que la función `ops.backfill_ledger_identity()` exista

## Próximos Pasos

1. **Crear vista materializada `mv_cabinet_financial_14d`**
   - Ejecutar script `create_mv_cabinet_financial_simple.sql`
   - Luego agregar índices si es necesario

2. **Corregir errores de sintaxis en `v_health_checks.sql`**
   - Corregir uso de `string_agg` con `DISTINCT` y `ORDER BY`
   - Crear `v_health_checks` y luego `v_health_global`

3. **Ejecutar backfill de identidad para los 11 pagos sin `driver_id`**
   - Crear función `ops.backfill_ledger_identity()` si no existe
   - Ejecutar backfill para asignar `driver_id` a pagos pendientes

4. **Configurar automatización**
   - Programar `ingest_yango_payments.py` para ejecutarse periódicamente (cada hora recomendado)
   - Programar refresh de `mv_cabinet_financial_14d` diariamente

## Verificación

Para verificar que todo funciona:

1. **Health Check:**
   ```sql
   SELECT * FROM ops.v_data_health_status WHERE source_name = 'module_ct_cabinet_payments';
   ```

2. **Pagos insertados:**
   ```sql
   SELECT COUNT(*) FROM ops.yango_payment_status_ledger WHERE snapshot_at >= CURRENT_DATE;
   ```

3. **Vista Financial:**
   ```sql
   SELECT MAX(lead_date), COUNT(*) FROM ops.v_cabinet_financial_14d;
   ```

