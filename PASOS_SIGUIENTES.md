# Pasos Siguientes: Atribución de Scouts

## ✅ Implementación Completada

Todos los componentes han sido creados según las especificaciones:

- ✅ FASE 0: Inspección de schema real
- ✅ FASE 1: Script `backfill_identity_links_scouting_daily.py`
- ✅ FASE 2: SQL `backfill_lead_ledger_attributed_scout.sql`
- ✅ FASE 3: Vista `v_cabinet_leads_missing_scout_alerts`
- ✅ FASE 4: Vistas canónicas (raw, attribution, conflicts, categorized)
- ✅ FASE 5: Vista final `v_scout_payment_base`
- ✅ FASE 6: Script `execute_scout_attribution_end_to_end.py`
- ✅ FASE 7: Runbook completo

---

## 🚀 Pasos para Ejecutar

### OPCIÓN 1: Ejecución Automática (Recomendada)

```powershell
# Desde la raíz del proyecto
.\EJECUTAR_SOLUCION_SCOUTS.ps1
```

Este script ejecuta automáticamente:
1. Verificación de conexión
2. Pipeline end-to-end completo
3. Validación de resultados

### OPCIÓN 2: Ejecución Manual Paso a Paso

#### PASO 1: Verificar Conexión

```powershell
cd backend
python scripts/verify_connection.py
```

**Salida esperada**: `✓ Conexión a base de datos OK`

---

#### PASO 2: Ejecutar Pipeline End-to-End

```powershell
cd backend
python scripts/execute_scout_attribution_end_to_end.py
```

**Este script ejecuta automáticamente:**
1. Diagnóstico inicial (métricas BEFORE)
2. Identity backfill scouting_daily
3. Lead_ledger backfill (categoría D)
4. Crear/actualizar todas las vistas
5. Verificación final (métricas AFTER)

**Tiempo estimado**: 5-15 minutos (depende del volumen de datos)

**Salida esperada**:
```
Métricas ANTES:
  - scouting_daily con scout_id: XXX
  - scouting_daily con identity: XXX
  - scouting_daily scout satisfactorio: XXX
  ...

Métricas DESPUÉS:
  - scouting_daily con scout_id: XXX
  - scouting_daily con identity: XXX (+YYY)
  - scouting_daily scout satisfactorio: XXX (+YYY)
  ...
```

---

#### PASO 3: Validar Resultados

##### Validación 1: Scouting Daily con Identity

```sql
SELECT 
    COUNT(*) FILTER (WHERE scout_id IS NOT NULL) AS total_with_scout,
    COUNT(*) FILTER (
        WHERE scout_id IS NOT NULL 
        AND EXISTS (
            SELECT 1 FROM canon.identity_links il
            WHERE il.source_table = 'module_ct_scouting_daily'
                AND il.source_pk = sd.id::TEXT
        )
    ) AS with_identity,
    ROUND(
        (COUNT(*) FILTER (
            WHERE scout_id IS NOT NULL 
            AND EXISTS (
                SELECT 1 FROM canon.identity_links il
                WHERE il.source_table = 'module_ct_scouting_daily'
                    AND il.source_pk = sd.id::TEXT
            )
        )::NUMERIC / 
        NULLIF(COUNT(*) FILTER (WHERE scout_id IS NOT NULL), 0)) * 100, 
        2
    ) AS pct_with_identity
FROM public.module_ct_scouting_daily sd;
```

**Esperado**: `pct_with_identity > 0%` (debería ser >50% después del backfill)

---

##### Validación 2: Scout Satisfactorio Global

```sql
SELECT 
    COUNT(DISTINCT ll.person_key) AS total_satisfactory,
    COUNT(DISTINCT ll.person_key) FILTER (
        WHERE EXISTS (
            SELECT 1 FROM canon.identity_links il
            WHERE il.person_key = ll.person_key
                AND il.source_table = 'module_ct_scouting_daily'
        )
    ) AS scouting_daily_satisfactory
FROM observational.lead_ledger ll
WHERE ll.attributed_scout_id IS NOT NULL;
```

**Esperado**: `total_satisfactory > 0` y `scouting_daily_satisfactory > 0`

---

##### Validación 3: Categoría D Reducida

```sql
SELECT 
    category,
    COUNT(*) AS count
FROM ops.v_persons_without_scout_categorized
GROUP BY category
ORDER BY category;
```

**Esperado**: 
- Categoría D debería ser menor que antes del backfill
- Si Categoría D > 0, son personas que necesitan `lead_ledger` creado primero

---

##### Validación 4: Conflictos

```sql
SELECT 
    COUNT(*) AS total_conflicts,
    COUNT(DISTINCT person_key) AS distinct_persons
FROM ops.v_scout_attribution_conflicts;
```

**Esperado**: Conflictos no deberían crecer sin razón. Si hay conflictos, son casos legítimos que requieren revisión manual.

---

##### Validación 5: Vista de Pagos

```sql
SELECT 
    payment_status,
    block_reason,
    COUNT(*) AS count
FROM ops.v_scout_payment_base
GROUP BY payment_status, block_reason
ORDER BY payment_status, block_reason;
```

**Esperado**:
- `ELIGIBLE` > 0 (personas elegibles para pago)
- `BLOCKED` con `block_reason` explícito (`NO_SCOUT`, `CONFLICT`, `NO_IDENTITY`)
- `PENDING` (milestone alcanzado pero fuera de ventana de 7 días)

---

#### PASO 4: Auditar Cambios

##### Auditoría 1: Identity Links Creados

```sql
SELECT 
    source_table,
    match_rule,
    confidence_level,
    COUNT(*) AS count,
    MIN(linked_at) AS first_link,
    MAX(linked_at) AS last_link
FROM canon.identity_links
WHERE source_table = 'module_ct_scouting_daily'
    AND linked_at >= CURRENT_DATE - INTERVAL '1 day'
GROUP BY source_table, match_rule, confidence_level
ORDER BY count DESC;
```

---

##### Auditoría 2: Lead_Ledger Actualizados

```sql
SELECT 
    backfill_method,
    attribution_rule_new,
    attribution_confidence_new,
    COUNT(*) AS count,
    MIN(backfill_timestamp) AS first_update,
    MAX(backfill_timestamp) AS last_update
FROM ops.lead_ledger_scout_backfill_audit
WHERE backfill_timestamp >= CURRENT_DATE - INTERVAL '1 day'
GROUP BY backfill_method, attribution_rule_new, attribution_confidence_new
ORDER BY count DESC;
```

---

##### Auditoría 3: Detalle de Cambios

```sql
SELECT 
    person_key,
    old_attributed_scout_id,
    new_attributed_scout_id,
    attribution_rule_new,
    attribution_confidence_new,
    backfill_timestamp,
    notes
FROM ops.lead_ledger_scout_backfill_audit
WHERE backfill_timestamp >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY backfill_timestamp DESC
LIMIT 50;
```

---

## 📊 Consultas de Diagnóstico

### Ver Estado Actual Completo

```sql
-- Resumen completo
SELECT 
    'scouting_daily con scout_id' AS metric,
    COUNT(*)::TEXT AS value
FROM public.module_ct_scouting_daily
WHERE scout_id IS NOT NULL

UNION ALL

SELECT 
    'scouting_daily con identity' AS metric,
    COUNT(DISTINCT sd.id)::TEXT AS value
FROM public.module_ct_scouting_daily sd
WHERE sd.scout_id IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM canon.identity_links il
        WHERE il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
    )

UNION ALL

SELECT 
    'scout satisfactorio global' AS metric,
    COUNT(DISTINCT person_key)::TEXT AS value
FROM observational.lead_ledger
WHERE attributed_scout_id IS NOT NULL

UNION ALL

SELECT 
    'categoría D' AS metric,
    COUNT(*)::TEXT AS value
FROM ops.v_persons_without_scout_categorized
WHERE category = 'D'

UNION ALL

SELECT 
    'conflictos' AS metric,
    COUNT(*)::TEXT AS value
FROM ops.v_scout_attribution_conflicts;
```

---

## ⚠️ Troubleshooting

### Problema: Script falla en conexión

**Causa**: Variables de entorno no configuradas

**Solución**:
```powershell
# Verificar variables de entorno
cd backend
python -c "from app.config import settings; print(settings.database_url)"
```

---

### Problema: scouting_daily sigue sin identity

**Causa**: Datos faltantes (phone/license) o matching falla

**Solución**: Revisar `canon.identity_unmatched`:
```sql
SELECT 
    source_table,
    reason_code,
    COUNT(*) AS count
FROM canon.identity_unmatched
WHERE source_table = 'module_ct_scouting_daily'
    AND created_at >= CURRENT_DATE - INTERVAL '1 day'
GROUP BY source_table, reason_code;
```

---

### Problema: Categoría D no se reduce

**Causa**: Personas no tienen `lead_ledger` creado aún

**Solución**: Estas personas necesitan pasar por el pipeline normal de creación de `lead_ledger` primero. Verificar:
```sql
SELECT COUNT(*) FROM ops.v_persons_without_scout_categorized
WHERE category = 'D'
    AND NOT EXISTS (
        SELECT 1 FROM observational.lead_ledger ll
        WHERE ll.person_key = ops.v_persons_without_scout_categorized.person_key
    );
```

---

### Problema: Conflictos aumentan

**Causa**: Datos inconsistentes o múltiples scouts legítimos

**Solución**: Revisar manualmente:
```sql
SELECT * FROM ops.v_scout_attribution_conflicts
ORDER BY distinct_scout_count DESC, total_sources DESC
LIMIT 20;
```

---

## 📝 Notas Importantes

1. **Idempotencia**: Todos los scripts son idempotentes. Se pueden ejecutar múltiples veces sin duplicar datos.

2. **Auditoría**: Todas las operaciones están auditadas en tablas append-only. No se pierden datos históricos.

3. **Seguridad**: Los scripts NO ejecutan pagos, solo declaran verdad operativa. Claims y pagos Yango no se modifican.

4. **No Inventar Scouts**: Si hay >1 scout distinto, es un CONFLICTO que requiere revisión manual.

---

## 🎯 Resultados Esperados

Después de la ejecución exitosa:

- ✅ **scouting_daily con identity** > 0% (idealmente >50%)
- ✅ **scout satisfactorio global** > 0
- ✅ **categoría D** reducida drásticamente
- ✅ **conflictos** no crecen sin razón
- ✅ **vista de pagos** funciona correctamente

---

## 📚 Documentación Adicional

- **Runbook completo**: `docs/runbooks/scout_attribution_end_to_end.md`
- **Scripts SQL**: `backend/scripts/sql/`
- **Scripts Python**: `backend/scripts/`

---

**Última actualización**: 2025-01-XX
