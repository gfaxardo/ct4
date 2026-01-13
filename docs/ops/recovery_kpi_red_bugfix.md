# Recovery KPI Red Bugfix - Análisis Quirúrgico

## RESUMEN EJECUTIVO

**Problema reportado:** "Matched last 24h = 93, pero KPI rojo 'Leads sin identidad ni claims' = 203 no baja"

**Conclusión del análisis:** **NO HAY BUG**. El sistema está funcionando correctamente.

## FASE A - IDENTIFICACIÓN DE FUENTES

### KPI ROJO: "Leads sin identidad ni claims" = 203

- **Frontend:** `frontend/app/pagos/cobranza-yango/page.tsx` (línea 559-561)
- **Endpoint:** `GET /api/v1/ops/payments/cabinet-financial-14d/funnel-gap`
- **Backend:** `backend/app/api/v1/ops_payments.py`, función `get_funnel_gap_metrics()` (línea 1692)
- **SQL:** Query directa que cuenta leads SIN identity_links:
  ```sql
  WITH leads_with_identity AS (
      SELECT DISTINCT
          COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk
      FROM public.module_ct_cabinet_leads mcl
      INNER JOIN canon.identity_links il
          ON il.source_table = 'module_ct_cabinet_leads'
          AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
  )
  -- KPI rojo = COUNT(*) - COUNT(DISTINCT li.lead_source_pk)
  ```

### MATCHED LAST 24H: 93

- **Frontend:** `frontend/app/pagos/cobranza-yango/page.tsx` (línea 819-821)
- **Endpoint:** `GET /api/v1/ops/identity/gaps`
- **Backend:** `backend/app/api/v1/ops.py`, función `get_identity_gaps()` (línea 1017)
- **SQL:** 
  ```sql
  SELECT COUNT(*) FILTER (
      WHERE status = 'matched' 
      AND last_attempt_at >= NOW() - INTERVAL '24 hours'
  ) as matched_last_24h
  FROM ops.identity_matching_jobs
  ```

## FASE B - PRUEBA CONTROLADA

### B1) Análisis de 20 leads matched last 24h

**Resultado:**
- 20/20 leads tienen `identity_link` correcto
- 20/20 leads tienen `source_table = 'module_ct_cabinet_leads'` (correcto)
- 20/20 leads tienen `source_pk` que coincide con `COALESCE(external_id::text, id::text)` (correcto)
- 19/20 leads tienen `identity_origin` correcto (1 sin origin, pero no afecta el KPI rojo)
- **0/20 leads están siendo contados en el KPI rojo** (correcto)

### B2) Verificación del KPI rojo

**Conteos actuales:**
- Total leads: 849
- Leads con identidad: 646
- **Leads sin identidad: 203** (KPI rojo)
- Matched last 24h: 93
- Matched last 24h con links: 93 (100%)
- **Matched last 24h que están en KPI rojo: 0** (0%)

## CONCLUSIÓN

### El sistema está funcionando correctamente

Los 93 leads "matched last 24h" **YA ESTÁN CORRECTAMENTE LINKADOS** y **YA FUERON EXCLUIDOS** del KPI rojo. Los 203 leads que aparecen en el KPI rojo son **OTROS LEADS DIFERENTES** que aún no han sido matched.

**Evidencia:**
1. ✅ Todos los matched last 24h tienen `identity_link` con formato correcto
2. ✅ Ninguno de los matched last 24h está siendo contado en el KPI rojo
3. ✅ El job `retry_identity_matching.py` SÍ está escribiendo en `canon.identity_links` correctamente

### Posibles causas de confusión

1. **Expectativa incorrecta:** El usuario podría esperar que los 203 bajaran a 203-93=110, pero en realidad los 93 matched **YA FUERON REMOVIDOS** de los 203 antes de que se muestre el KPI.

2. **Timing/caché:** Si el usuario está viendo datos en caché, podría ver el KPI antes de que el job corriera.

3. **Diferentes conjuntos de datos:** Los 93 matched last 24h y los 203 del KPI rojo son conjuntos DISJUNTOS (no hay overlap).

## ROOT CAUSE

**NO HAY BUG**. El sistema funciona correctamente. Los matched last 24h ya tienen links y ya fueron excluidos del KPI rojo.

## RECOMENDACIONES

1. **Verificar caché:** Asegurar que el frontend/backend no esté usando datos en caché.
2. **Documentar comportamiento:** Aclarar que "matched last 24h" se refiere a leads que fueron matched EN LAS ÚLTIMAS 24H, no a leads que están EN EL KPI ROJO y fueron matched.
3. **Monitorizar tendencia:** Si el usuario espera que el KPI baje, monitorear la tendencia a lo largo de varios días para verificar que los matched sí reducen el KPI rojo en el tiempo.

## QUERIES DE VERIFICACIÓN

### Verificar KPI rojo actual
```sql
-- Usar el endpoint GET /api/v1/ops/payments/cabinet-financial-14d/funnel-gap
-- O ejecutar directamente:
WITH leads_with_identity AS (
    SELECT DISTINCT
        COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk
    FROM public.module_ct_cabinet_leads mcl
    INNER JOIN canon.identity_links il
        ON il.source_table = 'module_ct_cabinet_leads'
        AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
),
leads_with_claims AS (
    SELECT DISTINCT
        COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk
    FROM public.module_ct_cabinet_leads mcl
    INNER JOIN canon.identity_links il
        ON il.source_table = 'module_ct_cabinet_leads'
        AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
    INNER JOIN ops.v_claims_payment_status_cabinet c
        ON c.person_key = il.person_key
        AND c.driver_id IS NOT NULL
)
SELECT 
    COUNT(*) - COUNT(DISTINCT COALESCE(li.lead_source_pk, lc.lead_source_pk)) AS leads_without_both
FROM public.module_ct_cabinet_leads mcl
LEFT JOIN leads_with_identity li
    ON li.lead_source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
LEFT JOIN leads_with_claims lc
    ON lc.lead_source_pk = COALESCE(mcl.external_id::text, mcl.id::text);
```

### Verificar matched last 24h con links
```sql
SELECT COUNT(DISTINCT imj.source_id) as matched_with_links
FROM ops.identity_matching_jobs imj
INNER JOIN canon.identity_links il
    ON il.source_table = 'module_ct_cabinet_leads'
    AND il.source_pk = imj.source_id
WHERE imj.status = 'matched'
    AND imj.last_attempt_at >= NOW() - INTERVAL '24 hours';
```

### Verificar overlap (debe ser 0)
```sql
WITH matched_last_24h AS (
    SELECT DISTINCT source_id AS lead_id
    FROM ops.identity_matching_jobs
    WHERE status = 'matched'
        AND last_attempt_at >= NOW() - INTERVAL '24 hours'
),
leads_without_identity AS (
    SELECT DISTINCT
        COALESCE(mcl.external_id::text, mcl.id::text) AS lead_source_pk
    FROM public.module_ct_cabinet_leads mcl
    WHERE NOT EXISTS (
        SELECT 1
        FROM canon.identity_links il
        WHERE il.source_table = 'module_ct_cabinet_leads'
            AND il.source_pk = COALESCE(mcl.external_id::text, mcl.id::text)
    )
)
SELECT COUNT(*) as overlap
FROM matched_last_24h m
INNER JOIN leads_without_identity lwi
    ON lwi.lead_source_pk = m.lead_id;
-- Debe retornar 0
```
