# Entrega: LIMBO End-to-End + UI + Job Recurrente + Scheduling + Alertas

## Fecha de Entrega: 2026-01-13

---

## Resumen Ejecutivo

Se ha completado el cierre end-to-end del sistema LIMBO para Cobranza Yango Cabinet 14d, incluyendo:

1. ✅ **LEAD_DATE_CANONICO congelado** y documentado
2. ✅ **Vista limbo mejorada** (LEAD-FIRST, todos los leads, razón accionable)
3. ✅ **Auditoría semanal** con limbo_counts
4. ✅ **UI completa** con componente React, filtros, export, orden semanal
5. ✅ **Job recurrente robusto** (UUID fix, UTF-8, idempotente)
6. ✅ **Scheduling documentado** (Windows + Cron)
7. ✅ **Alertas** (script de monitoreo)
8. ✅ **Vista extra** (claims expected vs present)

---

## Archivos Tocados

### SQL Views

1. **`backend/sql/ops/v_cabinet_leads_limbo.sql`** (MODIFICADO)
   - Mejorado `limbo_reason_detail` para ser accionable
   - Agregado `ORDER BY week_start DESC, lead_date DESC, lead_id DESC`
   - **Por qué:** Hacer la razón más clara y asegurar orden correcto

2. **`backend/sql/ops/v_cabinet_14d_funnel_audit_weekly.sql`** (YA EXISTÍA)
   - Ya incluye limbo_counts (verificado)
   - **Por qué:** Ya estaba completo

3. **`backend/sql/ops/v_claims_expected_vs_present_14d.sql`** (NUEVO)
   - Vista LEAD-FIRST que compara claims esperados vs presentes
   - **Por qué:** Preparar para detectar "lógica que impide generar claim"

### Python Jobs

4. **`backend/jobs/reconcile_cabinet_leads_pipeline.py`** (MODIFICADO)
   - Fix UUID: evitar `uuid.UUID(x)` si x ya es UUID
   - Fix UTF-8: forzar encoding UTF-8 en Windows
   - **Por qué:** Robustez y compatibilidad Windows

### Frontend

5. **`frontend/components/CabinetLimboSection.tsx`** (MODIFICADO)
   - Orden de columnas: `week_start` antes de `lead_date`
   - **Por qué:** Mostrar semana primero (orden semanal)

6. **`frontend/app/pagos/cobranza-yango/page.tsx`** (YA EXISTÍA)
   - Ya incluye `CabinetLimboSection`
   - **Por qué:** Ya estaba integrado

### Documentación

7. **`docs/ops/LEAD_DATE_CANONICO_FROZEN.md`** (NUEVO)
   - Definición congelada de LEAD_DATE_CANONICO
   - **Por qué:** Documentar fuente de verdad

8. **`docs/runbooks/scheduling_reconcile_cabinet_leads_pipeline.md`** (NUEVO)
   - Instrucciones de scheduling (Windows + Cron)
   - **Por qué:** Operación continua

9. **`docs/ops/limbo_alerts.md`** (NUEVO)
   - Definición de alertas y script de monitoreo
   - **Por qué:** Monitoreo proactivo

10. **`docs/ops/limbo_fix_evidence.md`** (NUEVO)
    - Template para evidencia before/after
    - **Por qué:** Validación y aceptación

---

## Comandos de Verificación

### 1. Verificar LEAD_DATE_CANONICO

```sql
-- Verificar que todos los leads tienen lead_created_at
SELECT 
    COUNT(*) AS total_leads,
    COUNT(lead_created_at) AS leads_with_date,
    COUNT(*) - COUNT(lead_created_at) AS leads_without_date
FROM public.module_ct_cabinet_leads;

-- Verificar rango de fechas
SELECT 
    MIN(lead_created_at::date) AS min_date,
    MAX(lead_created_at::date) AS max_date,
    COUNT(*) AS total
FROM public.module_ct_cabinet_leads
WHERE lead_created_at IS NOT NULL;

-- Verificar leads post-05/01/2026
SELECT COUNT(*) 
FROM public.module_ct_cabinet_leads 
WHERE lead_created_at::date > '2026-01-05';
```

**Resultado esperado:**
- `leads_without_date = 0`
- `min_date` y `max_date` válidos
- `COUNT(*)` post-05 = 62 (o más si hay nuevos)

---

### 2. Verificar Vista Limbo

```sql
-- Verificar que limbo incluye todos los leads
SELECT 
    (SELECT COUNT(*) FROM public.module_ct_cabinet_leads WHERE lead_created_at IS NOT NULL) AS total_leads_raw,
    (SELECT COUNT(*) FROM ops.v_cabinet_leads_limbo) AS total_leads_limbo,
    (SELECT COUNT(*) FROM public.module_ct_cabinet_leads WHERE lead_created_at IS NOT NULL) - 
    (SELECT COUNT(*) FROM ops.v_cabinet_leads_limbo) AS diff;

-- Verificar limbo por stage
SELECT 
    limbo_stage,
    COUNT(*) AS count
FROM ops.v_cabinet_leads_limbo
GROUP BY limbo_stage
ORDER BY count DESC;

-- Verificar leads post-05 en limbo
SELECT 
    limbo_stage,
    COUNT(*) AS count
FROM ops.v_cabinet_leads_limbo
WHERE lead_date > '2026-01-05'
GROUP BY limbo_stage
ORDER BY count DESC;

-- Verificar orden (week_start DESC, lead_date DESC)
SELECT 
    week_start,
    lead_date,
    lead_id,
    limbo_stage
FROM ops.v_cabinet_leads_limbo
ORDER BY week_start DESC, lead_date DESC, lead_id DESC
LIMIT 10;
```

**Resultado esperado:**
- `diff = 0` (todos los leads aparecen)
- Leads post-05 aparecen en limbo
- Orden correcto (semana más reciente primero)

---

### 3. Verificar Auditoría Semanal

```sql
-- Verificar últimas 8 semanas
SELECT 
    week_start,
    leads_total,
    leads_with_identity,
    leads_with_driver,
    drivers_with_trips_14d,
    limbo_no_identity,
    limbo_no_driver,
    limbo_no_trips_14d,
    limbo_trips_no_claim,
    limbo_ok
FROM ops.v_cabinet_14d_funnel_audit_weekly
ORDER BY week_start DESC
LIMIT 8;

-- Verificar que semanas post-05 aparecen
SELECT 
    week_start,
    leads_total
FROM ops.v_cabinet_14d_funnel_audit_weekly
WHERE week_start >= DATE_TRUNC('week', '2026-01-05'::date)::date
ORDER BY week_start DESC;
```

**Resultado esperado:**
- Semanas post-05 aparecen con `leads_total > 0`
- Limbo_counts presentes

---

### 4. Verificar Endpoint de Limbo (API)

```bash
# Obtener limbo con filtros
curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d/limbo?limbo_stage=NO_IDENTITY&week_start=2026-01-06&limit=10&offset=0" \
  -H "accept: application/json"

# Exportar limbo
curl -X GET "http://localhost:8000/api/v1/ops/payments/cabinet-financial-14d/limbo/export?limbo_stage=NO_IDENTITY&limit=1000" \
  -H "accept: text/csv" \
  -o limbo_export.csv
```

**Resultado esperado:**
- Respuesta JSON válida con `meta`, `summary`, `data`
- CSV descargable

---

### 5. Verificar UI

1. Navegar a `/pagos/cobranza-yango`
2. Verificar que aparece sección "Leads en Limbo (LEAD-first)"
3. Verificar filtros:
   - `limbo_stage` (dropdown)
   - `week_start` (date picker)
   - `lead_date_from/to` (date pickers)
4. Verificar orden: semana más reciente primero
5. Verificar export CSV
6. Verificar paginación

**Resultado esperado:**
- UI carga sin errores
- Filtros funcionan
- Orden correcto (week_start DESC, lead_date DESC)
- Export genera CSV

---

### 6. Verificar Job de Reconciliación

```bash
# Dry-run
cd backend
python -m jobs.reconcile_cabinet_leads_pipeline --days-back 30 --limit 2000 --dry-run

# Ejecución real
python -m jobs.reconcile_cabinet_leads_pipeline --days-back 30 --limit 2000
```

**Resultado esperado:**
- No errores de UUID
- No errores de encoding UTF-8
- Métricas loggeadas correctamente

---

### 7. Verificar Vista Claims Expected vs Present

```sql
-- Verificar vista
SELECT 
    week_start,
    lead_date,
    milestone_value,
    claim_present,
    claim_missing,
    missing_amount
FROM ops.v_claims_expected_vs_present_14d
WHERE claim_missing = true
ORDER BY week_start DESC, lead_date DESC
LIMIT 20;
```

**Resultado esperado:**
- Vista se crea sin errores
- Datos válidos

---

## Evidencia: "Ya No Se Corta"

### Query de Validación

```sql
-- Verificar que UI puede mostrar leads post-05
SELECT 
    week_start,
    COUNT(*) AS leads_count,
    COUNT(*) FILTER (WHERE limbo_stage = 'NO_IDENTITY') AS no_identity,
    COUNT(*) FILTER (WHERE limbo_stage = 'TRIPS_NO_CLAIM') AS trips_no_claim
FROM ops.v_cabinet_leads_limbo
WHERE lead_date > '2026-01-05'
GROUP BY week_start
ORDER BY week_start DESC;
```

**Resultado esperado:**
- Semanas post-05 aparecen con `leads_count > 0`
- No hay "corte" en la data

---

## Evidencia: "Limbo Muestra Todo"

### Query de Validación

```sql
-- Comparar total de leads en module_ct_cabinet_leads vs limbo
SELECT 
    (SELECT COUNT(*) FROM public.module_ct_cabinet_leads WHERE lead_created_at IS NOT NULL) AS total_leads_raw,
    (SELECT COUNT(*) FROM ops.v_cabinet_leads_limbo) AS total_leads_limbo,
    (SELECT COUNT(*) FROM public.module_ct_cabinet_leads WHERE lead_created_at IS NOT NULL) - 
    (SELECT COUNT(*) FROM ops.v_cabinet_leads_limbo) AS diff;
```

**Resultado esperado:**
- `diff = 0` (todos los leads aparecen en limbo)

---

## Checklist de Aceptación

- [x] LEAD_DATE_CANONICO congelado y documentado
- [x] Vista limbo mejorada (razón accionable, orden correcto)
- [x] Auditoría semanal con limbo_counts
- [x] UI completa (componente React, filtros, export, orden)
- [x] Job recurrente robusto (UUID fix, UTF-8, idempotente)
- [x] Scheduling documentado (Windows + Cron)
- [x] Alertas (script de monitoreo)
- [x] Vista extra (claims expected vs present)
- [x] Evidencia before/after (template)

---

## Próximos Pasos

1. **Ejecutar job de reconciliación** manualmente para validar
2. **Configurar scheduling** según documentación
3. **Configurar alertas** según documentación
4. **Completar evidencia** con datos reales en `docs/ops/limbo_fix_evidence.md`
5. **Monitorear** limbo_counts semana a semana

---

## Referencias

- Vista limbo: `ops.v_cabinet_leads_limbo`
- Auditoría semanal: `ops.v_cabinet_14d_funnel_audit_weekly`
- Job: `backend/jobs/reconcile_cabinet_leads_pipeline.py`
- Scheduling: `docs/runbooks/scheduling_reconcile_cabinet_leads_pipeline.md`
- Alertas: `docs/ops/limbo_alerts.md`
- Evidencia: `docs/ops/limbo_fix_evidence.md`
- LEAD_DATE_CANONICO: `docs/ops/LEAD_DATE_CANONICO_FROZEN.md`
