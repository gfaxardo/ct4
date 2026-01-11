# Runbook: Scout Attribution Fix

## Propósito

Este runbook documenta el proceso completo para cerrar Scout Attribution y dejar lista la base para pagar scouts sin discusión. Incluye auditoría, sanity-check, fixes de pipeline, backfills, vistas, verificación, integración con Cobranza Yango y base de liquidación diaria scout.

## Principios No Negociables

- **C0 Identidad no se recalcula globalmente**: Solo backfill segmentado y auditable.
- **C2 Elegibilidad define reglas**: C3 Claims solo nace desde C2; C4 Pagos concilia contra claims.
- **Source-of-truth canónico**: Para scout, "satisfactorio" = está en `observational.lead_ledger.attributed_scout_id` (por person_key) SI existe. Si no existe lead_ledger, entonces define el equivalente canónico actual y documenta el reemplazo.
- **No romper el flujo de cobro Yango**: Claims-to-collect/export existentes no se modifican.
- **Audit trail append-only**: Todo update debe tener audit trail o tabla de auditoría.

## Requisitos

### Variables de Entorno

El script requiere las siguientes variables de entorno (o configuración en `app/config.py`):

- `DATABASE_URL`: URL de conexión a PostgreSQL (formato: `postgresql://user:password@host:port/database`)

### Dependencias

- Python 3.8+
- PostgreSQL 12+
- Librerías Python: `psycopg2`, `sqlalchemy`, `psycopg2-binary`

## Archivos del PR

### A) SQL de Inventario/Diagnóstico (Idempotente)

1. `backend/scripts/sql/00_inventory_scout_sources.sql` - Inventario de tablas/columnas candidatas
2. `backend/scripts/sql/01_diagnose_scout_attribution.sql` - Diagnóstico completo
3. `backend/scripts/sql/02_categorize_persons_without_scout.sql` - Categorización (crea `ops.v_persons_without_scout_categorized`)
4. `backend/scripts/sql/03_verify_scout_attribution_views.sql` - Verificación final
5. `backend/scripts/sql/04_yango_collection_with_scout.sql` - Integración con cobranza Yango

### B) Vistas Canónicas de Atribución (Idempotente)

1. `backend/scripts/sql/10_create_v_scout_attribution_raw.sql` - Vista RAW con todas las fuentes
2. `backend/scripts/sql/11_create_v_scout_attribution.sql` - Vista canónica (1 fila por person_key)
3. `backend/scripts/sql/12_create_v_scout_attribution_conflicts.sql` - Vista de conflictos

### C) Backfills / Fixes (Segmentados, Auditable)

1. `backend/scripts/backfill_identity_links_scouting_daily.py` - Backfill de identity_links
2. `backend/scripts/sql/20_backfill_lead_ledger_attributed_scout.sql` - Backfill lead_ledger
3. `backend/scripts/sql/21_backfill_lead_events_scout_from_cabinet_leads.sql` - Backfill cabinet leads → events
4. `backend/scripts/sql/22_create_backfill_audit_tables.sql` - Crear tablas de auditoría

### D) Automatización de Ejecución Batch

1. `backend/scripts/execute_scout_attribution_fix.py` - Script Python principal
2. `backend/scripts/execute_scout_attribution_fix.ps1` - Script PowerShell para Windows

### E) Base para Liquidación Diaria Scout

1. `backend/scripts/sql/13_create_v_scout_daily_expected_base.sql` - Vista base para liquidación

## Cómo Ejecutar

### Opción 1: Script Python (Recomendado)

```bash
cd backend/scripts
python execute_scout_attribution_fix.py
```

### Opción 2: Script PowerShell (Windows)

```powershell
cd backend\scripts
.\execute_scout_attribution_fix.ps1
```

El script ejecuta automáticamente todos los pasos en orden:

1. Inventory (00)
2. Create/replace vistas (10-12)
3. Diagnose (baseline) (01)
4. Backfill audit tables (22)
5. Backfill identity_links scouting_daily
6. Backfill lead_ledger attributed_scout (20)
7. Backfill cabinet leads → events (21)
8. Recreate/refresh vistas (04, 13, 02)
9. Verify (03)
10. Genera reporte `SCOUT_ATTRIBUTION_AFTER_REPORT.md`

## Qué Revisar si Falla

### Error de Conexión a Base de Datos

- Verificar que `DATABASE_URL` esté configurado correctamente
- Verificar que PostgreSQL esté corriendo
- Verificar permisos de usuario en la base de datos

### Error en Vistas

- Verificar que existan las tablas base: `observational.lead_ledger`, `observational.lead_events`, `canon.identity_registry`, `canon.identity_links`
- Verificar que existan las tablas de fuente: `public.module_ct_scouting_daily`, `public.module_ct_cabinet_leads` (si aplica)
- Revisar logs del script para errores específicos de SQL

### Error en Backfills

- Verificar que las tablas de auditoría se hayan creado correctamente (`ops.identity_links_backfill_audit`, `ops.lead_ledger_scout_backfill_audit`, etc.)
- Revisar logs de backfill para ver qué registros fallaron y por qué
- Verificar que no haya conflictos de constraints (ej: identity_links ya existe)

### Cobertura 0%

Si después del fix la cobertura sigue en 0%:

1. Verificar que `module_ct_scouting_daily` tenga registros con `scout_id NOT NULL`
2. Verificar que existan `identity_links` para esos registros
3. Verificar que existan `lead_ledger` entries para los `person_key` correspondientes
4. Ejecutar diagnóstico manual: `backend/scripts/sql/01_diagnose_scout_attribution.sql`

## Cómo Revisar Conflictos y Categorías

### Conflictos (múltiples scout_ids para mismo person_key)

```sql
SELECT * FROM ops.v_scout_attribution_conflicts
ORDER BY distinct_scout_count DESC, total_records DESC
LIMIT 50;
```

Estos conflictos requieren revisión manual para decidir qué scout_id usar.

### Categorías de Personas Sin Scout

```sql
SELECT 
    categoria,
    COUNT(*) AS count,
    ROUND(COUNT(*)::NUMERIC / NULLIF((SELECT COUNT(*) FROM ops.v_persons_without_scout_categorized), 0) * 100, 2) AS pct
FROM ops.v_persons_without_scout_categorized
GROUP BY categoria
ORDER BY count DESC;
```

Categorías:
- **A**: Tiene lead_events pero sin scout_id
- **B**: Tiene lead_ledger sin scout (attribution_rule indica unassigned/bucket)
- **C**: Sin events ni ledger (legacy/externo)
- **D**: Scout en events pero no en ledger
- **E**: Otros (verificar manualmente)

### Muestras por Categoría

```sql
-- Categoría D (prioritaria para backfill)
SELECT * FROM ops.v_persons_without_scout_categorized
WHERE categoria = 'D: Scout en events pero no en ledger'
ORDER BY events_with_scout_count DESC, identity_created_at DESC
LIMIT 50;
```

## Cómo Validar en UI (Cobranza con Scout)

### Verificar Vista de Cobranza Yango con Scout

```sql
SELECT 
    scout_quality_bucket,
    COUNT(*) AS claim_count,
    ROUND(COUNT(*)::NUMERIC / NULLIF((SELECT COUNT(*) FROM ops.v_yango_collection_with_scout), 0) * 100, 2) AS pct
FROM ops.v_yango_collection_with_scout
GROUP BY scout_quality_bucket
ORDER BY claim_count DESC;
```

Calidad de atribución:
- **SATISFACTORY_LEDGER**: Desde lead_ledger (source-of-truth)
- **EVENTS_ONLY**: Solo desde eventos
- **SCOUTING_DAILY_ONLY**: Solo desde scouting_daily
- **MISSING**: Sin scout

### Cobertura de Scout en Cobranza

```sql
SELECT 
    COUNT(*) AS total_claims,
    COUNT(*) FILTER (WHERE is_scout_resolved = true) AS claims_with_scout,
    ROUND((COUNT(*) FILTER (WHERE is_scout_resolved = true)::NUMERIC / COUNT(*) * 100), 2) AS pct_with_scout
FROM ops.v_yango_collection_with_scout;
```

## Rollback / Seguridad

### Principios de Seguridad

- **Backfills segmentados**: Solo afectan registros específicos (ej: categoría D)
- **Audit logs**: Todas las actualizaciones se registran en tablas de auditoría append-only
- **Idempotencia**: Los scripts pueden ejecutarse múltiples veces sin duplicar efectos

### Tablas de Auditoría

1. **ops.identity_links_backfill_audit**: Registra creación de identity_links desde scouting_daily
2. **ops.lead_ledger_scout_backfill_audit**: Registra actualizaciones de `attributed_scout_id` en lead_ledger
3. **ops.lead_events_scout_backfill_audit**: Registra actualizaciones de `scout_id` en lead_events

### Rollback Manual

Si es necesario revertir un backfill:

1. Identificar registros afectados en las tablas de auditoría
2. Usar los campos `old_*` para restaurar valores anteriores
3. Ejecutar UPDATE manuales con WHERE clauses específicos
4. Documentar el rollback en las tablas de auditoría

**Ejemplo de rollback** (solo para emergencias, requiere aprobación):

```sql
-- Rollback de lead_ledger (ejemplo - NO ejecutar sin aprobación)
UPDATE observational.lead_ledger ll
SET 
    attributed_scout_id = audit.old_attributed_scout_id,
    attribution_rule = audit.attribution_rule_old,
    evidence_json = audit.evidence_json_old
FROM ops.lead_ledger_scout_backfill_audit audit
WHERE ll.person_key = audit.person_key
    AND audit.backfill_timestamp >= 'YYYY-MM-DD HH:MM:SS'  -- Timestamp específico
    AND audit.backfill_method = 'BACKFILL_SINGLE_SCOUT_FROM_EVENTS';
```

## Salida Final Esperada

Después de ejecutar el fix completo:

- ✅ Cobertura "satisfactorio" en scouting_daily **ya NO es 0%** (al menos identity_links > 0 y ledger scout > 0 si ledger existe)
- ✅ Categoría D reduce notablemente (propagación events → ledger)
- ✅ Categoría A: o se resuelve por mapping 1:1 o queda alertada con evidencia
- ✅ Vista de cobranza Yango con scout y buckets de calidad (`ops.v_yango_collection_with_scout`)
- ✅ Base para liquidación diaria scout lista para construir C2/C3 scout (`ops.v_scout_daily_expected_base`)

## Reportes Generados

Después de la ejecución, se genera:

- `backend/scripts/sql/SCOUT_ATTRIBUTION_AFTER_REPORT.md`: Reporte completo con métricas antes/después, warnings, y log de ejecución

## Notas Adicionales

- Los scripts están diseñados para ejecutarse en **modo batch sin interacción** (sin `input()`)
- Encoding UTF-8 para Windows
- Sin emojis en output
- Todos los scripts SQL son **idempotentes** (pueden ejecutarse múltiples veces)

## Soporte

Para problemas o preguntas:
1. Revisar logs del script
2. Ejecutar diagnóstico manual: `backend/scripts/sql/01_diagnose_scout_attribution.sql`
3. Consultar `ops.lead_ledger_backfill_audit` para auditoría
4. Revisar `ops.v_scout_attribution_conflicts` para conflictos
5. Consultar este runbook
