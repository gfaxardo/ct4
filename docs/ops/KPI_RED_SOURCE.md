# KPI RED SOURCE - Análisis Quirúrgico

## FASE A - IDENTIFICACIÓN DE FUENTES

### A1) KPI ROJO: "Leads sin identidad ni claims" = 203

**Frontend:**
- **Archivo:** `frontend/app/pagos/cobranza-yango/page.tsx`
- **Línea:** 559-561
- **Variable:** `funnelGap.leads_without_both`
- **Función:** `getFunnelGapMetrics()` (línea 113)

**API Client:**
- **Archivo:** `frontend/lib/api.ts`
- **Función:** `getFunnelGapMetrics()`
- **Endpoint:** `GET /api/v1/ops/payments/cabinet-financial-14d/funnel-gap`

**Backend:**
- **Archivo:** `backend/app/api/v1/ops_payments.py`
- **Función:** `get_funnel_gap_metrics()` (línea 1692)
- **Endpoint:** `GET /api/v1/ops/payments/cabinet-financial-14d/funnel-gap`

**SQL/Vista:**
- **Query SQL directa** (líneas 1718-1750)
- **Definición EXACTA de "sin identidad":**
  ```sql
  WITH leads_with_identity AS (
      SELECT DISTINCT
          COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk
      FROM public.module_ct_cabinet_leads mcl
      INNER JOIN canon.identity_links il
          ON il.source_table = 'module_ct_cabinet_leads'
          AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
  )
  ```
  
  **Condiciones:**
  - `il.source_table = 'module_ct_cabinet_leads'` (EXACTO)
  - `il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)` (lead_id unificado como TEXT)
  - Join: `INNER JOIN` → solo leads que TENGAN identity_link

**KPI "leads_without_both":**
- Calculado como: `COUNT(*) - COUNT(DISTINCT COALESCE(li.lead_source_pk, lc.lead_source_pk))`
- Representa: Leads que NO tienen identidad NI claims

---

### A2) KPI "Matched last 24h" = 93

**Frontend:**
- **Archivo:** `frontend/app/pagos/cobranza-yango/page.tsx`
- **Línea:** 819-821
- **Variable:** `identityGaps.totals.matched_last_24h`
- **Función:** `getIdentityGaps()` (línea 170)

**API Client:**
- **Archivo:** `frontend/lib/api.ts`
- **Función:** `getIdentityGaps()`
- **Endpoint:** `GET /api/v1/ops/identity/gaps`

**Backend:**
- **Archivo:** `backend/app/api/v1/ops.py`
- **Función:** `get_identity_gaps()` (línea 1017)
- **Endpoint:** `GET /api/v1/ops/identity/gaps`

**SQL/Vista:**
- **Tabla:** `ops.identity_matching_jobs`
- **Campo:** `matched_at` (timestamp)
- **Condición:** `matched_at >= NOW() - INTERVAL '24 hours'`
- **Qué significa "matched":**
  - Registro en `ops.identity_matching_jobs` con `matched_at` no nulo
  - `source_table` y `source_pk` registrados
  - **IMPORTANTE:** Esta tabla solo AUDITA matches, NO crea `canon.identity_links` automáticamente

---

## RESUMEN

**KPI ROJO:**
- Lee: `canon.identity_links` con `source_table='module_ct_cabinet_leads'` y `source_pk=COALESCE(external_id::text, id::text)`
- Condición: INNER JOIN → debe existir el link

**MATCHED LAST 24H:**
- Lee: `ops.identity_matching_jobs` con `matched_at >= NOW() - INTERVAL '24 hours'`
- **HIPÓTESIS:** El job que escribe en `ops.identity_matching_jobs` NO está escribiendo en `canon.identity_links` (o lo hace con formato diferente)
