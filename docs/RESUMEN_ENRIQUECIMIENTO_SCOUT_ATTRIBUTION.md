# Resumen: Enriquecimiento de Scout Attribution

## Problema Identificado

Basado en el chat anterior y la investigación actual, se identificó que:

1. **Gap grande de drivers sin scout**: 84.49% sin filtro, 43.22% con filtro "solo con deuda"
2. **Vista actual solo usa `lead_ledger`**: `v_yango_collection_with_scout` hace LEFT JOIN directo a `observational.lead_ledger`, perdiendo scouts de otras fuentes
3. **Falta `cabinet_payments`**: La vista `v_scout_attribution_raw` NO incluye `public.module_ct_cabinet_payments.scout_id` (PRIORITY 5)
4. **Falta enriquecimiento con `scout_name`**: No se usa `v_dim_scouts` para mostrar el nombre del scout

## Fuentes de Atribución Scout (Multifuente)

El sistema tiene múltiples fuentes de atribución scout con prioridad:

1. **PRIORITY 1**: `observational.lead_ledger.attributed_scout_id` (source-of-truth) ✅ Implementado
2. **PRIORITY 2**: `observational.lead_events.scout_id` o `payload_json->>'scout_id'` ✅ Implementado
3. **PRIORITY 3**: `public.module_ct_migrations.scout_id` ✅ Implementado
4. **PRIORITY 4**: `public.module_ct_scouting_daily.scout_id` ✅ Implementado
5. **PRIORITY 5**: `public.module_ct_cabinet_payments.scout_id` ❌ **NO implementado** (NUEVO)

## Solución Propuesta

### Paso 1: Actualizar `v_scout_attribution_raw` para incluir `cabinet_payments`

**Archivo**: `backend/scripts/sql/10_create_v_scout_attribution_raw.sql` (o usar versión ENRICHED)

**Cambios**:
- Agregar UNION ALL con PRIORITY 5: `public.module_ct_cabinet_payments.scout_id`
- Unir por `person_key` (prioridad) o `driver_id` (si `person_key` es NULL)
- Excluir si ya está en prioridades 1-4

**Script creado**: `backend/scripts/sql/10_create_v_scout_attribution_raw_ENRICHED.sql`

### Paso 2: Actualizar `v_yango_collection_with_scout` para usar vista canónica multifuente

**Archivo**: `backend/scripts/sql/04_yango_collection_with_scout.sql` (o usar versión ENRICHED)

**Cambios**:
- Reemplazar LEFT JOIN directo a `lead_ledger` por LEFT JOIN a `ops.v_scout_attribution` (vista canónica)
- Unir por `person_key` (prioridad) o `driver_id` (si `person_key` es NULL)
- Agregar LEFT JOIN a `ops.v_dim_scouts` para enriquecer con `scout_name`
- Agregar campos de metadata: `scout_source_table`, `scout_origin_tag`, `scout_attribution_date`, `scout_priority`
- Actualizar `scout_quality_bucket` para incluir nuevas fuentes (MIGRATIONS_ONLY, CABINET_PAYMENTS_ONLY, etc.)

**Script creado**: `backend/scripts/sql/04_yango_collection_with_scout_ENRICHED.sql`

### Paso 3: Verificar que el endpoint ya soporte los nuevos campos

**Archivo**: `backend/app/api/v1/ops_payments.py`

**Estado actual**:
- ✅ Ya usa `scout.scout_name` en el query (línea 437)
- ✅ Ya usa `scout.scout_quality_bucket` en el query (línea 438)
- ✅ El schema `CabinetFinancialRow` ya tiene `scout_name` definido

**Acción requerida**: Ninguna, el endpoint ya está preparado.

### Paso 4: Verificar que `v_dim_scouts` existe

**Archivo**: `backend/sql/ops/v_dim_scouts.sql`

**Estado**: ✅ Existe y está lista para usar

## Impacto Esperado

1. **Reducción del gap de drivers sin scout**: 
   - Incluir `cabinet_payments` debería cubrir más drivers
   - Usar vista canónica multifuente debería capturar scouts de todas las fuentes disponibles

2. **Mejor UX**: 
   - Mostrar `scout_name` en lugar de solo `scout_id`
   - Mostrar fuente de atribución para auditoría

3. **Trazabilidad**:
   - Conocer la fuente de cada atribución (`scout_source_table`)
   - Prioridad de la atribución (`scout_priority`)

## Scripts a Ejecutar (en orden)

1. **Primero**: Actualizar `v_scout_attribution_raw` para incluir `cabinet_payments`
   ```sql
   -- Ejecutar: backend/scripts/sql/10_create_v_scout_attribution_raw_ENRICHED.sql
   ```

2. **Segundo**: Actualizar `v_scout_attribution` (se regenera automáticamente desde `v_scout_attribution_raw`)
   ```sql
   -- Ejecutar: backend/scripts/sql/11_create_v_scout_attribution.sql (debe regenerarse)
   ```

3. **Tercero**: Actualizar `v_yango_collection_with_scout` para usar vista canónica y enriquecer con `scout_name`
   ```sql
   -- Ejecutar: backend/scripts/sql/04_yango_collection_with_scout_ENRICHED.sql
   ```

## Validación

Después de ejecutar los scripts, ejecutar:

```sql
-- Verificar cobertura de scout
SELECT 
    'COBERTURA SCOUT EN COBRANZA YANGO (ENRIQUECIDA)' AS metric,
    COUNT(*) AS total_claims,
    COUNT(*) FILTER (WHERE is_scout_resolved = true) AS claims_with_scout,
    COUNT(*) FILTER (WHERE is_scout_resolved = false) AS claims_without_scout,
    ROUND((COUNT(*) FILTER (WHERE is_scout_resolved = true)::NUMERIC / NULLIF(COUNT(*), 0) * 100), 2) AS pct_with_scout
FROM ops.v_yango_collection_with_scout;

-- Distribución por fuente
SELECT 
    scout_source_table,
    COUNT(*) AS claim_count,
    ROUND(COUNT(*)::NUMERIC / NULLIF((SELECT COUNT(*) FROM ops.v_yango_collection_with_scout WHERE is_scout_resolved = true), 0) * 100, 2) AS pct
FROM ops.v_yango_collection_with_scout
WHERE is_scout_resolved = true
GROUP BY scout_source_table
ORDER BY claim_count DESC;
```

## Notas Importantes

1. **Orden de ejecución**: Los scripts deben ejecutarse en orden porque `v_scout_attribution` depende de `v_scout_attribution_raw`, y `v_yango_collection_with_scout` depende de `v_scout_attribution`.

2. **Compatibilidad con endpoint**: El endpoint ya está preparado para los nuevos campos, no requiere cambios.

3. **Testing**: Después de ejecutar los scripts, verificar que:
   - Los KPIs de scout aumentan (más drivers con scout)
   - `scout_name` aparece en la UI
   - Los valores de `scout_quality_bucket` incluyen las nuevas fuentes

4. **Rollback**: Si hay problemas, se puede revertir ejecutando las versiones originales de las vistas.
