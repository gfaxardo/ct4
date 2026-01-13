# Estado Actual: Limbo Cabinet Leads

**Fecha de actualización:** 2026-01-13

---

## Alertas Detectadas

### ⚠️ ALERTAS CRÍTICAS

1. **limbo_no_identity aumentó 3100% semana a semana**
   - Semana afectada: 2026-01-05
   - **Acción requerida:** Ejecutar job de reconciliación urgentemente

2. **limbo_no_identity total = 202 (umbral: 100)**
   - **Acción requerida:** Revisar matching engine y datos de entrada

3. **pct_with_identity = 50% (umbral: 80%)**
   - **Acción requerida:** Mejorar calidad de datos o matching rules

---

## Métricas Actuales

### Limbo por Stage (Global)

- **NO_DRIVER:** 300
- **NO_TRIPS_14D:** 291
- **NO_IDENTITY:** 202 ⚠️ (umbral: 100)
- **OK:** 52
- **TRIPS_NO_CLAIM:** 4

### Leads Post-05

- **Total leads post-05:** 62 ✅
- **En limbo:**
  - NO_IDENTITY: 30
  - OK: 16
  - NO_TRIPS_14D: 15
  - TRIPS_NO_CLAIM: 1

### Validación de Integridad

- **Total leads raw:** 849
- **Total limbo:** 849
- **Diff:** 0 ✅ (todos los leads aparecen)

### Auditoría Semanal (Últimas 8 Semanas)

- **Semana 2026-01-05:** leads=64, no_identity=32, no_driver=0, no_trips=15, trips_no_claim=1, ok=16
- **Semana 2025-12-29:** leads=8, no_identity=1, no_driver=0, no_trips=3, trips_no_claim=1, ok=3
- **Semana 2025-12-22:** leads=60, no_identity=36, no_driver=1, no_trips=16, trips_no_claim=0, ok=7
- **Semana 2025-12-15:** leads=86, no_identity=16, no_driver=52, no_trips=12, trips_no_claim=0, ok=6

---

## Acciones Inmediatas

1. **Ejecutar job de reconciliación:**
   ```bash
   cd backend
   python -m jobs.reconcile_cabinet_leads_pipeline --only-limbo --limit 500
   ```

2. **Revisar logs del matching engine:**
   - Verificar `canon.identity_unmatched` para ver razones
   - Revisar calidad de datos en `module_ct_cabinet_leads`

3. **Monitorear evolución:**
   - Ejecutar `python scripts/check_limbo_alerts.py` cada hora
   - Revisar `ops.v_cabinet_14d_funnel_audit_weekly` semanalmente

---

## Próxima Revisión

- **Fecha:** [Actualizar después de ejecutar job]
- **Objetivo:** Reducir `limbo_no_identity` a < 100
- **Objetivo:** Aumentar `pct_with_identity` a > 80%

---

## Referencias

- Script de validación: `backend/scripts/validate_limbo.py`
- Script de alertas: `backend/scripts/check_limbo_alerts.py`
- Job de reconciliación: `backend/jobs/reconcile_cabinet_leads_pipeline.py`
