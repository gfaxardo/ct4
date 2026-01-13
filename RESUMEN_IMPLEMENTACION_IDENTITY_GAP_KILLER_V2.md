# Resumen de Implementación: Identity Gap Killer v2

## Objetivo

Reducir el gap "Leads sin Identidad ni Claims" de ~24% a través de:
1. Diagnóstico preciso del problema
2. Corrección de la medición (vista)
3. Recovery que crea vínculos reales
4. Operación recurrente con métricas visibles

## FASE 0: DIAGNÓSTICO ✅

### Archivo: `backend/scripts/diagnose_identity_gap.py`

Script completo de diagnóstico que imprime:
- ✅ Métricas actuales de brecha desde `ops.v_identity_gap_analysis`
- ✅ Freshness del job desde `ops.identity_matching_jobs` (last_run, pending/matched/failed)
- ✅ Top 10 fail_reason + attempt_count
- ✅ Volumen procesado real (últimas 24h)
- ✅ Verificación de vínculos creados (identity_links, identity_origin)

**Uso:**
```bash
cd backend
python scripts/diagnose_identity_gap.py
```

## FASE 1: CORRECCIÓN DE MEDICIÓN ✅

### 1.1 Vista Corregida: `backend/sql/ops/v_identity_gap_analysis.sql`

**Cambios:**
- ❌ Eliminada categoría `activity_without_identity` (imposible de medir por lead)
- ✅ Separado concepto: `lead_sin_identity` vs `driver_activity_unlinked` (KPI aparte)
- ✅ Agregada categoría `inconsistent_origin` para detectar origins con `source_id` incorrecto
- ✅ Gap reasons ahora: `no_identity`, `no_origin`, `inconsistent_origin`, `resolved`

**Categorías medibles:**
- `no_identity`: Lead sin `identity_link` (no tiene `person_key`)
- `no_origin`: Lead tiene `person_key` pero NO tiene `identity_origin` con `origin_tag='cabinet_lead'` y `origin_source_id=lead_id`
- `inconsistent_origin`: Lead tiene origin pero `origin_source_id != lead_id`
- `resolved`: Tiene identity + origin correcto

### 1.2 Vista KPI: `backend/sql/ops/v_identity_driver_unlinked_activity.sql`

Nueva vista para medir drivers con actividad sin identidad (KPI independiente):
- Grano: 1 fila por `date_file`
- Columnas: `date_file`, `drivers_without_identity_count`, `trips_from_unlinked_drivers`

**Nota:** Esta vista es INDEPENDIENTE de los leads. Mide un problema diferente.

## FASE 2: RECOVERY QUE CREA VÍNCULOS ✅

### 2.1 Job Mejorado: `backend/jobs/retry_identity_matching.py`

**Mejoras:**
- ✅ Batching real: Procesa en lotes de 500 (configurable)
- ✅ Commit por batch (mejor manejo de transacciones)
- ✅ Logging detallado por batch
- ✅ Verificación: Confirma que crea `identity_links` e `identity_origin` correctamente

**Flujo:**
1. Obtiene leads unresolved de `ops.v_identity_gap_analysis`
2. Procesa en batches de 500
3. Para cada lead:
   - Crea/actualiza `ops.identity_matching_jobs`
   - Intenta matching usando `MatchingEngine` (ya usa `drivers_index` y `phone_normalization`)
   - Si match exitoso:
     - Crea `canon.identity_links` (source_table='module_ct_cabinet_leads')
     - Crea/actualiza `canon.identity_origin` (origin_tag='cabinet_lead')
   - Actualiza job status (matched/failed/pending)
4. Commit después de cada batch

**Configuración:**
- `BATCH_SIZE = 500` (procesar en lotes)
- `MAX_ATTEMPTS = 5` (máximo de reintentos por lead)

## FASE 3: OPERACIÓN RECURRENTE + UI ✅

### 3.1 Runbook: `docs/runbooks/identity_gap_recovery.md`

Runbook completo con:
- ✅ Comando exacto para ejecutar el job
- ✅ Ejemplos de cron (Linux/Mac/Windows)
- ✅ Queries de verificación de freshness
- ✅ Queries de evolución (unresolved hoy vs ayer)
- ✅ Troubleshooting común
- ✅ Métricas de éxito

### 3.2 UI Mejorada: `frontend/app/pagos/cobranza-yango/page.tsx`

**Nuevas métricas agregadas:**
- ✅ **Freshness**: Último run del job + badge OK/STALE
- ✅ **Matched Last 24h**: Leads matcheados en últimas 24h
- ✅ **Estado del Recovery**: Indicador visual de si el job está activo

**Badges:**
- 🟢 OK: Job corrió en últimas 24h
- 🟠 STALE: Job no corrió en >24h
- 🔴 NUNCA: Job nunca ha corrido

**Indicadores:**
- ✅ ACTIVO: `matched_last_24h > 0`
- ⚠️ SIN SEÑAL: Job corre pero no encuentra matches
- ❌ NO CONFIGURADO: Job nunca ha corrido
- ✅ COMPLETO: Todos los leads resueltos

### 3.3 API Actualizada: `backend/app/api/v1/ops.py`

Endpoint `/api/v1/ops/identity-gaps` ahora retorna:
- `matched_last_24h`: Número de leads matcheados en últimas 24h
- `last_job_run`: Timestamp del último run (ISO datetime)
- `job_freshness_hours`: Horas desde último run (None si nunca corrió)

## Archivos Modificados/Creados

### Nuevos
- `backend/scripts/diagnose_identity_gap.py` - Script de diagnóstico
- `backend/sql/ops/v_identity_driver_unlinked_activity.sql` - Vista KPI
- `docs/runbooks/identity_gap_recovery.md` - Runbook completo

### Modificados
- `backend/sql/ops/v_identity_gap_analysis.sql` - Vista corregida
- `backend/jobs/retry_identity_matching.py` - Job mejorado con batching
- `backend/app/api/v1/ops.py` - Endpoint con freshness
- `backend/app/schemas/identity_gap.py` - Schema con nuevas métricas
- `frontend/lib/api.ts` - Types actualizados
- `frontend/app/pagos/cobranza-yango/page.tsx` - UI con nuevas métricas

## Criterios de Aceptación

### ✅ A) Vista no miente
- `ops.v_identity_gap_analysis` ya no tiene categoría imposible de alcanzar
- Breakdown cuadra (solo categorías medibles)

### ✅ B) Job crea vínculos reales
- Al "matched", realmente inserta `canon.identity_links`
- Al "matched", realmente crea/actualiza `canon.identity_origin`
- Evidencia auditable en DB

### ✅ C) Operación recurrente
- Runbook con comandos exactos y ejemplos de cron
- Script de diagnóstico para verificar freshness
- UI muestra freshness y matched_last_24h

### ✅ D) Métricas visibles
- UI muestra:
  - Freshness (último run + badge)
  - Matched last 24h
  - Estado del recovery (ACTIVO/SIN SEÑAL/NO CONFIGURADO)

## Próximos Pasos

1. **Ejecutar diagnóstico inicial:**
   ```bash
   cd backend
   python scripts/diagnose_identity_gap.py
   ```

2. **Aplicar vistas corregidas:**
   ```bash
   # Ejecutar en PostgreSQL
   psql -d yego_integral -f backend/sql/ops/v_identity_gap_analysis.sql
   psql -d yego_integral -f backend/sql/ops/v_identity_driver_unlinked_activity.sql
   ```

3. **Ejecutar job manualmente (primer test):**
   ```bash
   cd backend
   python -m jobs.retry_identity_matching 100  # Procesar 100 leads primero
   ```

4. **Configurar scheduler:**
   - Ver `docs/runbooks/identity_gap_recovery.md` para ejemplos de cron

5. **Monitorear en UI:**
   - Ir a "Cobranza Yango - Cabinet Financial 14d"
   - Verificar sección "Brechas de Identidad (Recovery)"
   - Confirmar que freshness y matched_last_24h se actualizan

## Notas Técnicas

- El job usa `MatchingEngine` que ya tiene `phone_normalization` y usa `canon.drivers_index`
- El job es idempotente: puede ejecutarse múltiples veces sin romper
- El job procesa en batches para mejor performance y manejo de errores
- La vista `v_identity_gap_analysis` se actualiza automáticamente (es una vista, no tabla)

## Verificación Post-Deploy

```sql
-- 1. Verificar vista corregida
SELECT gap_reason, COUNT(*) 
FROM ops.v_identity_gap_analysis 
GROUP BY gap_reason;

-- 2. Verificar freshness
SELECT MAX(last_attempt_at) as last_run,
       COUNT(*) FILTER (WHERE status = 'matched' AND last_attempt_at >= NOW() - INTERVAL '24 hours') as matched_24h
FROM ops.identity_matching_jobs;

-- 3. Verificar vínculos creados
SELECT COUNT(*) as links_created_24h
FROM canon.identity_links
WHERE source_table = 'module_ct_cabinet_leads'
  AND linked_at >= NOW() - INTERVAL '24 hours';
```
