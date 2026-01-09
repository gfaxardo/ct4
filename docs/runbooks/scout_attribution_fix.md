# Runbook: Scout Attribution Fix

## Objetivo

Cerrar el gap "0% scout satisfactorio" y normalizar atribución scout end-to-end, asegurando que todos los registros con `scout_id` en las fuentes lleguen a `observational.lead_ledger.attributed_scout_id` (source of truth).

## Contexto

- **Total personas**: 1,919
- **Con scout canónico**: 353 (18.39%)
- **Sin scout**: 1,566 (81.61%)

### Categorías sin scout:
- **C (legacy/externo)**: 1,199 - Sin events ni ledger
- **A (eventos sin scout_id)**: 193 - Principalmente `module_ct_cabinet_leads`
- **D (scout en events, no en ledger)**: 174 - Requiere propagación

### scouting_daily:
- **609 registros** con `scout_id`
- **605 tienen lead_events** con `scout_id`
- **0 tienen identity_links** → **0% "satisfactorio"**

## Definición de "Scout Satisfactorio"

Un scout es "satisfactorio" cuando existe en el source of truth:
- `observational.lead_ledger.attributed_scout_id` (por `person_key`)

## Ejecución

### Opción 1: Ejecución Automatizada (Recomendada)

```bash
cd backend
python scripts/execute_scout_attribution_fix.py
```

Este script ejecuta todos los pasos en orden:
1. Diagnóstico y categorización
2. Crear/actualizar vistas canónicas
3. Backfill identity_links para scouting_daily
4. Backfill lead_ledger attributed_scout
5. Fix eventos sin scout_id
6. Verificación completa

### Opción 2: Ejecución Manual (Paso a Paso)

#### Paso 1: Diagnóstico y Categorización

```bash
psql $DATABASE_URL -f backend/scripts/sql/categorize_persons_without_scout.sql
```

O desde Python:
```bash
python -c "from app.config import settings; import psycopg2; from urllib.parse import urlparse; from pathlib import Path; parsed = urlparse(settings.database_url); conn = psycopg2.connect(host=parsed.hostname, port=parsed.port or 5432, database=parsed.path[1:], user=parsed.username, password=parsed.password); conn.autocommit = True; cur = conn.cursor(); cur.execute(Path('backend/scripts/sql/categorize_persons_without_scout.sql').read_text(encoding='utf-8')); print('Vista creada')"
```

#### Paso 2: Crear/Actualizar Vistas Canónicas

```bash
psql $DATABASE_URL -f backend/scripts/sql/scout_attribution_recommendations.sql
```

#### Paso 3: Backfill Identity Links para scouting_daily

```bash
cd backend
python scripts/backfill_identity_links_scouting_daily.py
```

**Output esperado:**
```
Total procesados: 609
Creados con driver match: X
Creados con person nuevo: Y
Errores: Z
```

#### Paso 4: Backfill Lead Ledger Attributed Scout

```bash
psql $DATABASE_URL -f backend/scripts/sql/backfill_lead_ledger_attributed_scout.sql
```

**Output esperado:**
```
Actualizados X registros en lead_ledger
Registrados X registros en auditoría
```

#### Paso 5: Fix Eventos Sin Scout ID

```bash
psql $DATABASE_URL -f backend/scripts/sql/fix_events_missing_scout_id.sql
```

#### Paso 6: Verificación Completa

```bash
psql $DATABASE_URL -f backend/scripts/sql/verify_scout_attribution_complete.sql
```

## Validaciones

### 1. Coverage scouting_daily

```sql
-- % de scouting_daily con scout_id que tienen identity_links
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

-- % que llegan a lead_ledger con attributed_scout_id
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
```

**Esperado después del fix:**
- `pct_with_links` > 0% (antes: 0%)
- `pct_with_ledger_scout` > 0% (antes: 0%)

### 2. Coverage Global

```sql
SELECT 
    (SELECT COUNT(DISTINCT person_key) FROM canon.identity_registry) AS total_persons,
    (SELECT COUNT(DISTINCT person_key) FROM observational.lead_ledger WHERE attributed_scout_id IS NOT NULL) AS persons_with_scout,
    ROUND((
        SELECT COUNT(DISTINCT person_key) FROM observational.lead_ledger WHERE attributed_scout_id IS NOT NULL
    )::NUMERIC / NULLIF((
        SELECT COUNT(DISTINCT person_key) FROM canon.identity_registry
    ), 0) * 100, 2) AS pct_with_scout
```

**Esperado después del fix:**
- `pct_with_scout` > 18.39% (mejora desde baseline)

### 3. Categoría D (Scout en events, no en ledger)

```sql
SELECT 
    categoria,
    COUNT(*) AS count
FROM ops.v_persons_without_scout_categorized
WHERE categoria = 'D: Scout en eventos, no en ledger'
GROUP BY categoria;
```

**Esperado después del fix:**
- Categoría D debería reducirse sustancialmente (de 174 a menos)

### 4. Conflictos

```sql
SELECT COUNT(*) AS total_conflicts
FROM ops.v_scout_attribution_conflicts;
```

**Esperado:**
- No deben aumentar sin explicación
- Revisar los 17 conflictos existentes

### 5. Grano de Vistas

```sql
-- Verificar que v_scout_attribution tiene 1 fila por person_key
SELECT 
    COUNT(*) AS total_rows,
    COUNT(DISTINCT person_key) AS distinct_person_keys,
    CASE 
        WHEN COUNT(*) = COUNT(DISTINCT person_key) THEN 'OK'
        ELSE 'ERROR: Hay duplicados'
    END AS status
FROM ops.v_scout_attribution
WHERE person_key IS NOT NULL;
```

**Esperado:**
- `status = 'OK'` (sin duplicados)

## Rollback

### Si es necesario revertir cambios:

#### 1. Revertir Backfill de Lead Ledger

```sql
-- Revertir cambios de backfill en lead_ledger usando auditoría
UPDATE observational.lead_ledger ll
SET 
    attributed_scout_id = a.old_attributed_scout_id,
    attribution_rule = a.attribution_rule_old,
    confidence_level = a.confidence_level_old::attributionconfidence,
    evidence_json = a.evidence_json_old,
    updated_at = NOW()
FROM ops.lead_ledger_backfill_audit a
WHERE ll.person_key = a.person_key
    AND a.backfill_method = 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS'
    AND a.backfill_timestamp >= NOW() - INTERVAL '1 day';
```

#### 2. Revertir Identity Links (Solo si es necesario)

**ADVERTENCIA**: Esto puede afectar otros procesos. Solo hacer si es absolutamente necesario.

```sql
-- Eliminar identity_links creados por el backfill
DELETE FROM canon.identity_links
WHERE source_table = 'module_ct_scouting_daily'
    AND match_rule LIKE 'BACKFILL_%'
    AND linked_at >= NOW() - INTERVAL '1 day';
```

## Revisión de Conflictos

Los conflictos se pueden revisar en:

```sql
SELECT * FROM ops.v_scout_attribution_conflicts
ORDER BY distinct_scout_count DESC, total_attributions DESC;
```

Para cada conflicto, revisar:
1. ¿Cuál scout_id es el correcto?
2. ¿Hay evidencia adicional en otras fuentes?
3. ¿Requiere resolución manual?

## Validación en Cobranza Yango

Para validar que el fix no rompió la lógica de cobranza:

```sql
-- Verificar que los scouts atribuidos están siendo usados correctamente
SELECT 
    ll.attributed_scout_id,
    COUNT(DISTINCT ll.person_key) AS distinct_persons,
    COUNT(DISTINCT cp.payment_id) AS distinct_payments
FROM observational.lead_ledger ll
LEFT JOIN public.module_ct_cabinet_payments cp 
    ON cp.person_key = ll.person_key
WHERE ll.attributed_scout_id IS NOT NULL
GROUP BY ll.attributed_scout_id
ORDER BY distinct_persons DESC
LIMIT 20;
```

## Troubleshooting

### Error: "relation ops.lead_ledger_backfill_audit does not exist"

El script `backfill_lead_ledger_attributed_scout.sql` crea esta tabla automáticamente. Si falla, ejecutar manualmente:

```sql
CREATE TABLE IF NOT EXISTS ops.lead_ledger_backfill_audit (
    id SERIAL PRIMARY KEY,
    person_key UUID NOT NULL,
    old_attributed_scout_id INTEGER,
    new_attributed_scout_id INTEGER,
    -- ... (ver script completo)
);
```

### Error: "No se pueden crear identity_links"

Verificar que:
1. `canon.drivers_index` está actualizado
2. Los datos de `scouting_daily` tienen `driver_license` o `driver_phone` válidos
3. No hay restricciones de integridad referencial

### Performance: Scripts muy lentos

Si los scripts son muy lentos:
1. Ejecutar en horarios de bajo tráfico
2. Considerar ejecutar por lotes (fechas)
3. Verificar índices en `canon.identity_links` y `observational.lead_ledger`

## Contacto

Para dudas o problemas:
1. Revisar logs del script
2. Consultar `ops.lead_ledger_backfill_audit` para auditoría
3. Revisar `ops.v_scout_attribution_conflicts` para conflictos

