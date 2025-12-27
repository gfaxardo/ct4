# Enriquecimiento de Identidad en Ledger Yango

Este documento explica el sistema de enriquecimiento de identidad implementado para el ledger de pagos Yango.

## Problema

El ledger de pagos Yango (`ops.v_yango_payments_ledger_latest`) tiene registros donde `driver_id` y `person_key` son NULL, lo que impide hacer matching con claims y reconciliar pagos correctamente. Esto resulta en `Total Paid = 0` en el dashboard aunque existen pagos marcados como `is_paid = true` en el ledger.

## Solución

Se creó una vista enriquecida `ops.v_yango_payments_ledger_latest_enriched` que deriva `driver_id` y `person_key` usando matching por nombre normalizado.

## Vista Enriquecida

### Archivo: `backend/sql/ops/v_yango_payments_ledger_latest_enriched.sql`

**Funcionamiento:**

1. **Base**: Toma `ops.v_yango_payments_ledger_latest` como fuente
2. **Enriquecimiento por nombre**: 
   - JOIN con `ops.v_driver_name_index` usando `driver_name_normalized`
   - Solo aplica el match si es único (`name_match_count = 1`)
   - Si hay múltiples matches, no asigna identidad (por seguridad)
3. **Preservación de originales**: 
   - Mantiene `driver_id_original` y `person_key_original` para auditoría
   - Expone `driver_id_enriched` y `person_key_enriched` para los nuevos matches
4. **Campos finales**:
   - `driver_id`: COALESCE(original, enriched)
   - `person_key`: COALESCE(original, enriched)
   - `match_rule`: Indica cómo se obtuvo la identidad
   - `match_confidence`: Nivel de confianza (high/medium/unknown)
   - `identity_enriched`: Flag que indica si la identidad fue enriquecida

### Reglas de Matching

- **driver_id_direct**: Driver ID vino originalmente en el ledger (alta confianza)
- **driver_name_unique**: Match por nombre normalizado único (confianza media)
- **none**: Sin match (confianza desconocida)

### Confianza

- **high**: Identidad original (driver_id_direct)
- **medium**: Match por nombre único (driver_name_unique)
- **unknown**: Sin match o match ambiguo

## Actualización de Claims View

La vista `ops.v_yango_payments_claims_cabinet_14d` ahora usa `ops.v_yango_payments_ledger_latest_enriched` en lugar de `ops.v_yango_payments_ledger_latest` para hacer matching.

**Cambios:**
- Todos los JOINs ahora usan `ledger_enriched` CTE
- Matching sigue siendo por `driver_id + milestone_value` o `person_key + milestone_value`
- Pero ahora puede usar identidad enriquecida

## Métricas de Validación

El endpoint `/api/v1/yango/payments/reconciliation/summary` ahora expone en `filters._validation`:

- `ledger_total_rows`: Total de registros en ledger
- `ledger_rows_is_paid_true`: Pagos marcados como pagados
- `ledger_rows_driver_id_null`: Registros sin driver_id
- `ledger_rows_person_key_null`: Registros sin person_key
- `ledger_rows_both_identity_null`: Registros sin identidad (ambos NULL)
- `ledger_rows_identity_enriched`: Registros enriquecidos
- `matched_paid_rows`: Claims con `paid_status='paid'`

## Validación

### Scripts SQL

1. **`validation_ledger_identity.sql`**: 
   - Compara ledger original vs enriquecido
   - Muestra distribución de match_rule/match_confidence
   - Lista registros enriquecidos
   - Identifica registros que siguen sin identidad

2. **`validation_paid_reconciliation.sql`**:
   - Valida distribución de paid_status en claims
   - Verifica matches por match_method
   - Compara ledger enriquecido vs claims pagados
   - Calcula totales financieros

### Queries de Validación Recomendadas

```sql
-- Verificar que la vista enriquecida tiene más identidades
SELECT 
    COUNT(*) FILTER (WHERE driver_id IS NOT NULL OR person_key IS NOT NULL) 
FROM ops.v_yango_payments_ledger_latest_enriched;

-- Ver cuántos pagos fueron enriquecidos
SELECT 
    COUNT(*) FILTER (WHERE identity_enriched = true AND is_paid = true)
FROM ops.v_yango_payments_ledger_latest_enriched;

-- Verificar que claims tienen paid_status='paid' después del enriquecimiento
SELECT 
    COUNT(*) FILTER (WHERE paid_status = 'paid')
FROM ops.v_yango_payments_claims_cabinet_14d;
```

## Frontend

### Card "Identidad del Ledger"

El dashboard muestra:
- **Pagos pagados**: Total de registros con `is_paid = true`
- **Sin identidad**: Registros con ambos (driver_id, person_key) NULL
- **Enriquecidos**: Registros donde `identity_enriched = true`

### Banner Warning

Si `Total Paid = 0` pero `ledger_rows_is_paid_true > 0`, se muestra un banner que explica:
- Hay pagos pagados en ledger pero sin identidad
- Cuántos fueron enriquecidos
- Cuántos siguen sin identidad
- Links a modales para ver detalles

### Modales

Los modales de ledger (sin match / con match) ahora incluyen:
- Columna `identity_enriched`: Muestra si la identidad fue enriquecida
- `match_rule` y `match_confidence`: Para auditoría

## Limitaciones

1. **Matching solo por nombre único**: Si hay múltiples drivers con el mismo nombre normalizado, no se asigna identidad (por seguridad)
2. **No sobrescribe identidades existentes**: Si el ledger ya tenía `driver_id`/`person_key`, se preserva
3. **No crea nuevos identity_links**: Solo usa identidades existentes en `ops.v_driver_name_index`

## Próximos Pasos (Opcional)

Si se necesita más enriquecimiento:
1. Usar `source_pk` para buscar relaciones directas (si existe)
2. Implementar matching por teléfono/licencia (si están disponibles)
3. Crear identity_links nuevos (requiere proceso controlado y revisable)

## Auditoría

Todos los enriquecimientos son auditable:
- `match_rule`: Indica el método usado
- `match_confidence`: Nivel de confianza
- `identity_enriched`: Flag que identifica registros enriquecidos
- Campos originales preservados: `driver_id_original`, `person_key_original`

Esto permite revisar qué registros fueron enriquecidos y por qué método.

