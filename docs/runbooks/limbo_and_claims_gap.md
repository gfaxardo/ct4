# Runbook: Leads en Limbo y Claims Gap

**Última actualización:** 2024-12-19  
**Sistema:** CT4 - Cabinet 14d Auditable

---

## 1. INTRODUCCIÓN

Este runbook documenta cómo operar y mantener el sistema auditable de Cabinet 14d, específicamente:
- **Leads en Limbo (LEAD-first):** Leads que no avanzan en el embudo
- **Claims Gap (CLAIM-first):** Milestones alcanzados sin claim generado

---

## 2. ARQUITECTURA

### 2.1 Vistas SQL
- `ops.v_cabinet_leads_limbo`: Vista LEAD-first que muestra todos los leads con su etapa
- `ops.v_cabinet_claims_expected_14d`: Fuente de verdad de qué claims DEBEN existir
- `ops.v_cabinet_claims_gap_14d`: Vista CLAIM-first que identifica gaps

### 2.2 Endpoints API
- `GET /api/v1/ops/payments/cabinet-financial-14d/limbo`: Obtener leads en limbo
- `GET /api/v1/ops/payments/cabinet-financial-14d/claims-gap`: Obtener gaps de claims

### 2.3 Jobs
- `reconcile_cabinet_leads_pipeline`: Reconciliar leads en limbo (identity matching)
- `reconcile_cabinet_claims_14d`: Generar claims faltantes

### 2.4 Scripts de Validación
- `validate_limbo.py`: Validar reglas duras de limbo
- `validate_claims_gap_before_after.py`: Validar expected_amount y consistencia
- `check_limbo_alerts.py`: Verificar umbrales y generar alertas

---

## 3. ETAPAS DE LIMBO

### 3.1 NO_IDENTITY
**Descripción:** Lead no tiene `person_key` en `canon.identity_links`

**Causa:** No pasó matching de identidad

**Acción:**
1. Verificar datos RAW del lead (phone, license, plate)
2. Ejecutar matching job:
   ```bash
   python -m jobs.reconcile_cabinet_leads_pipeline --only-limbo --limit 500
   ```
3. Si persiste, revisar `canon.identity_unmatched` para ver razón

**Queries útiles:**
```sql
-- Ver lead específico
SELECT * FROM ops.v_cabinet_leads_limbo 
WHERE lead_source_pk = 'XXX' AND limbo_stage = 'NO_IDENTITY';

-- Ver unmatched para este lead
SELECT * FROM canon.identity_unmatched 
WHERE source_table = 'module_ct_cabinet_leads' AND source_pk = 'XXX';
```

### 3.2 NO_DRIVER
**Descripción:** Lead tiene `person_key` pero no tiene `driver_id`

**Causa:** `person_key` no está vinculado a `drivers` en `canon.identity_links`

**Acción:**
1. Verificar si existe driver para este `person_key`:
   ```sql
   SELECT * FROM canon.identity_links 
   WHERE person_key = 'XXX' AND source_table = 'drivers';
   ```
2. Si no existe, puede requerir:
   - Esperar job de drivers
   - Crear link manual si hay evidencia
3. Re-ejecutar matching si hay nuevos drivers:
   ```bash
   python -m jobs.reconcile_cabinet_leads_pipeline --only-limbo --limit 500
   ```

### 3.3 NO_TRIPS_14D
**Descripción:** Lead tiene `driver_id` pero `trips_14d = 0`

**Causa:** Driver no completó viajes en ventana 14d desde `lead_date`

**Acción:**
- **NO ES ERROR:** Es realidad operativa
- Solo monitorear (no se puede "arreglar")
- Verificar `public.summary_daily` para confirmar:
  ```sql
  SELECT * FROM public.summary_daily 
  WHERE driver_id = 'XXX' 
    AND to_date(date_file, 'DD-MM-YYYY') >= 'YYYY-MM-DD'
    AND to_date(date_file, 'DD-MM-YYYY') < 'YYYY-MM-DD'::date + INTERVAL '14 days';
  ```

### 3.4 TRIPS_NO_CLAIM
**Descripción:** Driver alcanzó milestone pero no tiene claim generado

**Causa:** Claims generator no creó claim esperado

**Acción:**
1. Verificar milestone alcanzado:
   ```sql
   SELECT * FROM ops.v_cabinet_leads_limbo 
   WHERE lead_source_pk = 'XXX' 
     AND (reached_m1_14d = true OR reached_m5_14d = true OR reached_m25_14d = true);
   ```
2. Ejecutar job de reconciliación de claims:
   ```bash
   python -m jobs.reconcile_cabinet_claims_14d --days-back 21 --limit 1000
   ```
3. Verificar que claim se generó:
   ```sql
   SELECT * FROM canon.claims_yango_cabinet_14d 
   WHERE person_key::text = 'XXX' 
     AND lead_date = 'YYYY-MM-DD' 
     AND milestone IN (1, 5, 25);
   ```

### 3.5 OK
**Descripción:** Lead completo (tiene identity, driver, trips y claims)

**Acción:** Ninguna (estado deseado)

---

## 4. CLAIMS GAP

### 4.1 Interpretación de gap_reason

#### CLAIM_NOT_GENERATED
**Descripción:** Milestone alcanzado pero claim no existe en `canon.claims_yango_cabinet_14d`

**Acción:**
1. Ejecutar job de reconciliación:
   ```bash
   python -m jobs.reconcile_cabinet_claims_14d --only-gaps --limit 1000
   ```
2. Verificar que claim se generó

#### NO_IDENTITY
**Descripción:** `person_key IS NULL`

**Acción:** Misma que NO_IDENTITY en limbo (ver sección 3.1)

#### NO_DRIVER
**Descripción:** `driver_id IS NULL`

**Acción:** Misma que NO_DRIVER en limbo (ver sección 3.2)

#### INSUFFICIENT_TRIPS
**Descripción:** `trips_in_window < milestone`

**Acción:** NO ES ERROR (es realidad operativa)

#### OK
**Descripción:** Claim existe

**Acción:** Ninguna (estado deseado)

---

## 5. EJECUCIÓN MANUAL DE JOBS

### 5.1 Reconciliar Leads en Limbo

```bash
# Procesar solo leads en limbo (últimos 30 días)
python -m jobs.reconcile_cabinet_leads_pipeline --only-limbo --limit 500

# Procesar leads recientes y limbo
python -m jobs.reconcile_cabinet_leads_pipeline --days-back 30 --limit 2000

# Dry-run (solo mostrar qué se procesaría)
python -m jobs.reconcile_cabinet_leads_pipeline --only-limbo --dry-run
```

**Parámetros:**
- `--only-limbo`: Solo procesar leads en limbo (NO_IDENTITY, NO_DRIVER, TRIPS_NO_CLAIM)
- `--days-back`: Días hacia atrás para leads recientes (default: 30)
- `--limit`: Límite de leads a procesar (default: 2000)
- `--dry-run`: Modo dry-run (no ejecuta ingestion)

### 5.2 Reconciliar Claims Gap

```bash
# Procesar gaps (últimos 21 días)
python -m jobs.reconcile_cabinet_claims_14d --days-back 21 --limit 1000

# Solo gaps (claim_status=CLAIM_NOT_GENERATED)
python -m jobs.reconcile_cabinet_claims_14d --only-gaps --limit 1000

# Solo milestone M1
python -m jobs.reconcile_cabinet_claims_14d --only-milestone 1 --limit 500

# Dry-run
python -m jobs.reconcile_cabinet_claims_14d --only-gaps --dry-run
```

**Parámetros:**
- `--days-back`: Días hacia atrás (default: 21)
- `--limit`: Límite de gaps a procesar (default: 1000)
- `--only-gaps`: Solo procesar gaps (claim_status=CLAIM_NOT_GENERATED)
- `--only-milestone`: Solo procesar un milestone (1, 5, o 25)
- `--week-start`: Filtrar por semana (YYYY-MM-DD)
- `--dry-run`: Modo dry-run

---

## 6. VALIDACIÓN

### 6.1 Validar Limbo

```bash
# Validación completa
python scripts/validate_limbo.py

# Solo validar reglas duras
python scripts/validate_limbo.py --check-rules-only

# Filtrar por etapa
python scripts/validate_limbo.py --stage NO_IDENTITY

# Guardar resultados
python scripts/validate_limbo.py --output-json results/limbo_validation.json
```

**Qué valida:**
- Regla dura: `trips_14d` debe ser 0 cuando `driver_id IS NULL`
- Regla dura: `TRIPS_NO_CLAIM` solo con condiciones válidas
- Consistencia de `limbo_stage` con datos subyacentes

### 6.2 Validar Claims Gap

```bash
# Validación completa
python scripts/validate_claims_gap_before_after.py

# Filtrar por gap_reason
python scripts/validate_claims_gap_before_after.py --gap-reason CLAIM_NOT_GENERATED

# Guardar resultados
python scripts/validate_claims_gap_before_after.py --output-json results/claims_gap_validation.json
```

**Qué valida:**
- `expected_amount` siempre tiene valor cuando `claim_expected=true`
- Endpoint funciona (no error 500)
- Resumen por `gap_reason` y `milestone_value`

### 6.3 Verificar Alertas

```bash
# Verificar alertas con umbrales por defecto
python scripts/check_limbo_alerts.py

# Umbrales personalizados
python scripts/check_limbo_alerts.py --threshold-no-identity 200 --threshold-pct-identity 75

# Guardar resultados
python scripts/check_limbo_alerts.py --output-json results/limbo_alerts.json
```

**Umbrales por defecto:**
- `limbo_no_identity` > 100 → Alerta
- `pct_with_identity` < 80% → Alerta
- `TRIPS_NO_CLAIM` > 0 por 3 días → Alerta

---

## 7. QUERIES DE AUDITORÍA

### 7.1 Auditoría de un Lead Específico

```sql
-- Ver estado completo de un lead
SELECT 
    lead_id,
    lead_source_pk,
    lead_date,
    person_key,
    driver_id,
    trips_14d,
    limbo_stage,
    limbo_reason_detail
FROM ops.v_cabinet_leads_limbo
WHERE lead_source_pk = 'XXX';

-- Ver identity_links del lead
SELECT * FROM canon.identity_links 
WHERE source_table = 'module_ct_cabinet_leads' AND source_pk = 'XXX';

-- Ver unmatched del lead
SELECT * FROM canon.identity_unmatched 
WHERE source_table = 'module_ct_cabinet_leads' AND source_pk = 'XXX';

-- Ver claims del driver
SELECT * FROM canon.claims_yango_cabinet_14d 
WHERE person_key::text = 'XXX' OR driver_id = 'XXX';
```

### 7.2 Auditoría de Claims Gap

```sql
-- Ver gaps de un driver específico
SELECT 
    lead_id,
    lead_source_pk,
    driver_id,
    milestone_value,
    trips_14d,
    expected_amount,
    gap_reason,
    claim_status
FROM ops.v_cabinet_claims_gap_14d
WHERE driver_id = 'XXX';

-- Ver claims esperados vs existentes
SELECT 
    ec.lead_source_pk,
    ec.milestone,
    ec.claim_expected,
    ec.amount_expected,
    (exc.person_key_uuid IS NOT NULL) AS claim_exists
FROM ops.v_cabinet_claims_expected_14d ec
LEFT JOIN canon.claims_yango_cabinet_14d exc
    ON exc.person_key::text = ec.person_key
    AND exc.lead_date = ec.lead_date_canonico
    AND exc.milestone = ec.milestone
WHERE ec.driver_id = 'XXX';
```

---

## 8. TROUBLESHOOTING

### 8.1 Error 500 en Claims Gap

**Síntoma:** Endpoint `/cabinet-financial-14d/claims-gap` retorna 500

**Causa:** Columna `expected_amount` no existe en vista

**Solución:**
1. Verificar migración desplegada:
   ```bash
   cd backend
   alembic current
   alembic upgrade head
   ```
2. Verificar vista:
   ```sql
   SELECT column_name FROM information_schema.columns 
   WHERE table_schema = 'ops' 
     AND table_name = 'v_cabinet_claims_gap_14d' 
     AND column_name = 'expected_amount';
   ```
3. Si no existe, ejecutar migración `019_fix_claims_gap_expected_amount`

### 8.2 Limbo NO_IDENTITY crece constantemente

**Síntoma:** `limbo_no_identity` aumenta día a día

**Causa:** Matching job no está corriendo o fallando

**Solución:**
1. Verificar que scheduler está corriendo
2. Ejecutar matching manual:
   ```bash
   python -m jobs.reconcile_cabinet_leads_pipeline --only-limbo --limit 500
   ```
3. Revisar logs del job
4. Verificar datos RAW (phone, license, plate disponibles)

### 8.3 TRIPS_NO_CLAIM persistente

**Síntoma:** `TRIPS_NO_CLAIM` > 0 por varios días

**Causa:** Claims generator no está corriendo o fallando

**Solución:**
1. Ejecutar job de reconciliación:
   ```bash
   python -m jobs.reconcile_cabinet_claims_14d --only-gaps --limit 1000
   ```
2. Verificar que claims se generaron:
   ```sql
   SELECT COUNT(*) FROM canon.claims_yango_cabinet_14d 
   WHERE status = 'generated' AND generated_at >= NOW() - INTERVAL '1 day';
   ```
3. Revisar logs del job

---

## 9. MÉTRICAS Y MONITOREO

### 9.1 Métricas Clave

- **Total leads:** `COUNT(*) FROM ops.v_cabinet_leads_limbo`
- **% con identity:** `100.0 * COUNT(*) FILTER (WHERE person_key IS NOT NULL) / COUNT(*)`
- **TRIPS_NO_CLAIM:** `COUNT(*) FILTER (WHERE limbo_stage = 'TRIPS_NO_CLAIM')`
- **Gaps de claims:** `COUNT(*) FROM ops.v_cabinet_claims_gap_14d WHERE gap_reason = 'CLAIM_NOT_GENERATED'`

### 9.2 Alertas Recomendadas

- `limbo_no_identity` > 100 → Revisar matching job
- `pct_with_identity` < 80% → Revisar calidad de datos RAW
- `TRIPS_NO_CLAIM` > 0 por 3 días → Revisar claims generator

---

## 10. CONTACTO Y SOPORTE

- **Documentación:** `docs/ops/`
- **Scripts:** `backend/scripts/`
- **Jobs:** `backend/jobs/`
- **Vistas SQL:** `backend/sql/ops/`

---

**NOTA:** Este runbook es un documento vivo. Actualizar cuando haya cambios en el sistema.
