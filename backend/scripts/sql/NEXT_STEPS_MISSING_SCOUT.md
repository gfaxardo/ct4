# Próximos Pasos: Resolver Registros Sin Scout

## 📊 Situación Actual

**Resumen:**
- **Total personas:** 1,919
- **Con scout atribuido:** 353 (18.39%)
- **Sin scout atribuido:** 1,566 (81.61%)
- **Con scout en eventos:** 527
- **Sin scout en ledger:** 165

## 🔍 Análisis de Razones

### Razones Principales por las que NO tienen scout:

1. **No hay eventos con scout_id en lead_events**
   - Algunas personas tienen `lead_events` pero los eventos no incluyen `scout_id`
   - Puede ser porque:
     - Los eventos vienen de fuentes que no capturan scout (ej: cabinet leads antiguos)
     - El scout_id no se propagó correctamente durante la ingesta

2. **No tienen lead_ledger o lead_ledger sin attributed_scout_id**
   - 165 personas tienen `lead_ledger` pero sin `attributed_scout_id`
   - Razones según `attribution_rule` y `confidence_level`:
     - `attribution_rule = NULL` o `'none'`: No se encontró evidencia de scout
     - `confidence_level = 'low'`: Evidencia insuficiente
     - `decision_status = 'unassigned'`: No se pudo asignar automáticamente

3. **Personas sin lead_events**
   - Algunas personas en `identity_registry` no tienen eventos asociados
   - Pueden ser:
     - Drivers legacy sin leads asociados
     - Personas creadas por otros procesos (no relacionados con scouts)

## 📋 Próximos Pasos Recomendados

### PASO 1: Backfill desde Fuentes Originales

**Objetivo:** Buscar scout_id en las tablas fuente originales que no se propagaron a `lead_events`

```sql
-- 1.1 Buscar en module_ct_migrations
SELECT 
    mm.driver_id,
    mm.scout_id,
    mm.scout_name,
    mm.hire_date
FROM public.module_ct_migrations mm
WHERE mm.scout_id IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM observational.lead_events le
        WHERE le.source_table = 'module_ct_migrations'
            AND le.source_pk = mm.id::TEXT
            AND (le.scout_id = mm.scout_id OR le.payload_json->>'scout_id' = mm.scout_id::TEXT)
    )
LIMIT 20;

-- 1.2 Buscar en module_ct_scouting_daily
SELECT 
    sd.id,
    sd.scout_id,
    sd.driver_phone,
    sd.driver_license,
    sd.registration_date
FROM public.module_ct_scouting_daily sd
WHERE sd.scout_id IS NOT NULL
    AND NOT EXISTS (
        SELECT 1 FROM observational.lead_events le
        WHERE le.source_table = 'module_ct_scouting_daily'
            AND le.source_pk = sd.id::TEXT
            AND (le.scout_id = sd.scout_id OR le.payload_json->>'scout_id' = sd.scout_id::TEXT)
    )
LIMIT 20;
```

**Acción:** Crear script de backfill que:
- Identifique personas sin scout
- Busque scout_id en tablas fuente originales
- Actualice `lead_events` o cree nuevos eventos con scout_id
- Re-ejecute el proceso de atribución

### PASO 2: Mejorar Proceso de Atribución

**Objetivo:** Ajustar reglas de atribución para capturar más casos

**Análisis necesario:**
```sql
-- Ver casos donde hay evidencia pero no se atribuyó
SELECT 
    ll.person_key,
    ll.attribution_rule,
    ll.confidence_level,
    ll.decision_status,
    ll.evidence_json,
    (SELECT COUNT(*) FROM observational.lead_events le 
     WHERE le.person_key = ll.person_key 
     AND (le.scout_id IS NOT NULL OR le.payload_json->>'scout_id' IS NOT NULL)) AS events_with_scout
FROM observational.lead_ledger ll
WHERE ll.attributed_scout_id IS NULL
    AND EXISTS (
        SELECT 1 FROM observational.lead_events le
        WHERE le.person_key = ll.person_key
            AND (le.scout_id IS NOT NULL OR le.payload_json->>'scout_id' IS NOT NULL)
    )
LIMIT 20;
```

**Acción:** 
- Revisar reglas de atribución en `ops.v_attribution_canonical`
- Ajustar prioridades y umbrales de confianza
- Re-ejecutar atribución para casos con evidencia

### PASO 3: Clasificar Personas Sin Scout

**Objetivo:** Categorizar los 1,566 casos sin scout

```sql
-- Categorías:
-- A) Tienen lead_events pero sin scout_id
-- B) Tienen lead_ledger pero sin attributed_scout_id (aunque haya evidencia)
-- C) No tienen lead_events ni lead_ledger (legacy/externos)
-- D) Tienen scout en eventos pero no se propagó a ledger

WITH categorized AS (
    SELECT 
        ir.person_key,
        CASE 
            WHEN EXISTS (SELECT 1 FROM observational.lead_events le 
                         WHERE le.person_key = ir.person_key 
                         AND (le.scout_id IS NOT NULL OR le.payload_json->>'scout_id' IS NOT NULL))
                AND NOT EXISTS (SELECT 1 FROM observational.lead_ledger ll 
                               WHERE ll.person_key = ir.person_key 
                               AND ll.attributed_scout_id IS NOT NULL)
            THEN 'D: Scout en eventos, no en ledger'
            
            WHEN EXISTS (SELECT 1 FROM observational.lead_events le WHERE le.person_key = ir.person_key)
                AND NOT EXISTS (SELECT 1 FROM observational.lead_events le 
                               WHERE le.person_key = ir.person_key 
                               AND (le.scout_id IS NOT NULL OR le.payload_json->>'scout_id' IS NOT NULL))
            THEN 'A: Tienen eventos pero sin scout_id'
            
            WHEN EXISTS (SELECT 1 FROM observational.lead_ledger ll WHERE ll.person_key = ir.person_key)
            THEN 'B: Tienen ledger pero sin scout'
            
            ELSE 'C: Sin eventos ni ledger (legacy/externo)'
        END AS categoria
    FROM canon.identity_registry ir
    LEFT JOIN observational.lead_ledger ll_with_scout 
        ON ll_with_scout.person_key = ir.person_key 
        AND ll_with_scout.attributed_scout_id IS NOT NULL
    WHERE ll_with_scout.person_key IS NULL
)
SELECT 
    categoria,
    COUNT(*) AS count
FROM categorized
GROUP BY categoria
ORDER BY count DESC;
```

**Acción:** 
- Crear vista `ops.v_persons_without_scout_categorized`
- Priorizar categorías D y A (más fáciles de resolver)
- Categoría C puede requerir revisión manual o marcado como legacy

### PASO 4: Script de Backfill Automático

**Crear script:** `backend/scripts/backfill_missing_scout_attribution.py`

**Funcionalidad:**
1. Identificar personas sin scout (categoría D y A)
2. Buscar scout_id en:
   - `lead_events` (para categoría D)
   - Tablas fuente originales (para categoría A)
3. Actualizar o crear eventos con scout_id
4. Re-ejecutar proceso de atribución
5. Actualizar `lead_ledger`

### PASO 5: Validación y Monitoreo

**Queries de validación:**
```sql
-- Antes y después del backfill
SELECT 
    'Antes' AS etapa,
    COUNT(DISTINCT person_key) AS personas_con_scout
FROM observational.lead_ledger
WHERE attributed_scout_id IS NOT NULL

UNION ALL

SELECT 
    'Después' AS etapa,
    COUNT(DISTINCT person_key) AS personas_con_scout
FROM observational.lead_ledger
WHERE attributed_scout_id IS NOT NULL;
```

**Monitoreo continuo:**
- Alertar cuando nuevas personas se crean sin scout
- Revisar semanalmente el gap
- Documentar casos que requieren intervención manual

## 🎯 Priorización

1. **ALTA:** Categoría D (527 personas) - Scout en eventos pero no en ledger
   - Solución: Re-ejecutar atribución o ajustar reglas

2. **MEDIA:** Categoría A - Tienen eventos pero sin scout_id
   - Solución: Backfill desde tablas fuente

3. **BAJA:** Categoría B - Tienen ledger pero sin scout (puede ser por reglas)
   - Solución: Revisar y ajustar reglas de atribución

4. **REVISIÓN MANUAL:** Categoría C - Sin eventos ni ledger
   - Solución: Clasificar como legacy o buscar en otras fuentes

## 📝 Scripts a Crear

1. `backend/scripts/sql/categorize_persons_without_scout.sql` - Vista de categorización
2. `backend/scripts/backfill_missing_scout_attribution.py` - Script de backfill
3. `backend/scripts/validate_scout_attribution_coverage.py` - Validación
4. `backend/scripts/sql/monitor_scout_attribution_gap.sql` - Monitoreo


