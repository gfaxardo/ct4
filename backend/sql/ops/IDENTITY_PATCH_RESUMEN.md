# Resumen: Patch de Identidad en Ingest de Pagos Yango

## ✅ Estado: COMPLETADO Y FUNCIONANDO

### Problema Resuelto
El pipeline de pagos no persistía la identidad (`driver_id`/`person_key`) en el ledger cuando el match por nombre aparecía después del insert inicial.

**Causa raíz:**
- `ops.ingest_yango_payments_snapshot()` usa `ON CONFLICT (payment_key, state_hash) DO NOTHING`
- `state_hash` solo depende de `is_paid` (MD5(is_paid::text))
- Cuando un match aparece después, `driver_id` cambia de NULL a NOT NULL pero `state_hash` no cambia
- El INSERT es rechazado por el conflicto y el `driver_id` nunca se persiste

### Solución Implementada
Se agregó un **UPDATE posterior** en `ops.ingest_yango_payments_snapshot()` que:
- Actualiza `driver_id`, `person_key`, `match_rule`, `match_confidence` y `snapshot_at`
- Solo cuando el ledger tiene `driver_id IS NULL` y `raw_current` tiene `driver_id IS NOT NULL`
- Unir por `(payment_key, state_hash)` para mantener idempotencia

### Archivos Creados/Modificados

1. **`backend/sql/ops/ingest_yango_payments_snapshot.sql`** (modificado)
   - Función principal con UPDATE posterior agregado

2. **`backend/sql/ops/patch_ingest_identity_upsert.sql`** (nuevo)
   - Patch standalone para aplicar el fix

3. **`backend/sql/ops/verify_ingest_identity_gap.sql`** (nuevo)
   - Queries de verificación del gap antes/después

4. **`backend/sql/ops/apply_identity_patch_steps.sql`** (nuevo)
   - Script guía paso a paso para aplicar el patch

5. **`backend/sql/ops/verify_patch_execution.sql`** (nuevo)
   - Verificación detallada de ejecución del patch

6. **`backend/sql/ops/v_yango_payments_raw_current_aliases.sql`** (creado)
   - Vista alias para compatibilidad

### Verificación de Éxito

✅ **Función existe:** `ops.ingest_yango_payments_snapshot()` creada correctamente  
✅ **Gap cerrado:** `count_gap = 0` (no hay registros con identidad en raw que no estén en ledger)  
✅ **Matches persistidos:** 195 matches con `driver_name_unique` tienen `driver_id` en el ledger

### Uso Normal

El patch es **transparente** - no requiere cambios en el código que llama a la función:

```sql
-- Ejecutar ingest normalmente
SELECT ops.ingest_yango_payments_snapshot();
```

La función ahora:
1. Inserta nuevos registros (si cambia el estado)
2. Actualiza automáticamente la identidad cuando aparece después (UPDATE posterior)

### Mantenimiento

- El patch es **idempotente** - se puede ejecutar múltiples veces sin efectos secundarios
- El UPDATE solo afecta registros donde `ledger.driver_id IS NULL` y `raw_current.driver_id IS NOT NULL`
- No modifica otros campos del ledger, solo identidad y metadata de match

### Notas Técnicas

- El `state_hash` sigue siendo `MD5(is_paid::text)` - no se modificó
- El UPDATE se ejecuta **después** del INSERT para mantener la idempotencia
- El `snapshot_at` se actualiza cuando se backfillea la identidad para tracking

---

**Fecha de implementación:** [Fecha actual]  
**Estado:** ✅ Producción - Funcionando correctamente












