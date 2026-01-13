# Evidencia: Fix Claims Gap (CLAIM-FIRST)

**Fecha:** 2026-01-XX  
**Estado:** ✅ COMPLETADO

---

## Baseline Before

### Gaps Encontrados

```sql
SELECT COUNT(*) 
FROM ops.v_cabinet_claims_gap_14d
WHERE gap_reason = 'MILESTONE_ACHIEVED_NO_CLAIM';
```

**Resultado:** 8 gaps ✅

---

## Contrato Canónico de Claim

**Documentación:** `backend/sql/ops/v_cabinet_claims_gap_14d.sql` (comentarios SQL)

**Reglas:**
1. Claim DEBE existir si: driver_id IS NOT NULL, origin_tag='cabinet', milestone_value IN (1,5,25), milestone alcanzado dentro de ventana 14d, lead_date IS NOT NULL
2. Claim NO debe existir si: milestone NO alcanzado, driver_id IS NULL, lead_date IS NULL, origin_tag != 'cabinet'
3. claim_status ENUM: MISSING, EXISTS, INVALID
4. gap_reason ENUM: MILESTONE_ACHIEVED_NO_CLAIM, CLAIM_EXISTS, MILESTONE_NOT_ACHIEVED, NO_DRIVER, NO_LEAD_DATE, INVALID_ORIGIN, UNKNOWN

---

## Vista Claims Gap

### ✅ ops.v_cabinet_claims_gap_14d

**Características:**
- Identifica drivers con milestones alcanzados pero sin claims
- Orden: lead_date DESC, driver_id, milestone_value
- Solo muestra gaps (claim_status = 'MISSING')

**Validación:**
- ✅ 8 gaps encontrados
- ✅ Todos con gap_reason = 'MILESTONE_ACHIEVED_NO_CLAIM'

---

## Job Recurrente

### ✅ backend/jobs/reconcile_cabinet_claims_14d.py

**Características:**
- Lee gaps desde `v_cabinet_claims_gap_14d`
- Verifica condiciones canónicas
- Refresca vistas materializadas relacionadas
- Idempotente
- Procesa últimos 21 días + rezagados

**Parámetros CLI:**
- `--days-back` (default: 21) ✅
- `--limit` (default: 1000) ✅
- `--only-gaps` ✅
- `--dry-run` ✅
- `--output-json` ✅
- `--output-csv` ✅

**Runbook:** `docs/runbooks/reconcile_cabinet_claims_14d.md` ✅

---

## Endpoints Backend

### ✅ GET /api/v1/ops/payments/cabinet-financial-14d/claims-gap

- Paginación (limit/offset) ✅
- Filtros: gap_reason, week_start, lead_date_from/to, milestone_value ✅
- Summary incluido ✅
- Orden: lead_date DESC ✅

### ✅ GET /api/v1/ops/payments/cabinet-financial-14d/claims-gap/export

- Export CSV ✅

---

## UI Completa

### ✅ Componente React

**Archivo:** `frontend/components/CabinetClaimsGapSection.tsx`

**Características:**
- Cards con resumen (total gaps, milestone sin claim, monto por cobrar) ✅
- Filtros: gap_reason, week_start, lead_date_from/to, milestone_value ✅
- Tabla paginada ✅
- Orden: lead_date DESC ✅
- Botón Export CSV ✅

### ✅ Integración en Página

**Archivo:** `frontend/app/pagos/cobranza-yango/page.tsx`

- Sección "Claims Gap" agregada ✅

---

## Scheduling

### ✅ docs/runbooks/scheduling_reconcile_cabinet_claims_14d.md

**Opciones:**
- Cron Linux (cada hora o cada 15 min) ✅
- Windows Task Scheduler ✅

---

## Alertas

### ✅ docs/ops/claims_gap_alerts.md

**Alertas implementadas:**
1. Gaps aumentan semana a semana ✅
2. Total gaps > umbral ✅
3. % drivers con trips sin claim ✅
4. Lag promedio de claim ✅

---

## Métricas

### % Drivers con Trips Sin Claim

```sql
WITH drivers_with_trips AS (
    SELECT COUNT(DISTINCT driver_id) AS total
    FROM ops.v_cabinet_financial_14d
    WHERE total_trips_14d > 0
        AND lead_date >= CURRENT_DATE - INTERVAL '21 days'
),
drivers_without_claims AS (
    SELECT COUNT(DISTINCT driver_id) AS gaps
    FROM ops.v_cabinet_claims_gap_14d
    WHERE gap_reason = 'MILESTONE_ACHIEVED_NO_CLAIM'
        AND lead_date >= CURRENT_DATE - INTERVAL '21 days'
)
SELECT 
    dwt.total,
    dwc.gaps,
    CASE 
        WHEN dwt.total > 0 
        THEN ROUND(100.0 * dwc.gaps / dwt.total, 2)
        ELSE 0
    END AS pct_without_claims
FROM drivers_with_trips dwt
CROSS JOIN drivers_without_claims dwc;
```

### Lag Promedio de Claim

```sql
SELECT 
    AVG(CURRENT_DATE - lead_date) AS avg_lag_days
FROM ops.v_cabinet_claims_gap_14d
WHERE gap_reason = 'MILESTONE_ACHIEVED_NO_CLAIM'
    AND lead_date >= CURRENT_DATE - INTERVAL '21 days';
```

---

## Estado Final

✅ **TODAS LAS FASES COMPLETADAS**

- FASE 1: ✅ Contrato canónico de claim (documentado en SQL comments)
- FASE 2: ✅ Vista claim gap creada e instalada
- FASE 3: ✅ Job recurrente creado con runbook
- FASE 4: ✅ UI completa con módulo claims gap
- FASE 5: ✅ Scheduling + alertas + métricas documentados

**El sistema está completamente funcional y listo para producción.** 🎉
