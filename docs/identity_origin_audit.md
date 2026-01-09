# Runbook: Auditoría de Origen Canónico

## Objetivo

Este módulo detecta y gestiona violaciones del contrato canónico de origen sin afectar claims (C3) ni pagos (C4). Solo opera sobre C0 (Identidad) y C1 (Funnel).

## Contrato Canónico de Origen

**REGLA FUNDAMENTAL**: Ningún `person_key` puede existir sin un origen válido.

### Orígenes Válidos

1. **cabinet_lead**: Registro desde `module_ct_cabinet_leads`
2. **scout_registration**: Registro desde `module_ct_scouting_daily`
3. **migration**: Registro desde `module_ct_migrations`
4. **legacy_external**: Driver existente antes del sistema de leads (explícito y marcado)

### Prioridad de Orígenes

Cuando una persona tiene múltiples orígenes:
1. `cabinet_lead` > `scout_registration` > `migration` > `legacy_external`
2. Si mismo tipo: mayor `match_score` y `confidence_level`
3. Si mismo confidence: más temprano (`linked_at`)

## Tipos de Violaciones

### 1. missing_origin
**Descripción**: No existe registro en `canon.identity_origin` y no se puede inferir automáticamente.

**Acción recomendada**: `manual_review`

**Cómo resolver**:
1. Revisar `links_summary` en `v_identity_origin_audit`
2. Determinar origen manualmente desde los links disponibles
3. Crear registro en `canon.identity_origin` vía API o script

### 2. multiple_origins
**Descripción**: Hay múltiples orígenes válidos con alta confianza (>= 85).

**Acción recomendada**: `manual_review`

**Cómo resolver**:
1. Revisar `links_summary` para ver todos los orígenes
2. Aplicar prioridad: cabinet > scout > migration
3. Si conflicto fuerte, revisar evidencia y decidir manualmente
4. Actualizar `canon.identity_origin` con decisión

### 3. late_origin_link
**Descripción**: El link de driver es más temprano que el link de lead.

**Acción recomendada**: `auto_link`

**Cómo resolver**:
- Generalmente se puede resolver automáticamente
- El sistema puede crear el link faltante si hay evidencia suficiente
- Si no, marcar para revisión manual

### 4. orphan_lead
**Descripción**: Hay link de lead pero nunca se creó link de driver.

**Acción recomendada**: `auto_link`

**Cómo resolver**:
- Verificar si el driver existe en `public.drivers`
- Si existe, crear link de driver vía matching
- Si no existe, puede ser un lead que nunca se convirtió (normal)

### 5. legacy_driver_unclassified
**Descripción**: Driver existe pero no tiene origen válido y `first_seen_at` es anterior a `LEAD_SYSTEM_START_DATE`.

**Acción recomendada**: `mark_legacy`

**Cómo resolver**:
1. Verificar `first_seen_at` vs `LEAD_SYSTEM_START_DATE`
2. Confirmar que no tiene links a fuentes válidas
3. Marcar como `legacy_external` vía API: `POST /api/v1/identity/audit/origin/{person_key}/mark-legacy`

## Flujo de Conciliación

### Estados de Resolución

- `pending_review`: Pendiente de revisión
- `resolved_auto`: Resuelto automáticamente por el sistema
- `resolved_manual`: Resuelto manualmente por operación
- `marked_legacy`: Marcado explícitamente como legacy_external
- `discarded`: Descartado del sistema operativo (mantiene en BD para auditoría)

### Pasos de Conciliación

1. **Identificar violación**: Usar `v_identity_origin_audit` o `v_identity_origin_alerts`
2. **Revisar evidencia**: Ver `links_summary` y `origin_evidence`
3. **Decidir acción**: Seguir `recommended_action` o decidir manualmente
4. **Aplicar resolución**: Usar endpoints de API o scripts
5. **Verificar**: Confirmar que `violation_flag = false` después de resolver

## Endpoints de API

### Listar Auditoría
```
GET /api/v1/identity/audit/origin
Query params:
  - violation_flag: bool (opcional)
  - violation_reason: string (opcional)
  - resolution_status: string (opcional)
  - origin_tag: string (opcional)
  - skip: int (default: 0)
  - limit: int (default: 100)
```

### Detalle de Persona
```
GET /api/v1/identity/audit/origin/{person_key}
```

### Resolver Violación
```
POST /api/v1/identity/audit/origin/{person_key}/resolve
Body:
{
  "resolution_status": "resolved_manual",
  "origin_tag": "cabinet_lead",
  "origin_source_id": "external_id_123",
  "origin_confidence": 95.0,
  "notes": "Resuelto manualmente después de revisión"
}
```

### Marcar como Legacy
```
POST /api/v1/identity/audit/origin/{person_key}/mark-legacy
Body:
{
  "notes": "Driver existente antes del sistema de leads"
}
```

### Listar Alertas
```
GET /api/v1/identity/audit/alerts
Query params:
  - alert_type: string (opcional)
  - severity: string (opcional)
  - impact: string (opcional)
  - resolved_only: bool (default: false)
  - skip: int (default: 0)
  - limit: int (default: 100)
```

### Resolver Alerta
```
POST /api/v1/identity/audit/alerts/{person_key}/{alert_type}/resolve
Body:
{
  "resolved_by": "operacion@yego.com",
  "notes": "Resuelto después de revisión"
}
```

### Silenciar Alerta
```
POST /api/v1/identity/audit/alerts/{person_key}/{alert_type}/mute
Body:
{
  "muted_until": "2025-02-01T00:00:00Z",
  "notes": "Silenciada temporalmente"
}
```

### Estadísticas
```
GET /api/v1/identity/audit/stats
```

## Scripts

### Backfill de Origen
```bash
# Dry run (solo muestra qué haría)
python backend/scripts/backfill_identity_origin.py

# Ejecutar cambios
python backend/scripts/backfill_identity_origin.py --execute

# Con tamaño de lote personalizado
python backend/scripts/backfill_identity_origin.py --execute --batch-size 50
```

## Configuración

### LEAD_SYSTEM_START_DATE

Variable de entorno que define la fecha de arranque del pipeline de leads.

**Ubicación**: `backend/app/config.py`

**Default**: `2024-01-01`

**Uso**: Drivers con `first_seen_at` anterior a esta fecha sin origen válido se clasifican como `legacy_external`.

**Configurar**:
```bash
export LEAD_SYSTEM_START_DATE=2024-01-01
```

## Exclusiones de Vistas de Negocio

Las vistas de negocio (claims, pagos, exports) deben **EXCLUIR**:
- `resolution_status = 'discarded'`
- `resolution_status = 'marked_legacy'` (salvo módulos de auditoría)

Esto garantiza que los datos legacy o descartados no afecten el negocio operativo.

## Monitoreo

### KPIs a Monitorear

1. **Total de violaciones**: `violation_flag = true`
2. **Violaciones por razón**: Distribución de `violation_reason`
3. **Alertas por severidad**: `high`, `medium`, `low`
4. **Tasa de resolución**: `resolved_auto` + `resolved_manual` vs `pending_review`
5. **Tiempo promedio de resolución**: `resolved_at - first_detected_at`

### Alertas Críticas

- **Alta severidad**: Afectan export/collection - resolver inmediatamente
- **Media severidad**: Afectan reporting - resolver en 24-48 horas
- **Baja severidad**: Solo calidad de datos - resolver cuando sea posible

## Troubleshooting

### Persona sin origen determinado

1. Verificar que tiene links en `identity_links`
2. Revisar `links_summary` en `v_identity_origin_audit`
3. Si no tiene links válidos, puede ser legacy o requiere creación manual

### Conflicto de múltiples orígenes

1. Revisar `origin_evidence` para ver todos los candidatos
2. Aplicar reglas de prioridad manualmente
3. Si no hay claridad, marcar para revisión de dirección

### Legacy mal clasificado

1. Verificar `first_seen_at` vs `LEAD_SYSTEM_START_DATE`
2. Confirmar ausencia de links válidos
3. Si tiene links válidos, corregir origen manualmente

## Contacto

Para dudas o problemas con el módulo de auditoría:
- Revisar este runbook
- Consultar código en `backend/app/services/origin_determination.py`
- Revisar vistas SQL en `backend/sql/ops/v_identity_origin_audit.sql`

