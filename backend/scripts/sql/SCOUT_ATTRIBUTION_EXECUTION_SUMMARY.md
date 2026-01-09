# Resumen de Ejecución: Análisis de Atribución de Scouts

## ✅ Archivos Generados y Ajustados

### 1. Script de Diagnóstico
**Archivo:** `backend/scripts/sql/diagnose_scout_attribution.sql`

**Contenido:**
- ✅ Query 1: Inventario de columnas candidatas en schemas `public`, `canon`, `ops`
- ✅ Query 2: Profiling automático por tabla (conteos, distinct, porcentajes)
- ✅ Query 3: Profiling manual de tablas conocidas:
  - `observational.lead_events`
  - `observational.lead_ledger`
  - `public.module_ct_migrations`
  - `public.module_ct_scouting_daily`
- ✅ Query 4: Identificación de columnas de identificación de conductor
- ✅ Query 5: Detección de conflictos (mismo person_key con múltiples scouts)
- ✅ Query 6: Muestras de datos por tabla candidata
- ✅ Query 7: Análisis de cobertura (% de eventos/personas con scout_id)
- ✅ Query 8: Búsqueda de otras tablas de atribución

**Ajustes realizados:**
- ✅ Reemplazado `canon.drivers` por `observational.lead_events` y `observational.lead_ledger`
- ✅ Agregado soporte para `payload_json->>'scout_id'` en `lead_events`
- ✅ Agregado `public.module_ct_migrations` y `public.module_ct_scouting_daily`

### 2. Script de Recomendaciones y Vistas
**Archivo:** `backend/scripts/sql/scout_attribution_recommendations.sql`

**Contenido:**
- ✅ Propuesta de `ops.v_scout_attribution_raw` (UNION ALL de todas las fuentes)
- ✅ Propuesta de `ops.v_scout_attribution` (1 fila por person_key/driver_id)
- ✅ Propuesta de `ops.v_scout_attribution_conflicts` (detección de conflictos)
- ✅ Queries de verificación

**Ajustes realizados:**
- ✅ Prioridad 1: `observational.lead_ledger.attributed_scout_id` (ya procesado)
- ✅ Prioridad 2: `observational.lead_events.scout_id` (eventos directos)
- ✅ Prioridad 3: `public.module_ct_migrations.scout_id` (migraciones)
- ✅ Prioridad 4: `public.module_ct_scouting_daily.scout_id` (scouting diario)
- ✅ Soporte para extraer `scout_id` desde `payload_json` en `lead_events`

### 3. Documentación
**Archivo:** `docs/ops/SCOUT_ATTRIBUTION_ANALYSIS.md`

**Contenido:**
- ✅ Resumen ejecutivo
- ✅ Explicación de fuentes identificadas
- ✅ Recomendaciones de source of truth
- ✅ Estrategia de resolución de conflictos
- ✅ Próximos pasos

**Ajustes realizados:**
- ✅ Actualizado source of truth a `observational.lead_ledger`
- ✅ Documentada integración con `ops.v_attribution_canonical` existente
- ✅ Actualizadas queries de verificación

## 📊 Fuentes de Datos Identificadas

### Fuentes Principales (Confirmadas)
1. **observational.lead_ledger.attributed_scout_id**
   - Source of Truth Principal
   - Grano: 1 fila por person_key
   - Confiabilidad: ALTA

2. **observational.lead_events.scout_id**
   - Eventos de leads originales
   - Grano: Múltiples eventos por person_key
   - Confiabilidad: MEDIA-ALTA
   - Nota: scout_id puede estar en columna o en payload_json

3. **public.module_ct_migrations.scout_id** (si existe)
   - Migraciones de flota
   - Confiabilidad: MEDIA-ALTA

4. **public.module_ct_scouting_daily.scout_id** (si existe)
   - Scouting diario
   - Confiabilidad: MEDIA

### Fuentes Secundarias (a verificar)
- Otras tablas con campos `recruiter`, `referral`, `captador`, etc.
- Requieren validación cruzada

## 🎯 Próximos Pasos de Ejecución

### Paso 1: Ejecutar Diagnóstico
```sql
-- En pgAdmin o psql
\i backend/scripts/sql/diagnose_scout_attribution.sql
```

**Resultados esperados:**
- Lista de todas las columnas candidatas
- Estadísticas de cobertura por tabla
- Identificación de conflictos
- Muestras de datos

### Paso 2: Revisar Resultados
- Verificar qué tablas existen realmente
- Analizar cobertura de scout_id
- Identificar conflictos que requieren resolución manual

### Paso 3: Ajustar Vistas (si es necesario)
- Modificar `scout_attribution_recommendations.sql` según tablas reales encontradas
- Agregar/quitar fuentes según resultados del diagnóstico

### Paso 4: Crear Vistas
```sql
-- En pgAdmin o psql
\i backend/scripts/sql/scout_attribution_recommendations.sql
```

### Paso 5: Validar
```sql
-- Verificar cobertura
SELECT 
    'Total person_key con scout_id' AS metric,
    COUNT(DISTINCT person_key) AS count
FROM ops.v_scout_attribution
WHERE person_key IS NOT NULL;

-- Verificar conflictos
SELECT COUNT(*) AS conflict_count
FROM ops.v_scout_attribution_conflicts;

-- Distribución por scout
SELECT 
    scout_id,
    COUNT(*) AS attribution_count
FROM ops.v_scout_attribution
GROUP BY scout_id
ORDER BY attribution_count DESC
LIMIT 20;
```

## ⚠️ Notas Importantes

1. **No se crean tablas ni migraciones** - Solo vistas y queries de diagnóstico
2. **Las vistas propuestas son tentativas** - Requieren ajuste según tablas reales
3. **Ya existe `ops.v_attribution_canonical`** - La nueva vista complementa y unifica todas las fuentes
4. **Los conflictos deben resolverse manualmente** - O con reglas de negocio específicas
5. **El source of truth principal es `observational.lead_ledger`** - Ya procesado por el sistema de atribución

## 📝 Integración con Sistema Existente

- **`ops.v_attribution_canonical`** ya existe y hace atribución desde `lead_events`
- **`ops.v_scout_attribution_raw`** propuesta unifica todas las fuentes (lead_ledger, lead_events, migrations, scouting_daily)
- **`ops.v_scout_attribution`** propuesta resuelve conflictos y proporciona 1 fila por person_key/driver_id
- **`ops.v_scout_attribution_conflicts`** propuesta identifica casos que requieren revisión manual

## ✅ Estado Actual

- ✅ Scripts de diagnóstico generados y ajustados
- ✅ Vistas propuestas definidas
- ✅ Documentación actualizada
- ⏳ Pendiente: Ejecución en base de datos real
- ⏳ Pendiente: Validación de resultados
- ⏳ Pendiente: Ajustes finales según tablas reales


