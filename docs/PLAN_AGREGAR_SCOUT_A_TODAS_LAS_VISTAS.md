# Plan: Agregar Scout Attribution a Todas las Vistas con Drivers

## Objetivo

Agregar información de scout atribuido (scout_id, scout_name, scout_quality_bucket) a todas las vistas que contengan drivers.

## Vistas Identificadas

### Vistas Principales (Alta Prioridad)

1. **`ops.v_payments_driver_matrix_cabinet`** ⭐ MÁS IMPORTANTE
   - Vista principal del driver matrix
   - Usada por endpoint `/ops/driver-matrix`
   - Grano: 1 fila por driver_id
   - JOIN: `v_scout_attribution` por `person_key` o `driver_id`

2. **`ops.v_cabinet_milestones_achieved`**
   - Milestones alcanzados por drivers
   - Grano: 1 fila por (driver_id, milestone_value)
   - JOIN: `v_scout_attribution` por `person_key` o `driver_id`

### Vistas Secundarias (Media Prioridad)

3. **`ops.v_cabinet_financial_14d`**
   - Ya tiene scout (a través de `v_yango_collection_with_scout`)
   - ✅ NO REQUIERE CAMBIOS

4. **`ops.v_yango_cabinet_claims_for_collection`**
   - Base para `v_yango_collection_with_scout`
   - ✅ Ya tiene scout en `v_yango_collection_with_scout`

### Vistas Menores (Baja Prioridad)

5. `ops.v_ct4_driver_achieved_from_trips`
6. `ops.v_ct4_eligible_drivers`
7. Otras vistas específicas

## Estrategia de Implementación

### Patrón Estándar

Para todas las vistas, usar el mismo patrón:

```sql
-- Agregar campos de scout
LEFT JOIN ops.v_scout_attribution sa
    ON (sa.person_key = base.person_key AND base.person_key IS NOT NULL)
    OR (sa.driver_id = base.driver_id AND base.person_key IS NULL AND sa.person_key IS NULL)
LEFT JOIN ops.v_dim_scouts ds
    ON ds.scout_id = sa.scout_id

-- Agregar columnas en SELECT
sa.scout_id,
ds.raw_name AS scout_name,
CASE 
    WHEN sa.source_table = 'observational.lead_ledger' THEN 'SATISFACTORY_LEDGER'
    WHEN sa.source_table = 'observational.lead_events' THEN 'EVENTS_ONLY'
    WHEN sa.source_table = 'public.module_ct_migrations' THEN 'MIGRATIONS_ONLY'
    WHEN sa.source_table = 'public.module_ct_scouting_daily' OR sa.source_table = 'module_ct_scouting_daily' THEN 'SCOUTING_DAILY_ONLY'
    WHEN sa.source_table = 'public.module_ct_cabinet_payments' THEN 'CABINET_PAYMENTS_ONLY'
    WHEN sa.scout_id IS NOT NULL THEN 'SCOUTING_DAILY_ONLY'
    ELSE 'MISSING'
END AS scout_quality_bucket,
CASE WHEN sa.scout_id IS NOT NULL THEN true ELSE false END AS is_scout_resolved
```

## Orden de Implementación

1. **`v_payments_driver_matrix_cabinet`** - Prioridad 1
2. **`v_cabinet_milestones_achieved`** - Prioridad 2
3. Otras vistas según necesidad

## Validación

Para cada vista:
1. Verificar que scout_id y scout_name están presentes
2. Verificar que el JOIN funciona correctamente
3. Verificar que no se rompe funcionalidad existente
4. Verificar performance (no debe degradarse significativamente)
