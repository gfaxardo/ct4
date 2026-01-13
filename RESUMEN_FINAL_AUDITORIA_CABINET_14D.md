# Resumen Final: Auditoría Semanal Cobranza 14d - Leads Post-05/01/2026

**Fecha:** 2026-01-XX  
**Estado:** ✅ Root Cause Identificado | ⏳ Fix Pendiente de Ejecución

---

## ✅ Completado

### 1. Vista de Auditoría Semanal
- **Archivo:** `backend/sql/ops/v_cabinet_14d_funnel_audit_weekly.sql`
- **Estado:** ✅ Instalada y funcionando
- **Propósito:** Auditoría semanal del embudo completo por `lead_date`

### 2. Scripts de Diagnóstico y Fix
- **Diagnóstico:** `backend/scripts/diagnose_post_05_leads.py` ✅
- **Fix:** `backend/scripts/fix_post_05_leads_matching.py` ✅
- **Instalación y prueba:** `backend/scripts/install_and_test_audit_weekly.py` ✅

### 3. Orden Semanal en UI
- **Vista actualizada:** `ops.v_cabinet_financial_14d` (agregado `week_start`)
- **Endpoint actualizado:** `GET /api/v1/ops/payments/cabinet-financial-14d`
- **Orden:** `week_start DESC, lead_date DESC, driver_id`

### 4. Documentación
- **Hallazgos:** `docs/ops/cabinet_14d_funnel_audit_findings.md` ✅
- **Resumen:** `RESUMEN_AUDITORIA_CABINET_14D_WEEKLY.md` ✅

---

## 🔍 Root Cause Identificado

**Problema:** C2 - Leads post-05/01/2026 están en `lead_events` pero NO tienen `person_key`

**Evidencia:**
- ✅ 62 leads post-05 en `module_ct_cabinet_leads` (rango: 2026-01-06 a 2026-01-10)
- ✅ 62 events en `lead_events` (todos están ahí)
- ❌ Solo 33 con `person_key` (53.2%), 29 sin `person_key` (46.8%)
- ❌ Solo 31 con `identity_links` (50%)

**Causa:** El job incremental de matching no se ejecutó para estos leads o falló.

---

## ⏳ Acción Requerida

### Ejecutar Job de Matching

**Opción 1: Script Python**
```bash
python backend/scripts/fix_post_05_leads_matching.py
```

**Opción 2: API Directa**
```bash
curl -X POST "http://localhost:8000/api/v1/identity/run" \
  -H "Content-Type: application/json" \
  -d '{
    "source_tables": ["module_ct_cabinet_leads"],
    "scope_date_from": "2026-01-06",
    "scope_date_to": "2026-01-10",
    "incremental": true
  }'
```

**Opción 3: Desde código Python**
```python
from app.services.ingestion import IngestionService
from datetime import date

service = IngestionService(db)
service.run_ingestion(
    source_tables=['module_ct_cabinet_leads'],
    scope_date_from=date(2026, 1, 6),
    scope_date_to=date(2026, 1, 10),
    incremental=True
)
```

### Verificación Post-Fix

```bash
python backend/scripts/diagnose_post_05_leads.py
```

**Resultado esperado:**
- 62 leads con `person_key` (100%)
- 62 leads con `identity_links` (100%)

---

## 📊 Resultados de Auditoría

### Semana 2026-01-05 (Problema Identificado)

| Métrica | Valor | % |
|---------|-------|---|
| Leads Total | 64 | 100% |
| Con Identity | 31 | 48.4% |
| Con Driver | 31 | 48.4% |
| Con Trips 14d | 31 | 48.4% |
| Reached M1 | 0 | 0% |
| Reached M5 | 0 | 0% |
| Reached M25 | 0 | 0% |

**Gap identificado:** Solo 48.4% de leads tienen identity (debería ser ~100%)

### Comparación con Semanas Anteriores

| Semana | Leads | Con Identity | % |
|--------|-------|--------------|---|
| 2026-01-05 | 64 | 31 | 48.4% ❌ |
| 2025-12-29 | 8 | 7 | 87.5% ✅ |
| 2025-12-22 | 60 | 24 | 40.0% ❌ |
| 2025-12-15 | 86 | 70 | 81.4% ✅ |

**Observación:** La semana 2025-12-22 también tiene bajo porcentaje (40%), sugiere problema intermitente.

---

## 📁 Archivos Creados/Modificados

### Nuevos
- `backend/sql/ops/v_cabinet_14d_funnel_audit_weekly.sql`
- `backend/scripts/test_cabinet_14d_audit_weekly.py`
- `backend/scripts/install_and_test_audit_weekly.py`
- `backend/scripts/diagnose_post_05_leads.py`
- `backend/scripts/fix_post_05_leads_matching.py`
- `docs/ops/cabinet_14d_funnel_audit_findings.md`
- `RESUMEN_AUDITORIA_CABINET_14D_WEEKLY.md`
- `RESUMEN_FINAL_AUDITORIA_CABINET_14D.md`

### Modificados
- `backend/sql/ops/v_cabinet_financial_14d.sql` (agregado `week_start`)
- `backend/app/api/v1/ops_payments.py` (orden semanal)

---

## 🔄 Próximos Pasos

1. **EJECUTAR:** Job de matching para leads post-05 (ver sección "Acción Requerida")
2. **VERIFICAR:** Ejecutar script de diagnóstico post-fix
3. **MONITOREAR:** Revisar auditoría semanal en semanas siguientes
4. **PREVENIR:** Configurar job automático de matching para leads nuevos

---

## 📝 Notas Técnicas

### Estructura del Flujo

```
module_ct_cabinet_leads (lead_created_at)
    ↓ populate_events_from_cabinet
observational.lead_events (event_date, person_key=NULL)
    ↓ run_ingestion (matching)
canon.identity_links (person_key, source_pk)
    ↓
observational.v_conversion_metrics (lead_date, driver_id)
    ↓
ops.v_cabinet_financial_14d (lead_date, driver_id, milestones, claims)
    ↓
ops.v_cabinet_14d_funnel_audit_weekly (week_start, embudo completo)
```

### Punto de Ruptura

**Identificado:** Entre `lead_events` y `identity_links`
- Los leads están en `lead_events` ✅
- Pero NO tienen `person_key` ❌
- Por lo tanto, NO tienen `identity_links` ❌

**Solución:** Ejecutar `run_ingestion` para crear `identity_links` y `person_key`.

---

## ✅ Checklist Final

- [x] Vista de auditoría creada e instalada
- [x] Scripts de diagnóstico y fix creados
- [x] Orden semanal aplicado en UI
- [x] Root cause identificado (C2)
- [x] Documentación completada
- [ ] **EJECUTAR:** Job de matching para leads post-05
- [ ] **VERIFICAR:** Resultados post-fix
- [ ] **MONITOREAR:** Semanas siguientes

---

**Estado:** Listo para ejecutar fix. El root cause está identificado y los scripts están listos.
