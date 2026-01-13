# Runbook: Limpieza de Drivers Huérfanos (Orphans)

## Objetivo

Eliminar definitivamente el concepto de "drivers fantasma" en CT4 Identity System sin perder auditabilidad. Un driver NO puede existir operativamente si no proviene de un lead (cabinet, scouting, migration).

## Arquitectura

### Estados de Drivers Huérfanos

Un driver sin lead debe caer en uno de estos estados:

1. **REPARADO** (`resolved_relinked`): Se creó el link faltante si hay evidencia / lead_events
2. **QUARANTINED** (`quarantined`): Huérfano sin evidencia; excluido de funnel/claims/pagos; visible en UI para revisión
3. **PURGED** (`purged`): Eliminado después de revisión manual (futuro)

### Tabla de Cuarentena

```sql
canon.driver_orphan_quarantine
```

- **driver_id** (PK): ID del driver huérfano
- **person_key** (FK, nullable): Person key asociado
- **detected_at**: Fecha de detección
- **detected_reason**: Razón (no_lead_no_events, no_lead_has_events_repair_failed, legacy_driver_without_origin, manual_detection)
- **creation_rule**: Regla que creó el driver (RT_PHONE_EXACT, R2_LICENSE_EXACT, driver_direct)
- **evidence_json**: JSONB con evidencia del caso
- **status**: quarantined | resolved_relinked | resolved_created_lead | purged
- **resolved_at**: Fecha de resolución (si aplica)
- **resolution_notes**: Notas de resolución

## Flujo de Trabajo

### 1. Detección Automática

El script `backend/scripts/fix_drivers_without_leads.py` detecta drivers sin leads:

```bash
# Dry-run (recomendado primero)
python backend/scripts/fix_drivers_without_leads.py

# Ejecutar corrección
python backend/scripts/fix_drivers_without_leads.py --execute
```

### 2. Clasificación

Para cada driver sin lead:

#### Caso A: Tiene lead_events
- **Acción**: Crear links faltantes desde lead_events
- **Resultado**: Marcar como `resolved_relinked` en quarantine
- **Audit**: Se crea registro en quarantine con evidencia

#### Caso B: No tiene lead_events
- **Acción**: Enviar a cuarentena
- **Resultado**: Marcar como `quarantined` en quarantine
- **Audit**: Se crea registro en quarantine con evidencia mínima

### 3. Exclusión Operativa

Los drivers en cuarentena (`status = 'quarantined'`) son **automáticamente excluidos** de:

- ✅ Vista `ops.v_cabinet_funnel_status` (C1 - Funnel)
- ✅ Vistas de claims (C2/C3/C4)
- ✅ Cálculos de pagos
- ✅ Reportes operativos

**Mantienen visibilidad** en:
- ✅ Vista `ops.v_driver_orphans` (para UI)
- ✅ Tabla `canon.driver_orphan_quarantine` (audit)

## Scripts

### Script Principal: `fix_drivers_without_leads.py`

**Ubicación**: `backend/scripts/fix_drivers_without_leads.py`

**Modo de Uso**:
```bash
# Dry-run (por defecto)
python backend/scripts/fix_drivers_without_leads.py

# Ejecutar cambios
python backend/scripts/fix_drivers_without_leads.py --execute

# Limitar número de drivers a procesar
python backend/scripts/fix_drivers_without_leads.py --limit 100

# Especificar directorio de salida para reportes
python backend/scripts/fix_drivers_without_leads.py --output-dir ./reports
```

**Salidas**:
- Reporte JSON: `orphans_report_YYYYMMDD_HHMMSS.json`
- Reporte CSV: `orphans_report_YYYYMMDD_HHMMSS.csv`

**Reporte JSON incluye**:
```json
{
  "timestamp": "20250122_143022",
  "dry_run": false,
  "stats": {
    "processed": 886,
    "with_events": 872,
    "without_events": 14,
    "links_created": 125,
    "resolved_relinked": 850,
    "quarantined": 36,
    "errors": 0
  },
  "drivers": [...]
}
```

## Endpoints API

### GET `/api/v1/identity/orphans`

Lista drivers huérfanos con paginación y filtros.

**Parámetros**:
- `page` (int, default: 1): Número de página
- `page_size` (int, default: 50, max: 500): Tamaño de página
- `status` (string, opcional): Filtrar por status (quarantined, resolved_relinked, resolved_created_lead, purged)
- `detected_reason` (string, opcional): Filtrar por razón
- `driver_id` (string, opcional): Buscar por driver_id exacto

**Respuesta**:
```json
{
  "orphans": [...],
  "total": 886,
  "page": 1,
  "page_size": 50,
  "total_pages": 18
}
```

### GET `/api/v1/identity/orphans/metrics`

Métricas agregadas de drivers huérfanos.

**Respuesta**:
```json
{
  "total_orphans": 886,
  "by_status": {
    "quarantined": 36,
    "resolved_relinked": 850,
    "resolved_created_lead": 0,
    "purged": 0
  },
  "by_reason": {
    "no_lead_no_events": 14,
    "no_lead_has_events_repair_failed": 22,
    "legacy_driver_without_origin": 0,
    "manual_detection": 0
  },
  "quarantined": 36,
  "resolved_relinked": 850,
  "with_lead_events": 872,
  "without_lead_events": 14,
  "last_updated_at": "2025-01-22T14:30:22Z"
}
```

### POST `/api/v1/identity/orphans/run-fix`

Ejecuta el script de limpieza (requiere `ENABLE_ORPHANS_FIX=true` en variables de entorno).

**Parámetros**:
- `execute` (bool, default: false): Si true, aplica cambios. Si false, solo hace dry-run.
- `limit` (int, opcional): Limitar número de drivers a procesar
- `output_dir` (string, opcional): Directorio para guardar reportes

**Respuesta**:
```json
{
  "dry_run": false,
  "timestamp": "20250122_143022",
  "stats": {...},
  "drivers": [...],
  "report_path": "/path/to/report.json"
}
```

## Vistas SQL

### `ops.v_driver_orphans`

Vista para mostrar drivers huérfanos en la UI con información detallada.

**Campos**:
- Información básica: driver_id, person_key, detected_at, detected_reason, status
- Información adicional: primary_phone, primary_license, primary_full_name
- Conteos: driver_links_count, lead_events_count

### `ops.v_cabinet_funnel_status` (Actualizada)

**Cambio**: Excluye automáticamente drivers en cuarentena activa (`status = 'quarantined'`).

## Prevención

### Validaciones en Código

El código actualizado ya previene la creación de drivers sin leads:

1. **`IngestionService.process_drivers()`**: DEPRECATED - ya no crea links directamente
2. **`LeadAttributionService.ensure_driver_identity_link()`**: Verifica existencia de lead antes de crear link
3. **`MatchingEngine`**: Solo crea drivers cuando hay match con lead

### Tests de Integridad

**Query de verificación**:
```sql
-- Debe retornar 0 (excepto drivers en cuarentena)
SELECT COUNT(*)
FROM canon.identity_links il
WHERE il.source_table = 'drivers'
AND il.person_key NOT IN (
    SELECT DISTINCT person_key
    FROM canon.identity_links
    WHERE source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily', 'module_ct_migrations')
)
AND il.source_pk NOT IN (
    SELECT driver_id 
    FROM canon.driver_orphan_quarantine 
    WHERE status = 'quarantined'
);
```

## Proceso de Limpieza Recomendado

### Paso 1: Análisis Inicial

```bash
# Ejecutar dry-run para ver qué haría
python backend/scripts/fix_drivers_without_leads.py
```

Revisar reporte JSON y CSV generados.

### Paso 2: Ejecutar Corrección

```bash
# Ejecutar con cambios (solo si el análisis es satisfactorio)
python backend/scripts/fix_drivers_without_leads.py --execute
```

### Paso 3: Verificar Resultados

```sql
-- Verificar que no hay drivers operativos sin leads (debe ser 0)
SELECT COUNT(*)
FROM ops.v_cabinet_funnel_status
WHERE driver_id IN (
    SELECT driver_id 
    FROM canon.driver_orphan_quarantine 
    WHERE status = 'quarantined'
);
```

### Paso 4: Revisar Casos en Cuarentena

Usar UI en `Identidad > Orphans` para revisar casos en cuarentena y decidir:

- **Relink manual**: Si se encuentra evidencia adicional
- **Crear lead faltante**: Si el driver debería tener un lead
- **Marcar como purged**: Si el driver es inválido/duplicado

### Paso 5: Monitoreo Continuo

Ejecutar el script periódicamente (ej: semanal) para detectar nuevos casos:

```bash
# Cron job recomendado
0 2 * * 0 cd /path/to/backend && python scripts/fix_drivers_without_leads.py --execute
```

## Métricas de Éxito

- ✅ `drivers_without_leads operativos = 0` (excepto quarantined)
- ✅ Todos los drivers en cuarentena tienen audit trail completo
- ✅ Vista de funnel/claims excluye automáticamente drivers en cuarentena
- ✅ UI muestra métricas y lista de orphans con refresh

## Troubleshooting

### Error: "No se pudo determinar source_pk para {source_table}"

**Causa**: El lead_event no tiene suficiente información para crear el link.

**Solución**: Revisar manualmente el lead_event en `observational.lead_events` y corregir si es necesario.

### Error: "Link ya existe para {source_table}:{source_pk}"

**Causa**: El link ya existe, probablemente creado anteriormente.

**Solución**: Normal - el script omite estos casos automáticamente.

### Drivers en cuarentena aparecen en funnel/claims

**Causa**: Las vistas no se han actualizado o hay drivers con status != 'quarantined'.

**Solución**: 
1. Verificar que las vistas están actualizadas: `REFRESH MATERIALIZED VIEW ops.v_cabinet_funnel_status;` (si es materializada)
2. Verificar status en quarantine: `SELECT status, COUNT(*) FROM canon.driver_orphan_quarantine GROUP BY status;`

## Referencias

- Migración: `backend/alembic/versions/014_create_driver_orphan_quarantine.py`
- Script: `backend/scripts/fix_drivers_without_leads.py`
- Vistas: `backend/sql/ops/v_driver_orphans.sql`, `backend/sql/ops/v_cabinet_funnel_status.sql`
- Endpoints: `backend/app/api/v1/identity.py` (líneas ~1794+)
- Modelos: `backend/app/models/canon.py` (DriverOrphanQuarantine)
- Schemas: `backend/app/schemas/identity.py` (OrphanDriver, OrphansListResponse, etc.)



