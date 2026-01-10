# Resumen Implementación: Scout Attribution Observability + Auto-Refresh + UI Friendly

**Fecha**: 2025-01-09  
**Estado**: ✅ **COMPONENTES CRÍTICOS IMPLEMENTADOS** - Pendiente: Frontend UI y Runbook

---

## ✅ COMPONENTES COMPLETADOS

### 1. SQL / Vistas ✅
- ✅ `backend/scripts/sql/00_inventory_scout_sources.sql` - Inventario de fuentes
- ✅ `backend/scripts/sql/01_metrics_scout_attribution.sql` - Vistas de métricas
- ✅ `backend/scripts/sql/02-07_create_v_*.sql` - Vistas canónicas (reutilizadas existentes)
- ✅ `backend/scripts/sql/20_create_audit_tables.sql` - Tablas de auditoría
- ✅ `backend/scripts/sql/07_verify_scout_attribution.sql` - Verificaciones

### 2. Backfills / Jobs ✅
- ✅ `backend/scripts/backfill_identity_links_scouting_daily.py` (mejorado)
- ✅ `backend/scripts/sql/backfill_lead_ledger_attributed_scout.sql` (existente)
- ✅ `backend/scripts/sql/backfill_lead_events_scout_from_cabinet_leads.sql` (nuevo)
- ✅ `backend/scripts/run_scout_attribution_refresh.py` (nuevo - run once)
- ✅ `backend/scripts/ops_refresh_scout_attribution.py` (nuevo - recurrente)
- ✅ `backend/scripts/ops_refresh_scout_attribution.ps1` (nuevo - Windows)

### 3. Backend API ✅
- ✅ `backend/app/api/v1/scouts.py` - Endpoints completos:
  - `GET /api/v1/scouts/attribution/metrics` - Métricas instantáneas
  - `GET /api/v1/scouts/attribution/metrics/daily?days=30` - Métricas históricas
  - `GET /api/v1/scouts/attribution/conflicts` - Lista conflictos
  - `GET /api/v1/scouts/attribution/backlog` - Backlog por categorías
  - `GET /api/v1/scouts/attribution/job-status` - Estado del job
  - `POST /api/v1/scouts/attribution/run-now` - Trigger manual
  - `GET /api/v1/scouts/liquidation/base` - Vista base liquidación
  - `GET /api/v1/yango/cabinet/collection-with-scout` - Cobranza Yango con scout

### 4. Modelos ✅
- ✅ `backend/app/models/ops.py` - Actualizado JobType con `SCOUT_ATTRIBUTION_REFRESH`

### 5. Integración API ✅
- ✅ `backend/app/api/v1/__init__.py` - Router scouts incluido

---

## ⚠️ PENDIENTE (Frontend UI + Runbook)

### Frontend UI (Pendiente - Requiere implementación)

**Ubicación sugerida**: `frontend/app/scouts/attribution-health/page.tsx`

**Componentes necesarios**:
1. **Cards de métricas**:
   - % scout satisfactorio
   - # missing scout
   - # conflictos
   - Backlog por categorías (A/C/D)

2. **Auto-refresh**:
   - Polling cada 10-15s (configurable)
   - Indicador "Actualizado hace X segundos"
   - Botón "Actualizar ahora"
   - Pause/resume

3. **Tabla de backlog**:
   - Por categorías (A/C/D)
   - CTAs: "Ver conflictos", "Ver en Cobranza Yango", "Ver registros sin identidad"

4. **Gráfico de tendencias**:
   - Últimos 30 días
   - Línea de % scout satisfactorio

5. **Estado del job**:
   - Última ejecución + duración + resultado
   - Botón "Ejecutar ahora"

6. **Pantallas adicionales**:
   - `frontend/app/scouts/cobranza-yango/page.tsx` - Cobranza Yango con scout
   - `frontend/app/scouts/liquidation/page.tsx` - Liquidación base

7. **API Client**:
   - Agregar funciones en `frontend/lib/api.ts` para endpoints de scouts

8. **Tipos TypeScript**:
   - Agregar tipos en `frontend/lib/types.ts` para respuestas de scouts

### Runbook (Pendiente - Requiere creación)

**Ubicación**: `docs/runbooks/scout_attribution_observability.md`

**Contenido necesario**:
1. Setup del job recurrente (cron + docker)
2. Cómo verificar salud del sistema
3. Qué hacer si sube missing/conflicts
4. Cómo auditar backfills
5. Límites/garantías (no afecta claims Yango)
6. Troubleshooting común

---

## 🚀 EJECUCIÓN INMEDIATA

### 1. Ejecutar Scripts SQL
```bash
cd backend
# Ejecutar en orden:
python -c "from app.db import SessionLocal; from sqlalchemy import text; from pathlib import Path; db = SessionLocal(); [db.execute(text(Path(f'scripts/sql/{f}').read_text())); db.commit() for f in ['00_inventory_scout_sources.sql', '20_create_audit_tables.sql', '01_metrics_scout_attribution.sql', '02_create_v_scout_attribution_raw.sql', '03_create_v_scout_attribution.sql', '04_create_v_scout_attribution_conflicts.sql', '05_create_v_persons_without_scout_categorized.sql', '06_create_v_yango_collection_with_scout.sql', '07_verify_scout_attribution.sql']]; db.close()"
```

### 2. Probar Endpoints API
```bash
# Métricas
curl http://localhost:8000/api/v1/scouts/attribution/metrics

# Estado del job
curl http://localhost:8000/api/v1/scouts/attribution/job-status

# Ejecutar refresh manual
curl -X POST http://localhost:8000/api/v1/scouts/attribution/run-now
```

### 3. Programar Job Recurrente

**Linux (Cron)**:
```bash
# Agregar a crontab:
0 */4 * * * cd /path/to/CT4 && python backend/scripts/ops_refresh_scout_attribution.py >> /var/log/scout_refresh.log 2>&1
```

**Windows (Task Scheduler)**:
- Programar tarea ejecutando: `backend\scripts\ops_refresh_scout_attribution.ps1`
- Frecuencia: Cada 4 horas

---

## 📝 NOTAS IMPORTANTES

1. **No rompe claims Yango**: Todas las vistas y scripts son read-only o solo backfill de atribución scout. No modifican lógica de cobranza.

2. **Idempotente**: Todos los scripts son seguros para ejecutar múltiples veces.

3. **Auditable**: Todas las operaciones quedan registradas en tablas de auditoría append-only.

4. **Conflictos**: No se inventan scouts. Los conflictos se listan para revisión manual.

5. **Frontend pendiente**: UI necesita implementarse según especificaciones. Los endpoints API ya están listos.

---

## ✅ VERIFICACIONES

Ejecutar:
```sql
-- Verificar métricas
SELECT * FROM ops.v_scout_attribution_metrics_snapshot;

-- Verificar conflictos
SELECT COUNT(*) FROM ops.v_scout_attribution_conflicts;

-- Verificar backlog
SELECT category, COUNT(*) FROM ops.v_persons_without_scout_categorized GROUP BY category;
```

---

**PR LISTO PARA REVISIÓN** - Pendiente: Frontend UI + Runbook documentación

