# Verificación: Cabinet Recovery Impact

## FASE 5 — CRITERIOS DE ACEPTACIÓN (PASS/FAIL)

Este documento contiene queries de verificación para validar que el sistema de Recovery Impact funciona correctamente.

---

## 1. Verificar que el job funciona y matchea leads

**Criterio:** Si el job corre y matchea leads, entonces:
- `identity_effective` debe subir (en la vista puente)
- `unidentified_count` debe bajar (en la vista puente)

### Query 1.1: Verificar identidad efectiva

```sql
-- Verificar leads con identidad efectiva
SELECT 
    COUNT(*) AS total_leads,
    COUNT(*) FILTER (WHERE identity_effective = true) AS with_identity,
    COUNT(*) FILTER (WHERE identity_effective = false) AS without_identity,
    ROUND(100.0 * COUNT(*) FILTER (WHERE identity_effective = true) / COUNT(*), 2) AS pct_with_identity
FROM ops.v_cabinet_lead_identity_effective;
```

### Query 1.2: Verificar impactos (antes y después del job)

```sql
-- Verificar distribución de impact_bucket
SELECT 
    impact_bucket,
    COUNT(*) AS count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS pct
FROM ops.v_cabinet_identity_recovery_impact_14d
GROUP BY impact_bucket
ORDER BY count DESC;
```

### Query 1.3: Verificar que unidentified_count baja

```sql
-- Comparar antes/después (ejecutar antes y después del job)
SELECT 
    claim_status_bucket,
    COUNT(*) AS count
FROM ops.v_cabinet_identity_recovery_impact_14d
GROUP BY claim_status_bucket
ORDER BY count DESC;
```

---

## 2. Verificar trazabilidad

**Criterio:** Debe existir trazabilidad:
- `canon.identity_links` muestra `lead_id -> person_key`
- `canon.identity_origin` tiene `origin_tag='cabinet_lead'` y `origin_source_id=lead_id`
- `ops.cabinet_lead_recovery_audit` guarda `first_recovered_at` y método

### Query 2.1: Verificar identity_links

```sql
-- Verificar que existen identity_links para leads cabinet
SELECT 
    COUNT(*) AS total_links,
    COUNT(DISTINCT source_pk) AS unique_leads,
    MIN(linked_at) AS first_link,
    MAX(linked_at) AS last_link
FROM canon.identity_links
WHERE source_table = 'module_ct_cabinet_leads';
```

### Query 2.2: Verificar identity_origin

```sql
-- Verificar que existen identity_origin para leads cabinet
SELECT 
    COUNT(*) AS total_origins,
    COUNT(DISTINCT origin_source_id) AS unique_leads,
    MIN(origin_created_at) AS first_origin,
    MAX(origin_created_at) AS last_origin
FROM canon.identity_origin
WHERE origin_tag = 'cabinet_lead';
```

### Query 2.3: Verificar recovery_audit

```sql
-- Verificar registros en audit
SELECT 
    COUNT(*) AS total_audits,
    COUNT(*) FILTER (WHERE first_recovered_at IS NOT NULL) AS with_first_recovered,
    COUNT(*) FILTER (WHERE last_recovered_at IS NOT NULL) AS with_last_recovered,
    MIN(first_recovered_at) AS first_recovery,
    MAX(last_recovered_at) AS last_recovery
FROM ops.cabinet_lead_recovery_audit;
```

### Query 2.4: Verificar coherencia (links + origin + audit)

```sql
-- Verificar que leads con identity_link también tienen origin y audit
WITH links AS (
    SELECT DISTINCT source_pk AS lead_id
    FROM canon.identity_links
    WHERE source_table = 'module_ct_cabinet_leads'
),
origins AS (
    SELECT DISTINCT origin_source_id AS lead_id
    FROM canon.identity_origin
    WHERE origin_tag = 'cabinet_lead'
),
audits AS (
    SELECT DISTINCT lead_id
    FROM ops.cabinet_lead_recovery_audit
)
SELECT 
    COUNT(*) FILTER (WHERE l.lead_id IS NOT NULL AND o.lead_id IS NOT NULL AND a.lead_id IS NOT NULL) AS all_three,
    COUNT(*) FILTER (WHERE l.lead_id IS NOT NULL AND o.lead_id IS NULL) AS link_without_origin,
    COUNT(*) FILTER (WHERE l.lead_id IS NOT NULL AND a.lead_id IS NULL) AS link_without_audit,
    COUNT(*) FILTER (WHERE o.lead_id IS NOT NULL AND a.lead_id IS NULL) AS origin_without_audit
FROM links l
LEFT JOIN origins o ON o.lead_id = l.lead_id
LEFT JOIN audits a ON a.lead_id = l.lead_id;
```

---

## 3. Verificar UI muestra cifras que cuadran

**Criterio:** UI muestra cifras que cuadran:
- "sin identidad" del bloque de impacto = `count(impact_bucket='still_unidentified')`
- Y se diferencia claramente de "recovered late"

### Query 3.1: Verificar endpoint response

```sql
-- Query equivalente al endpoint (para verificar coherencia)
SELECT 
    COUNT(*) AS total_leads,
    COUNT(*) FILTER (WHERE impact_bucket = 'still_unidentified') AS still_unidentified_count,
    COUNT(*) FILTER (WHERE impact_bucket = 'identified_but_missing_origin') AS identified_but_missing_origin_count,
    COUNT(*) FILTER (WHERE impact_bucket = 'recovered_within_14d_but_no_claim') AS recovered_within_14d_but_no_claim_count,
    COUNT(*) FILTER (WHERE impact_bucket = 'recovered_within_14d_and_claim') AS recovered_within_14d_and_claim_count,
    COUNT(*) FILTER (WHERE impact_bucket = 'recovered_late') AS recovered_late_count,
    COUNT(*) FILTER (WHERE claim_status_bucket = 'unidentified') AS unidentified_count,
    COUNT(*) FILTER (WHERE claim_status_bucket = 'identified_no_origin') AS identified_no_origin_count,
    COUNT(*) FILTER (WHERE claim_status_bucket = 'identified_origin_no_claim') AS identified_origin_no_claim_count
FROM ops.v_cabinet_identity_recovery_impact_14d;
```

### Query 3.2: Verificar diferencia entre still_unidentified y recovered_late

```sql
-- Verificar que still_unidentified y recovered_late son diferentes
SELECT 
    impact_bucket,
    COUNT(*) AS count,
    AVG(EXTRACT(EPOCH FROM (CURRENT_DATE - lead_date))) / 86400 AS avg_days_since_lead
FROM ops.v_cabinet_identity_recovery_impact_14d
WHERE impact_bucket IN ('still_unidentified', 'recovered_late')
GROUP BY impact_bucket;
```

---

## 4. Verificar que nada tocó reglas de claims/pagos

**Criterio:** Nada tocó reglas de claims/pagos. Solo conectamos recovery a precondiciones y medición.

### Query 4.1: Verificar que v_payment_calculation no cambió

```sql
-- Verificar que v_payment_calculation sigue funcionando igual
SELECT 
    COUNT(*) AS total_claims,
    COUNT(DISTINCT driver_id) AS unique_drivers,
    COUNT(DISTINCT lead_date) AS unique_lead_dates,
    MIN(lead_date) AS min_lead_date,
    MAX(lead_date) AS max_lead_date
FROM ops.v_payment_calculation
WHERE origin_tag = 'cabinet'
    AND milestone_achieved = true
    AND milestone_trips IN (1, 5, 25);
```

---

## 5. Verificar performance

### Query 5.1: Verificar que las vistas son eficientes

```sql
-- EXPLAIN ANALYZE de la vista principal
EXPLAIN ANALYZE
SELECT 
    impact_bucket,
    COUNT(*)
FROM ops.v_cabinet_identity_recovery_impact_14d
GROUP BY impact_bucket;
```

---

## 6. Checklist de Deployment

- [ ] Migración 015 ejecutada (tabla `ops.cabinet_lead_recovery_audit`)
- [ ] Vista `ops.v_cabinet_lead_identity_effective` creada
- [ ] Vista `ops.v_cabinet_identity_recovery_impact_14d` creada
- [ ] Endpoint `/api/v1/yango/cabinet/identity-recovery-impact-14d` funciona
- [ ] Job `cabinet_recovery_impact_job.py` puede ejecutarse
- [ ] Verificar que las queries de verificación pasan

---

## 7. Ejecutar Verificación Completa

```bash
# 1. Ejecutar migración
cd backend
alembic upgrade head

# 2. Crear vistas SQL
psql -d yego_integral -f backend/sql/ops/v_cabinet_lead_identity_effective.sql
psql -d yego_integral -f backend/sql/ops/v_cabinet_identity_recovery_impact_14d.sql

# 3. Ejecutar job (opcional, para poblar audit)
python -m jobs.cabinet_recovery_impact_job 1000

# 4. Probar endpoint
curl "http://localhost:8000/api/v1/yango/cabinet/identity-recovery-impact-14d?include_series=false"

# 5. Ejecutar queries de verificación (copiar desde este documento)
```

---

## 8. Problemas Comunes

### Error: "Vista ops.v_cabinet_identity_recovery_impact_14d no existe"

**Solución:** Crear las vistas SQL primero:
```bash
psql -d yego_integral -f backend/sql/ops/v_cabinet_lead_identity_effective.sql
psql -d yego_integral -f backend/sql/ops/v_cabinet_identity_recovery_impact_14d.sql
```

### Error: "Tabla ops.cabinet_lead_recovery_audit no existe"

**Solución:** Ejecutar la migración:
```bash
cd backend
alembic upgrade head
```

### El job no procesa ningún lead

**Verificar:**
1. ¿Hay leads en `ops.v_cabinet_identity_recovery_impact_14d` con `claim_status_bucket IN ('unidentified', 'identified_no_origin')`?
2. ¿Esos leads tienen `person_key_effective`? (El job solo procesa leads que ya tienen person_key)
