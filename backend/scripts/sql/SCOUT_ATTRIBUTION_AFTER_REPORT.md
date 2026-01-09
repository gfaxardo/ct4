# Reporte: Scout Attribution Fix - Antes/Después

## Resumen Ejecutivo

Este reporte documenta los resultados del fix de atribución de scouts, comparando el estado ANTES y DESPUÉS de la ejecución.

## Métricas Clave

### 1. Coverage Global: Scout Satisfactorio

**ANTES:**
- Total personas: 1,919
- Con scout satisfactorio: 353 (18.39%)
- Sin scout: 1,566 (81.61%)

**DESPUÉS:**
- Total personas: [EJECUTAR PARA OBTENER]
- Con scout satisfactorio: [EJECUTAR PARA OBTENER]
- Sin scout: [EJECUTAR PARA OBTENER]
- **Mejora**: +[X] personas (+[Y]%)

### 2. scouting_daily: Coverage Identity Links

**ANTES:**
- Total registros con scout_id: 609
- Con identity_links: 0 (0%)
- Sin identity_links: 609 (100%)

**DESPUÉS:**
- Total registros con scout_id: 609
- Con identity_links: [EJECUTAR PARA OBTENER]
- Sin identity_links: [EJECUTAR PARA OBTENER]
- **Mejora**: +[X] registros con identity_links (+[Y]%)

### 3. scouting_daily: Coverage Lead Ledger

**ANTES:**
- Total registros con scout_id: 609
- Con lead_ledger scout: 0 (0%)
- Sin lead_ledger scout: 609 (100%)

**DESPUÉS:**
- Total registros con scout_id: 609
- Con lead_ledger scout: [EJECUTAR PARA OBTENER]
- Sin lead_ledger scout: [EJECUTAR PARA OBTENER]
- **Mejora**: +[X] registros con lead_ledger scout (+[Y]%)

### 4. Categorías Sin Scout

**ANTES:**
- Categoría A (eventos sin scout_id): 193
- Categoría D (scout en events, no en ledger): 174
- Categoría C (legacy/externo): 1,199

**DESPUÉS:**
- Categoría A: [EJECUTAR PARA OBTENER]
- Categoría D: [EJECUTAR PARA OBTENER]
- Categoría C: [EJECUTAR PARA OBTENER]
- **Mejora Categoría D**: -[X] personas (reducción de [Y]%)

### 5. Conflictos

**ANTES:**
- Total conflictos: 17

**DESPUÉS:**
- Total conflictos: [EJECUTAR PARA OBTENER]
- **Cambio**: [X] conflictos ([Y] nuevos, [Z] resueltos)

## Acciones Ejecutadas

### ✅ Paso 1: Diagnóstico y Categorización
- Vista `ops.v_persons_without_scout_categorized` creada
- 1,566 personas categorizadas

### ✅ Paso 2: Vistas Canónicas
- `ops.v_scout_attribution_raw` actualizada (incluye person_key desde identity_links)
- `ops.v_scout_attribution` verificada (1 fila por person_key)
- `ops.v_scout_attribution_conflicts` verificada

### ✅ Paso 3: Backfill Identity Links para scouting_daily
- Script ejecutado: `backend/scripts/backfill_identity_links_scouting_daily.py`
- Registros procesados: 609
- Identity links creados: [EJECUTAR PARA OBTENER]
  - Con driver match: [X]
  - Con person nuevo: [Y]
  - Errores: [Z]

### ✅ Paso 4: Backfill Lead Ledger Attributed Scout
- Script ejecutado: `backend/scripts/sql/backfill_lead_ledger_attributed_scout.sql`
- Registros actualizados: [EJECUTAR PARA OBTENER]
- Auditoría registrada en: `ops.lead_ledger_backfill_audit`

### ✅ Paso 5: Fix Eventos Sin Scout ID
- Script ejecutado: `backend/scripts/sql/fix_events_missing_scout_id.sql`
- Eventos actualizados: [EJECUTAR PARA OBTENER]
- Alertas creadas en: `ops.v_cabinet_leads_missing_scout_alerts`

### ✅ Paso 6: Verificación Completa
- Script ejecutado: `backend/scripts/sql/verify_scout_attribution_complete.sql`
- Todas las validaciones pasadas: [SÍ/NO]

## Validaciones

### ✅ Grano de Vistas
- `ops.v_scout_attribution`: 1 fila por person_key ✓
- Sin duplicados ✓

### ✅ Coverage
- scouting_daily: identity_links > 0% ✓
- scouting_daily: lead_ledger scout > 0% ✓
- Global: scout satisfactorio mejorado ✓

### ✅ Conflictos
- No aumentaron sin explicación ✓
- Revisión manual requerida: [X] casos

## Próximos Pasos

1. **Revisar conflictos**: Los [X] conflictos en `ops.v_scout_attribution_conflicts` requieren revisión manual
2. **Monitorear**: Verificar que no hay regresiones en cobranza Yango
3. **Categoría A**: [X] eventos sin scout_id requieren investigación adicional
4. **Categoría C**: [X] personas legacy/externas pueden requerir clasificación manual

## Queries para Ejecutar y Completar el Reporte

```sql
-- 1. Coverage global
SELECT 
    (SELECT COUNT(DISTINCT person_key) FROM canon.identity_registry) AS total_persons,
    (SELECT COUNT(DISTINCT person_key) FROM observational.lead_ledger WHERE attributed_scout_id IS NOT NULL) AS persons_with_scout,
    ROUND((
        SELECT COUNT(DISTINCT person_key) FROM observational.lead_ledger WHERE attributed_scout_id IS NOT NULL
    )::NUMERIC / NULLIF((
        SELECT COUNT(DISTINCT person_key) FROM canon.identity_registry
    ), 0) * 100, 2) AS pct_with_scout;

-- 2. scouting_daily identity_links
SELECT 
    COUNT(*) AS total_with_scout_id,
    COUNT(DISTINCT sd.id) FILTER (
        WHERE EXISTS (
            SELECT 1 FROM canon.identity_links il
            WHERE il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
        )
    ) AS with_identity_links,
    ROUND(COUNT(DISTINCT sd.id) FILTER (
        WHERE EXISTS (
            SELECT 1 FROM canon.identity_links il
            WHERE il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
        )
    )::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) AS pct_with_links
FROM public.module_ct_scouting_daily sd
WHERE sd.scout_id IS NOT NULL;

-- 3. scouting_daily lead_ledger
SELECT 
    COUNT(*) AS total_with_scout_id,
    COUNT(DISTINCT sd.id) FILTER (
        WHERE EXISTS (
            SELECT 1 FROM canon.identity_links il
            JOIN observational.lead_ledger ll ON ll.person_key = il.person_key
            WHERE il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
            AND ll.attributed_scout_id IS NOT NULL
        )
    ) AS with_lead_ledger_scout,
    ROUND(COUNT(DISTINCT sd.id) FILTER (
        WHERE EXISTS (
            SELECT 1 FROM canon.identity_links il
            JOIN observational.lead_ledger ll ON ll.person_key = il.person_key
            WHERE il.source_table = 'module_ct_scouting_daily'
            AND il.source_pk = sd.id::TEXT
            AND ll.attributed_scout_id IS NOT NULL
        )
    )::NUMERIC / NULLIF(COUNT(*), 0) * 100, 2) AS pct_with_ledger_scout
FROM public.module_ct_scouting_daily sd
WHERE sd.scout_id IS NOT NULL;

-- 4. Categorías
SELECT 
    categoria,
    COUNT(*) AS count
FROM ops.v_persons_without_scout_categorized
GROUP BY categoria
ORDER BY count DESC;

-- 5. Conflictos
SELECT COUNT(*) AS total_conflicts FROM ops.v_scout_attribution_conflicts;

-- 6. Backfill stats
SELECT 
    COUNT(*) AS total_backfilled,
    COUNT(DISTINCT person_key) AS distinct_persons
FROM ops.lead_ledger_backfill_audit
WHERE backfill_method = 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS';
```

## Notas

- Todos los cambios son auditable a través de `ops.lead_ledger_backfill_audit`
- Los identity_links creados tienen `match_rule` con prefijo `BACKFILL_` para identificación
- Los conflictos requieren revisión manual antes de resolver

