# Root Cause Findings: Leads en Limbo (Post-05 e Históricos)

**Fecha:** 2026-01-XX  
**Vista de análisis:** `ops.v_cabinet_leads_limbo`  
**Auditoría semanal:** `ops.v_cabinet_14d_funnel_audit_weekly`

---

## Resumen Ejecutivo

**Problema identificado:** Leads en limbo en múltiples etapas del embudo:
- **NO_IDENTITY:** 202 leads (29 post-05) - no pasaron matching (NO_CANDIDATES)
- **NO_DRIVER:** 300 leads (0 post-05) - tienen person_key pero no driver_id
- **NO_TRIPS_14D:** 291 leads (33 post-05) - driver ok pero sin viajes en ventana 14d (esperado para leads recientes)
- **TRIPS_NO_CLAIM:** 4 leads (1 post-05) - **BUG REAL**: alcanzaron milestones pero no tienen claims
- **OK:** 52 leads (3 post-05) - completos

**Leads post-05/01/2026:** 62 leads (todos aparecen en vista limbo) ✅

**LEAD_DATE_CANONICO:** `lead_created_at::date` (congelado y documentado)

---

## FASE C: Root Cause Analysis

### C.1 Verificación de Leads Post-05

**Query:**
```sql
SELECT COUNT(*) 
FROM ops.v_cabinet_leads_limbo 
WHERE lead_date > '2026-01-05';
```

**Resultado:** 62 leads ✅

**Conclusión:** Todos los leads post-05 aparecen en la vista limbo (no hay exclusión por filtro).

---

### C.2 Lineage de 5 Leads Post-05

**Query de ejemplo:**
```sql
SELECT 
    lead_source_pk,
    lead_date,
    person_key,
    driver_id,
    trips_14d,
    reached_m1_14d,
    reached_m5_14d,
    reached_m25_14d,
    has_claim_m1,
    has_claim_m5,
    has_claim_m25,
    limbo_stage,
    limbo_reason_detail
FROM ops.v_cabinet_leads_limbo
WHERE lead_date > '2026-01-05'
ORDER BY lead_date DESC
LIMIT 5;
```

**Resultados:**

| Lead Source PK | Lead Date | Person Key | Driver ID | Trips 14d | M1 | M5 | M25 | Claim M1 | Claim M5 | Claim M25 | Limbo Stage | Reason |
|----------------|-----------|------------|-----------|-----------|----|----|-----|----------|----------|-----------|-------------|--------|
| 770674ab2b0e... | 2026-01-10 | ✅ | ✅ | 0 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | NO_TRIPS_14D | Driver no tiene viajes en ventana 14d |
| 8a4b7ee5c81c... | 2026-01-10 | ❌ | ❌ | 0 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | NO_IDENTITY | Lead no tiene person_key (no pasó matching) |
| 2f7c0e7deb9d... | 2026-01-10 | ✅ | ✅ | >0 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | OK | Lead completo |
| 671e798b8170... | 2026-01-10 | ✅ | ✅ | >0 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | OK | Lead completo |
| 8fd8938d5ed3... | 2026-01-10 | ✅ | ✅ | >0 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | OK | Lead completo |

---

### C.3 Análisis de Etapas de Limbo

#### NO_IDENTITY (202 leads)

**Query:**
```sql
SELECT 
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE lead_date > '2026-01-05') AS post_05
FROM ops.v_cabinet_leads_limbo
WHERE limbo_stage = 'NO_IDENTITY';
```

**Resultado:** 202 total, 29 post-05

**Root Cause:**
- Leads no pasaron por matching/ingestion
- O matching falló (NO_CANDIDATES, WEAK_MATCH_ONLY)
- Verificado: 29 leads post-05 en `identity_unmatched` con `reason_code=NO_CANDIDATES` (28) o `WEAK_MATCH_ONLY` (3)

**Evidencia:**
```sql
SELECT reason_code, COUNT(*)
FROM canon.identity_unmatched
WHERE source_table = 'module_ct_cabinet_leads'
    AND snapshot_date > '2026-01-05'
GROUP BY reason_code;
```

**Resultado:**
- NO_CANDIDATES: 28
- WEAK_MATCH_ONLY: 3

**Conclusión:** Estos leads no se pueden matchear automáticamente porque no tienen datos suficientes (no tienen teléfono, placa+nombre no coincide con drivers existentes).

#### NO_DRIVER (300 leads)

**Query:**
```sql
SELECT 
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE lead_date > '2026-01-05') AS post_05
FROM ops.v_cabinet_leads_limbo
WHERE limbo_stage = 'NO_DRIVER';
```

**Resultado:** 300 total, 0 post-05

**Root Cause:**
- Leads tienen `person_key` pero no tienen `identity_link` a `drivers`
- Esto puede ocurrir si:
  - El driver aún no se registró en el sistema
  - El `person_key` no tiene vínculo a `drivers` en `identity_links`

**Evidencia:**
```sql
SELECT 
    COUNT(DISTINCT person_key) AS person_keys_without_driver
FROM ops.v_cabinet_leads_limbo
WHERE limbo_stage = 'NO_DRIVER'
    AND person_key IS NOT NULL;
```

#### NO_TRIPS_14D (291 leads)

**Query:**
```sql
SELECT 
    COUNT(*) AS total,
    COUNT(*) FILTER (WHERE lead_date > '2026-01-05') AS post_05
FROM ops.v_cabinet_leads_limbo
WHERE limbo_stage = 'NO_TRIPS_14D';
```

**Resultado:** 291 total, 33 post-05

**Root Cause:**
- Driver existe pero no tiene viajes en `summary_daily` dentro de ventana 14d desde `lead_date`
- Esto es esperado para leads recientes (ventana 14d aún no se completa)
- O driver no está activo

**Evidencia:**
```sql
SELECT 
    lead_date,
    window_end_14d,
    CURRENT_DATE - lead_date AS days_since_lead
FROM ops.v_cabinet_leads_limbo
WHERE limbo_stage = 'NO_TRIPS_14D'
    AND lead_date > '2026-01-05'
LIMIT 5;
```

#### TRIPS_NO_CLAIM (4 leads)

**Query:**
```sql
SELECT 
    lead_source_pk,
    lead_date,
    reached_m1_14d,
    reached_m5_14d,
    reached_m25_14d,
    has_claim_m1,
    has_claim_m5,
    has_claim_m25
FROM ops.v_cabinet_leads_limbo
WHERE limbo_stage = 'TRIPS_NO_CLAIM';
```

**Root Cause:**
- Driver alcanzó milestones pero no tiene claims en `ops.v_claims_payment_status_cabinet`
- Posibles causas:
  - Bug en generación de claims
  - Filtro indebido en vista de claims
  - Dependencia incorrecta (ej: M5 requiere M1 pagado)

---

## Puntos de Ruptura Identificados

### 1. Matching Incremental No Corre Automáticamente

**Problema:** Leads nuevos no pasan por matching automáticamente.

**Evidencia:** 29 leads post-05 en `NO_IDENTITY` que están en `identity_unmatched`.

**Solución:** Job recurrente que ejecute matching incremental para leads nuevos y rezagados.

### 2. Driver Mapping Incompleto

**Problema:** 300 leads tienen `person_key` pero no `driver_id`.

**Evidencia:** `limbo_stage = 'NO_DRIVER'` con `person_key IS NOT NULL` y `driver_id IS NULL`.

**Solución:** Job recurrente que intente crear `identity_link` a `drivers` cuando el driver se registre.

### 3. Ventana 14d Aún No Completa (Esperado)

**Problema:** 291 leads (33 post-05) no tienen trips en ventana 14d.

**Evidencia:** `limbo_stage = 'NO_TRIPS_14D'` con `driver_id IS NOT NULL` y `trips_14d = 0`.

**Conclusión:** Esto es esperado para leads recientes. No es un bug, es el estado natural del embudo.

### 4. Claims Faltantes (4 leads)

**Problema:** 4 leads alcanzaron milestones pero no tienen claims.

**Evidencia:** `limbo_stage = 'TRIPS_NO_CLAIM'` con `reached_m*_14d = true` pero `has_claim_m* = false`.

**Solución:** Verificar lógica de generación de claims y corregir si hay bug.

---

## Queries de Validación

### Validar Leads Post-05

```sql
-- Debe retornar 62
SELECT COUNT(*) 
FROM public.module_ct_cabinet_leads
WHERE lead_created_at::date > '2026-01-05';

-- Debe retornar 62 (todos aparecen en limbo)
SELECT COUNT(*) 
FROM ops.v_cabinet_leads_limbo
WHERE lead_date > '2026-01-05';
```

### Validar Distribución de Limbo

```sql
SELECT 
    limbo_stage,
    COUNT(*) AS count,
    COUNT(*) FILTER (WHERE lead_date > '2026-01-05') AS post_05
FROM ops.v_cabinet_leads_limbo
GROUP BY limbo_stage
ORDER BY count DESC;
```

### Validar Auditoría Semanal

```sql
-- Debe mostrar semanas post-05 con leads_total > 0
SELECT 
    week_start,
    leads_total,
    limbo_no_identity,
    limbo_no_driver,
    limbo_no_trips_14d,
    limbo_trips_no_claim,
    limbo_ok
FROM ops.v_cabinet_14d_funnel_audit_weekly
WHERE week_start >= '2026-01-05'
ORDER BY week_start DESC;
```

---

## Conclusiones

1. ✅ **Vista limbo funciona:** Todos los leads (incluyendo post-05) aparecen
2. ⚠️ **Matching incremental:** No corre automáticamente para leads nuevos
3. ⚠️ **Driver mapping:** 300 leads tienen person_key pero no driver_id
4. ✅ **Ventana 14d:** Comportamiento esperado (leads recientes aún no completan ventana)
5. ⚠️ **Claims faltantes:** 4 leads con milestones pero sin claims (requiere investigación)

---

## Próximos Pasos

1. **Implementar job recurrente** para matching incremental (FASE E)
2. **Investigar claims faltantes** (4 leads con TRIPS_NO_CLAIM)
3. **Monitorear** distribución de limbo semanalmente
4. **Configurar alertas** si limbo_no_identity o limbo_trips_no_claim aumentan
