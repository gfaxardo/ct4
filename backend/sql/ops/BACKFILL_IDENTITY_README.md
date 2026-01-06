# Backfill de Identidad en Ledger

## Objetivo

Backfill de identidad (`driver_id`, `person_key`) en `ops.yango_payment_status_ledger` **SIN reingestar pagos**. Umbral score = 0.85. Evita falsos positivos: si hay ambigüedad, NO asigna.

## Componentes

### A1) Funciones de Normalización

1. **`ops.normalize_person_name(text)`** → text
   - lower
   - unaccent
   - replace puntuación por espacio (mantener letras/números)
   - colapsar espacios y trim

2. **`ops.normalize_person_tokens_sorted(text)`** → text
   - usa `normalize_person_name`
   - split por espacio
   - remover tokens vacíos
   - ordenar tokens
   - volver a juntar con espacio

3. **`ops.normalize_person_tokens_sorted_strip_particles(text)`** → text
   - igual que `tokens_sorted` pero remover tokens: de, del, la, las, los, y

### A2) Índice Canónico de Drivers

**Vista: `ops.v_driver_name_index_extended`**

Contiene:
- `driver_id`
- `person_key`
- `full_name_raw`
- `full_name_norm` = `ops.normalize_person_name(full_name_raw)`
- `full_name_tokens` = `ops.normalize_person_tokens_sorted(full_name_raw)`
- `full_name_tokens_nop` = `ops.normalize_person_tokens_sorted_strip_particles(full_name_raw)`

### A3) Función de Backfill

**`ops.backfill_ledger_identity(min_score_threshold, dry_run)`**

**Reglas de Matching:**

- **R1: exact tokens** (score 0.95)
  - `full_name_tokens = normalize_person_tokens_sorted(raw_driver_name)`
  - `match_rule`: `'r1_tokens_unique'`
  - `match_confidence`: `'high'`

- **R2: exact norm** (score 0.85)
  - `full_name_norm = normalize_person_name(raw_driver_name)`
  - `match_rule`: `'r2_norm_unique'`
  - `match_confidence`: `'medium'`

- **R3: exact tokens_nop** (score 0.85)
  - `full_name_tokens_nop = normalize_person_tokens_sorted_strip_particles(raw_driver_name)`
  - `match_rule`: `'r3_tokens_nop_unique'`
  - `match_confidence`: `'medium'`

**Criterios de Asignación:**

- Solo actualiza si:
  - `score >= min_score_threshold` (default: 0.85)
  - Candidato único (`count(*)=1` para esa regla/score en ese `payment_key`)
- Para cada `payment_key`, elige el mejor candidato por mayor score
- Si hay ambigüedad (múltiples candidatos), NO asigna

**Campos Actualizados:**

- `driver_id`
- `person_key`
- `match_rule` (`'r1_tokens_unique'` / `'r2_norm_unique'` / `'r3_tokens_nop_unique'` / `'none'`)
- `match_confidence` (`'high'` para 0.95 / `'medium'` para 0.85)

**Campos NO Tocados:**

- `payment_key`
- `state_hash`
- `snapshot_at`
- `paid_flag_source`

### A4) Vistas de Verificación

1. **`ops.v_ledger_backfill_stats`**
   - `total`: Total de filas
   - `enriched`: Filas con identidad
   - `still_null`: Filas sin identidad
   - `enrichment_percentage`: Porcentaje enriquecido

2. **`ops.v_ledger_match_rule_distribution`**
   - Distribución por `match_rule`
   - Conteo y porcentaje

3. **`ops.v_ledger_ambiguous_candidates`**
   - Lista de candidatos ambiguos (candidates > 1)
   - Para revisión manual

## Uso

### Paso 1: Crear Funciones y Vistas

```sql
\i backend/sql/ops/backfill_ledger_identity.sql
```

### Paso 2: Verificar Estado Actual

```sql
-- Estadísticas antes del backfill
SELECT * FROM ops.v_ledger_backfill_stats;

-- Ver cuántos registros necesitan enriquecimiento
SELECT still_null FROM ops.v_ledger_backfill_stats;
```

### Paso 3: Dry Run (Recomendado)

```sql
-- Ver qué se actualizaría sin hacer cambios
SELECT 
    payment_key,
    raw_driver_name,
    candidate_full_name,
    match_rule,
    match_score,
    match_confidence,
    action_taken,
    reason
FROM ops.backfill_ledger_identity(
    min_score_threshold => 0.85,
    dry_run => true
)
ORDER BY match_score DESC
LIMIT 20;
```

### Paso 4: Ejecutar Backfill

```sql
-- Ejecutar backfill real
SELECT 
    COUNT(*) AS total_candidates,
    COUNT(*) FILTER (WHERE action_taken = 'UPDATED') AS updated_count,
    COUNT(*) FILTER (WHERE action_taken = 'DRY_RUN_SKIP') AS skipped_count,
    COUNT(*) FILTER (WHERE match_rule = 'r1_tokens_unique') AS r1_count,
    COUNT(*) FILTER (WHERE match_rule = 'r2_norm_unique') AS r2_count,
    COUNT(*) FILTER (WHERE match_rule = 'r3_tokens_nop_unique') AS r3_count
FROM ops.backfill_ledger_identity(
    min_score_threshold => 0.85,
    dry_run => false
);
```

### Paso 5: Verificar Resultados

```sql
-- Estadísticas después del backfill
SELECT * FROM ops.v_ledger_backfill_stats;

-- Distribución por regla
SELECT * FROM ops.v_ledger_match_rule_distribution;

-- Candidatos ambiguos (no actualizados)
SELECT * FROM ops.v_ledger_ambiguous_candidates
ORDER BY candidate_count_per_rule DESC, max_score DESC
LIMIT 20;
```

## Ejemplo Completo

```sql
-- 1. Crear funciones y vistas
\i backend/sql/ops/backfill_ledger_identity.sql

-- 2. Estado antes
SELECT * FROM ops.v_ledger_backfill_stats;

-- 3. Dry run
SELECT 
    payment_key,
    raw_driver_name,
    candidate_full_name,
    match_rule,
    match_score,
    match_confidence
FROM ops.backfill_ledger_identity(0.85, true)
LIMIT 10;

-- 4. Ejecutar backfill
SELECT COUNT(*) AS updated
FROM ops.backfill_ledger_identity(0.85, false);

-- 5. Verificar resultados
SELECT * FROM ops.v_ledger_backfill_stats;
SELECT * FROM ops.v_ledger_match_rule_distribution;

-- 6. Revisar ambiguos
SELECT * FROM ops.v_ledger_ambiguous_candidates
ORDER BY candidate_count_per_rule DESC
LIMIT 20;
```

## Reglas de Matching

### R1: exact tokens (Score 0.95)
- Match exacto por tokens ordenados
- Más estricto, mayor confianza
- `match_rule`: `'r1_tokens_unique'`
- `match_confidence`: `'high'`

### R2: exact norm (Score 0.85)
- Match exacto por normalización básica
- `match_rule`: `'r2_norm_unique'`
- `match_confidence`: `'medium'`

### R3: exact tokens_nop (Score 0.85)
- Match exacto por tokens sin partículas
- Permite matching cuando hay partículas diferentes
- `match_rule`: `'r3_tokens_nop_unique'`
- `match_confidence`: `'medium'`

## Restricciones

1. **Prohibido reingestar pagos**: Solo actualiza columnas de identidad
2. **Prohibido asignar si hay ambigüedad**: Solo actualiza cuando hay un único candidato por regla
3. **Umbral mínimo**: Solo actualiza si `score >= 0.85`
4. **No toca campos críticos**: No modifica `payment_key`, `state_hash`, `snapshot_at`, `paid_flag_source`

## Troubleshooting

### No se actualizan filas

1. Verificar que hay filas sin identidad:
   ```sql
   SELECT COUNT(*) 
   FROM ops.yango_payment_status_ledger 
   WHERE driver_id IS NULL AND person_key IS NULL;
   ```

2. Verificar que hay candidatos en el índice:
   ```sql
   SELECT COUNT(*) FROM ops.v_driver_name_index_extended;
   ```

3. Verificar candidatos ambiguos:
   ```sql
   SELECT * FROM ops.v_ledger_ambiguous_candidates;
   ```

### Verificar normalización

```sql
-- Probar funciones de normalización
SELECT 
    'Luis Fabio Quispe' AS original,
    ops.normalize_person_name('Luis Fabio Quispe') AS norm,
    ops.normalize_person_tokens_sorted('Luis Fabio Quispe') AS tokens,
    ops.normalize_person_tokens_sorted_strip_particles('Luis Fabio Quispe') AS tokens_nop;
```

## Notas

- La función es **idempotente**: puede ejecutarse múltiples veces sin duplicar actualizaciones
- Solo actualiza filas donde `driver_id IS NULL AND person_key IS NULL`
- Las reglas se evalúan en orden de prioridad (R1 > R2 > R3)
- Si un `payment_key` tiene match en R1, no se evalúa R2 ni R3
- Los candidatos ambiguos se registran en `v_ledger_ambiguous_candidates` para revisión manual






















