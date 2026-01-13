# Resultado de Ejecución de Jobs de Reconciliación

**Fecha:** 2024-12-19  
**Sistema:** CT4 - Cabinet 14d Auditable

---

## JOBS EJECUTADOS

### 1. reconcile_cabinet_claims_14d
**Comando:** `python -m jobs.reconcile_cabinet_claims_14d --only-gaps --limit 100`

**Propósito:** Generar claims faltantes cuando milestones fueron alcanzados

**Resultado:** Verificar salida del comando

### 2. reconcile_cabinet_leads_pipeline
**Comando:** `python -m jobs.reconcile_cabinet_leads_pipeline --only-limbo --limit 200`

**Propósito:** Reconciliar leads en limbo (identity matching)

**Resultado:** Verificar salida del comando

---

## VALIDACIÓN POST-EJECUCIÓN

### 3. Verificación de Alertas
**Comando:** `python scripts/check_limbo_alerts.py`

**Resultado:** Verificar si alertas se redujeron

### 4. Validación de Claims Gap
**Comando:** `python scripts/validate_claims_gap_before_after.py`

**Resultado:** Verificar si gaps se redujeron

---

## MÉTRICAS ANTES vs DESPUÉS

### Antes de Ejecutar Jobs
- `limbo_no_identity`: 179
- `pct_with_identity`: 78.92%
- `TRIPS_NO_CLAIM`: 5
- `CLAIM_NOT_GENERATED`: 89 gaps

### Después de Ejecutar Jobs
- Verificar métricas en salida de `check_limbo_alerts.py`

---

**NOTA:** Revisar la salida de cada comando para verificar el impacto de los jobs.
