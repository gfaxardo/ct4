# Sistema de Enriquecimiento de Identidad para Ledger

## Objetivo

Enriquecer `ops.yango_payment_status_ledger` con `driver_id` y `person_key` **SIN reingestar pagos**, usando reglas + scoring auditables y evitando falsos positivos.

## Características

- ✅ **No reingesta pagos**: Solo actualiza columnas de identidad en registros existentes
- ✅ **Scoring auditable**: Cada match tiene un score calculado (0-100)
- ✅ **Evita falsos positivos**: Solo actualiza cuando:
  - Score >= umbral (default: 85)
  - Candidato único (sin ambigüedad)
- ✅ **Explicable**: Cada actualización incluye `match_rule` y `match_confidence`
- ✅ **No toca campos críticos**: No modifica `payment_key`, `state_hash`, `snapshot_at`

## Componentes

### 1. Función de Normalización: `ops.normalize_person_name()`

Normalización robusta de nombres:
- Lower case
- Unaccent (quita tildes)
- Remueve puntuación
- Colapsa espacios
- Tokeniza y ordena alfabéticamente
- Opcionalmente remueve partículas (de, del, la, los, etc.)

**Uso:**
```sql
SELECT ops.normalize_person_name('Luis Fabio Quispe', true);
-- Resultado: 'fabio luis quispe'
```

### 2. Función de Scoring: `ops.calculate_name_match_score()`

Calcula score de matching entre dos nombres (0-100):
- **Score 100**: Match exacto después de normalización
- **Score 85**: Mismos tokens, orden diferente
- **Score <85**: Porcentaje de tokens coincidentes * 70

**Uso:**
```sql
SELECT ops.calculate_name_match_score('Luis Quispe', 'Quispe Luis');
-- Resultado: 85 (mismos tokens, orden diferente)
```

### 3. Función Principal: `ops.enrich_ledger_identity()`

Enriquece identidad en el ledger. Retorna tabla con resultados.

**Parámetros:**
- `min_score_threshold` (NUMERIC, default: 85): Score mínimo para actualizar
- `dry_run` (BOOLEAN, default: false): Si true, solo muestra qué se actualizaría sin hacer cambios

**Retorna:**
- `payment_key`: Clave del pago
- `raw_driver_name`: Nombre original del driver
- `candidate_driver_id`: driver_id del candidato encontrado
- `candidate_person_key`: person_key del candidato encontrado
- `candidate_full_name`: Nombre completo del candidato
- `match_score`: Score del match (0-100)
- `match_rule`: Regla de matching usada
- `match_confidence`: Nivel de confianza (high/medium/low)
- `action_taken`: Acción realizada (UPDATED/DRY_RUN_SKIP)
- `reason`: Razón de la acción

## Uso

### Paso 1: Dry Run (Recomendado)

Ejecutar primero en modo dry_run para ver qué se actualizaría:

```sql
SELECT * FROM ops.enrich_ledger_identity(
    min_score_threshold => 85,
    dry_run => true
);
```

### Paso 2: Ejecutar Enriquecimiento

Si los resultados del dry_run son correctos, ejecutar la actualización:

```sql
SELECT * FROM ops.enrich_ledger_identity(
    min_score_threshold => 85,
    dry_run => false
);
```

### Paso 3: Verificar Resultados

Usar las vistas de verificación:

```sql
-- Estadísticas generales
SELECT * FROM ops.v_ledger_enrichment_stats;

-- Candidatos ambiguos (no actualizados)
SELECT * FROM ops.v_ledger_ambiguous_candidates;

-- Distribución por regla/confianza
SELECT * FROM ops.v_ledger_match_distribution;
```

## Vistas de Verificación

### `ops.v_ledger_enrichment_stats`

Estadísticas de enriquecimiento:
- `total_rows`: Total de filas en el ledger
- `enriched_rows`: Filas con driver_id o person_key
- `unenriched_rows`: Filas sin identidad
- `enrichment_percentage`: Porcentaje enriquecido
- `match_none_count`: Filas con match_rule='none'
- `confidence_unknown_count`: Filas con match_confidence='unknown'
- `successfully_matched_count`: Filas exitosamente matcheadas

### `ops.v_ledger_ambiguous_candidates`

Candidatos ambiguos (múltiples matches) que NO fueron actualizados:
- `payment_key`: Clave del pago
- `raw_driver_name`: Nombre original
- `candidate_count`: Cantidad de candidatos encontrados
- `max_score`: Score máximo entre candidatos
- `reason`: 'AMBIGUOUS'

### `ops.v_ledger_match_distribution`

Distribución de matches por regla y confianza:
- `match_rule`: Regla usada (name_exact_match, name_tokens_match, etc.)
- `match_confidence`: Confianza (high, medium, low)
- `row_count`: Cantidad de filas
- `percentage`: Porcentaje del total

## Reglas de Matching

### `name_exact_match` (Score >= 100)
- Match exacto después de normalización
- Confianza: `high`

### `name_tokens_match` (Score >= 85)
- Mismos tokens, orden diferente
- Confianza: `medium`

### `name_partial_match` (Score < 85)
- Algunos tokens coinciden
- Confianza: `low`
- **Nota**: Solo se actualiza si score >= umbral

## Restricciones

1. **Prohibido reingestar pagos**: Solo actualiza columnas de identidad
2. **Prohibido asignar si hay ambigüedad**: Solo actualiza cuando hay un único candidato
3. **Todo cambio debe ser explicable**: Cada actualización incluye `match_rule` y `match_confidence`
4. **No toca campos críticos**: No modifica `payment_key`, `state_hash`, `snapshot_at`

## Ejemplo Completo

```sql
-- 1. Ver estado actual
SELECT * FROM ops.v_ledger_enrichment_stats;

-- 2. Dry run
SELECT 
    payment_key,
    raw_driver_name,
    candidate_full_name,
    match_score,
    match_rule,
    match_confidence
FROM ops.enrich_ledger_identity(85, true)
LIMIT 10;

-- 3. Ejecutar enriquecimiento
SELECT COUNT(*) AS updated_count
FROM ops.enrich_ledger_identity(85, false);

-- 4. Verificar resultados
SELECT * FROM ops.v_ledger_enrichment_stats;
SELECT * FROM ops.v_ledger_match_distribution;

-- 5. Ver candidatos ambiguos (para revisión manual)
SELECT * FROM ops.v_ledger_ambiguous_candidates
ORDER BY candidate_count DESC, max_score DESC
LIMIT 20;
```

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

### Score muy bajo

- Ajustar `min_score_threshold` (default: 85)
- Verificar normalización de nombres:
  ```sql
  SELECT 
      ops.normalize_person_name('Luis Quispe', true) AS norm1,
      ops.normalize_person_name('Quispe Luis', true) AS norm2;
  ```

## Notas

- La función es **idempotente**: puede ejecutarse múltiples veces sin duplicar actualizaciones
- Solo actualiza filas donde `driver_id IS NULL AND person_key IS NULL`
- Los scores se calculan en tiempo real, no se almacenan
- Las vistas de verificación se actualizan automáticamente al consultar





















