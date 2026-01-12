# Identity Gap & Recovery Module - Resumen Ejecutivo

## Objetivo

Reducir la brecha de "Leads sin Identidad ni Claims" de ~24% a <5% mediante un mecanismo recurrente de matching + auditoría + visibilidad UI + métricas realtime.

## Entregables Completados

### ✅ Fase A: Base de Datos / Migraciones

1. **Migration 014**: `backend/alembic/versions/014_create_identity_gap_recovery.py`
   - Tabla `ops.identity_matching_jobs` para trackear reintentos
   - Trigger `trg_identity_origin_history` para historial append-only
   - Índices optimizados

2. **Modelos Python**: 
   - `IdentityMatchingJob` en `backend/app/models/ops.py`
   - Exportado en `backend/app/models/__init__.py`

### ✅ Fase B: Views de Análisis

1. **Vista de análisis**: `backend/sql/ops/v_identity_gap_analysis.sql`
   - Clasifica leads por gap_reason: no_identity, no_origin, activity_without_identity, no_activity, resolved
   - Calcula risk_level: high, medium, low
   - Incluye trips_14d y gap_age_days

2. **Vista de alertas**: `backend/sql/ops/v_identity_gap_alerts.sql`
   - Alertas activas: over_24h_no_identity, over_7d_unresolved, activity_no_identity
   - Filtra solo leads con problemas críticos

### ✅ Fase C: Job de Matching

1. **Job de reintento**: `backend/jobs/retry_identity_matching.py`
   - Idempotente: puede ejecutarse múltiples veces sin romper
   - Usa `MatchingEngine` existente para matching
   - Crea `identity_link` y `identity_origin` cuando matchea
   - Trackea intentos en `ops.identity_matching_jobs`

2. **Runbook**: `docs/runbooks/identity_gap_recovery.md`
   - Instrucciones de ejecución manual
   - Configuración de cron para ejecución diaria
   - Verificación de freshness y troubleshooting

### ✅ Fase D: API Endpoints

1. **GET /api/v1/ops/identity-gaps**
   - Retorna análisis completo con totals, breakdown, items
   - Filtros: date_from, date_to, risk_level, gap_reason
   - Paginación: page, page_size

2. **GET /api/v1/ops/identity-gaps/alerts**
   - Retorna alertas activas
   - Ordenadas por severity y days_open

3. **Schemas**: `backend/app/schemas/identity_gap.py`
   - Tipos TypeScript en `frontend/lib/api.ts`

### ✅ Fase E: UI

1. **Sección en página cobranza-yango**: `frontend/app/pagos/cobranza-yango/page.tsx`
   - Cards con métricas: Total Leads, Unresolved, Resolved, High Risk
   - Tabla con filtros y columnas principales
   - Auto-refresh cada 60 segundos
   - Modal/sección de alertas

2. **UX**:
   - Colores: rojo (high), amarillo (medium), gris/verde (resolved)
   - Copy claro: "cada lead sin identidad puede ser plata no cobrable"

### ✅ Fase F: Documentación

1. **Mapping doc**: `docs/ops/identity_gap_mapping.md`
   - Mapeo de tablas y campos reales del repositorio

2. **Checklist de verificación**: `docs/ops/verify_identity_gap_module.md`
   - Checklist completo para verificar todos los componentes

## Archivos Creados/Modificados

### Nuevos Archivos
- `backend/alembic/versions/014_create_identity_gap_recovery.py`
- `backend/jobs/retry_identity_matching.py`
- `backend/sql/ops/v_identity_gap_analysis.sql`
- `backend/sql/ops/v_identity_gap_alerts.sql`
- `backend/app/schemas/identity_gap.py`
- `docs/ops/identity_gap_mapping.md`
- `docs/runbooks/identity_gap_recovery.md`
- `docs/ops/verify_identity_gap_module.md`
- `docs/ops/IDENTITY_GAP_RECOVERY_SUMMARY.md` (este archivo)

### Archivos Modificados
- `backend/app/models/ops.py` - Agregado `IdentityMatchingJob`
- `backend/app/models/__init__.py` - Exportado `IdentityMatchingJob`
- `backend/app/api/v1/ops.py` - Agregados endpoints de identity-gaps
- `frontend/lib/api.ts` - Agregadas funciones API
- `frontend/app/pagos/cobranza-yango/page.tsx` - Agregada sección UI

## Próximos Pasos

1. **Aplicar migration**:
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Crear vistas SQL**:
   ```bash
   psql -d tu_db -f backend/sql/ops/v_identity_gap_analysis.sql
   psql -d tu_db -f backend/sql/ops/v_identity_gap_alerts.sql
   ```

3. **Probar job manualmente**:
   ```bash
   cd backend
   python -m jobs.retry_identity_matching 20
   ```

4. **Verificar API**:
   ```bash
   curl http://localhost:8000/api/v1/ops/identity-gaps?page=1&page_size=10
   curl http://localhost:8000/api/v1/ops/identity-gaps/alerts
   ```

5. **Verificar UI**:
   - Abrir http://localhost:3000/pagos/cobranza-yango
   - Verificar que la sección "Brechas de Identidad" está visible

6. **Configurar cron** (opcional):
   - Ver `docs/runbooks/identity_gap_recovery.md` para instrucciones

## Métricas de Éxito

- **identity_unresolved_pct**: <5% (objetivo)
- **identity_recovery_rate**: >50% de leads procesados se resuelven
- **high_risk_count**: Se reduce con el tiempo
- **avg_days_open_unresolved**: <2 días

## Notas Importantes

- El módulo es **idempotente**: puede ejecutarse múltiples veces sin romper
- **No crea nuevas personas** si no hay evidencia fuerte
- **Matching** = encontrar persona existente en `canon.identity_registry`
- Todo es **append-only** para auditoría
- **No modifica C2/C3/C4** (claims/pagos/eligibilidad) - solo C0 + C1

## Soporte

- Ver `docs/ops/verify_identity_gap_module.md` para troubleshooting
- Ver `docs/runbooks/identity_gap_recovery.md` para operación
- Ver `docs/ops/identity_gap_mapping.md` para estructura de datos
