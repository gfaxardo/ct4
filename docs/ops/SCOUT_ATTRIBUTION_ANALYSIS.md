# Análisis de Atribución de Conductores a Scouts

## Objetivo
Identificar todas las fuentes de datos que relacionan conductores con scouts (scout_id, recruiter, referral, etc.) y establecer un "source of truth" canónico.

## Archivos Generados

1. **`backend/scripts/sql/diagnose_scout_attribution.sql`**
   - Queries de diagnóstico completas
   - Inventario de columnas candidatas
   - Profiling por tabla
   - Detección de conflictos

2. **`backend/scripts/sql/scout_attribution_recommendations.sql`**
   - Propuesta de vistas canónicas
   - Definición de `ops.v_scout_attribution_raw`
   - Definición de `ops.v_scout_attribution` (1 fila por driver)
   - Vista de conflictos

## Columnas Candidatas Identificadas

El script busca columnas con los siguientes patrones:
- `%scout%` - scout_id, scout_name, etc.
- `%recruit%` - recruiter, recruiter_id, etc.
- `%referr%` - referral, referrer, etc.
- `%capt%` - captador, captation, etc.
- `%promot%` - promoter, promotion, etc.
- `%agent%` - agent, agent_id, etc.
- `%utm%` - utm_source, utm_campaign, etc.
- `%source%` - source, source_id, etc.
- `%campaign%` - campaign, campaign_id, etc.
- `%link%` - link_id, referral_link, etc.
- `%owner%` - owner, owner_id, etc.

## Fuentes de Datos Identificadas

### 1. **observational.lead_ledger.attributed_scout_id** (Source of Truth Principal)
- **Grano:** 1 fila por `person_key` (después de atribución)
- **Confiabilidad:** ALTA
- **Actualización:** Por proceso de atribución de leads
- **Uso recomendado:** Fuente primaria para atribución (ya procesada)

### 2. **observational.lead_events.scout_id** (Fuente de eventos)
- **Grano:** Múltiples eventos por `person_key`
- **Confiabilidad:** MEDIA-ALTA
- **Nota:** `scout_id` puede estar en columna directa o en `payload_json->>'scout_id'`
- **Uso recomendado:** Auditoría histórica y trazabilidad de eventos

### 3. **public.module_ct_migrations.scout_id** (Si existe)
- **Grano:** Múltiples migraciones por driver
- **Confiabilidad:** MEDIA-ALTA
- **Uso recomendado:** Trazabilidad de migraciones de flota

### 4. **public.module_ct_scouting_daily.scout_id** (Si existe)
- **Grano:** Múltiples registros de scouting por driver
- **Confiabilidad:** MEDIA
- **Uso recomendado:** Trazabilidad de scouting diario

### 4. **Otras fuentes secundarias**
- Tablas con campos `recruiter`, `referral`, `captador`, etc.
- Requieren validación cruzada
- Confiabilidad: BAJA-MEDIA

## Estructura Propuesta de Vistas

### `ops.v_scout_attribution_raw`
Vista que hace UNION ALL de todas las fuentes, estandarizando campos:
- `person_key` - Identificador de persona
- `driver_id` - ID del conductor
- `driver_license` - Licencia del conductor
- `driver_phone` - Teléfono del conductor
- `scout_id` - ID del scout
- `acquisition_method` - Método de adquisición (canon_drivers, scouting_daily, cabinet_lead, etc.)
- `source_table` - Tabla de origen
- `source_pk` - Primary key de la tabla origen
- `attribution_date` - Fecha de atribución
- `created_at` - Fecha de creación del registro
- `priority` - Prioridad de la fuente (1 = mayor prioridad)

### `ops.v_scout_attribution`
Vista canónica con **1 fila por driver_id**, usando la fuente de mayor prioridad:
- Prioridad 1: `canon.drivers`
- Prioridad 2: `ops.scouting_daily`
- Prioridad 3: `module_ct_cabinet_leads`
- En caso de empate, se toma la atribución más reciente

### `ops.v_scout_attribution_conflicts`
Vista que identifica conflictos donde un mismo driver tiene múltiples scouts asignados.

## Recomendaciones

### Source of Truth
**`observational.lead_ledger.attributed_scout_id`** debe ser el source of truth principal porque:
1. Ya pasó por el proceso de atribución canónica
2. Tiene grano 1:1 (1 fila por person_key después de atribución)
3. Incluye `attribution_confidence` y `attribution_rule` para trazabilidad
4. Es actualizada por el proceso de atribución de leads
5. Tiene alta confiabilidad

**Nota:** Ya existe `ops.v_attribution_canonical` que hace atribución de scouts desde `lead_events`. 
La vista propuesta `ops.v_scout_attribution_raw` complementa y unifica todas las fuentes disponibles.

### Estrategia de Resolución de Conflictos
1. **Prioridad por fuente:** 
   - `observational.lead_ledger` (prioridad 1) - Ya procesado
   - `observational.lead_events` (prioridad 2) - Eventos directos
   - `public.module_ct_migrations` (prioridad 3) - Migraciones
   - `public.module_ct_scouting_daily` (prioridad 4) - Scouting diario
2. **Prioridad por fecha:** Si hay múltiples atribuciones de la misma fuente, tomar la más reciente
3. **Detección de conflictos:** Usar `ops.v_scout_attribution_conflicts` para identificar casos que requieren revisión manual
4. **Integración con vista existente:** `ops.v_attribution_canonical` ya hace atribución desde `lead_events`. La nueva vista unifica todas las fuentes.

### Próximos Pasos

1. **Ejecutar diagnóstico:**
   ```sql
   \i backend/scripts/sql/diagnose_scout_attribution.sql
   ```

2. **Revisar resultados:**
   - Verificar qué tablas existen realmente
   - Analizar cobertura de scout_id
   - Identificar conflictos

3. **Ajustar vistas propuestas:**
   - Modificar `scout_attribution_recommendations.sql` según tablas reales
   - Agregar fuentes adicionales si se encuentran

4. **Crear vistas:**
   ```sql
   \i backend/scripts/sql/scout_attribution_recommendations.sql
   ```

5. **Validar:**
   - Verificar que `ops.v_scout_attribution` tiene 1 fila por driver_id
   - Revisar conflictos en `ops.v_scout_attribution_conflicts`
   - Validar cobertura vs. `canon.drivers`

## Queries de Verificación

```sql
-- Cobertura total por person_key
SELECT 
    COUNT(DISTINCT ll.person_key) AS total_persons,
    COUNT(DISTINCT ll.person_key) FILTER (WHERE ll.attributed_scout_id IS NOT NULL) AS persons_with_scout,
    ROUND(COUNT(DISTINCT ll.person_key) FILTER (WHERE ll.attributed_scout_id IS NOT NULL)::NUMERIC / 
          NULLIF(COUNT(DISTINCT ll.person_key), 0) * 100, 2) AS pct_coverage
FROM observational.lead_ledger ll;

-- Conflictos detectados
SELECT COUNT(*) AS conflict_count
FROM ops.v_scout_attribution_conflicts;

-- Distribución por scout
SELECT 
    scout_id,
    COUNT(*) AS driver_count
FROM ops.v_scout_attribution
GROUP BY scout_id
ORDER BY driver_count DESC
LIMIT 20;
```

## Notas Importantes

- **NO se crean tablas ni migraciones** - Solo vistas y queries de diagnóstico
- Las vistas propuestas son **tentativas** - Requieren ajuste según tablas reales encontradas
- Se recomienda ejecutar primero el diagnóstico para ver qué tablas/columnas existen realmente
- Los conflictos deben resolverse manualmente o con reglas de negocio específicas

