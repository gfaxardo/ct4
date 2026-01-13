# Resumen: Auditoría Semanal Cobranza 14d - Leads Post-05/01/2026

**Fecha:** [FECHA]  
**Objetivo:** Identificar y corregir el problema de leads post-05/01/2026 que quedan en limbo en el sistema de Cobranza Yango Cabinet 14d.

---

## ✅ Entregables Completados

### 1. Vista de Auditoría Semanal

**Archivo:** `backend/sql/ops/v_cabinet_14d_funnel_audit_weekly.sql`

**Propósito:**
- Auditoría semanal del embudo de Cobranza 14d por `lead_date`
- Identifica el punto exacto de ruptura en el flujo de leads
- Grano: 1 fila por `week_start` (semana ISO truncada desde `lead_date`)

**Columnas clave:**
- `leads_total`: Total de leads en `module_ct_cabinet_leads` por semana
- `leads_with_identity`: Leads con `person_key` en `identity_links`
- `leads_with_driver`: Leads con `driver_id` (identity_link → drivers)
- `drivers_with_trips_14d`: Drivers con viajes dentro de ventana 14d
- `reached_m1_14d`, `reached_m5_14d`, `reached_m25_14d`: Milestones alcanzados
- `claims_expected_m1/m5/m25`: Claims que deberían existir según milestones
- `claims_present_m1/m5/m25`: Claims que realmente existen
- `debt_expected_total`: Monto esperado total por semana
- `claims_missing_m1/m5/m25`: Gaps (claims faltantes)

**Instalación:**
```sql
\i backend/sql/ops/v_cabinet_14d_funnel_audit_weekly.sql
```

**Query de prueba:**
```sql
SELECT *
FROM ops.v_cabinet_14d_funnel_audit_weekly
ORDER BY week_start DESC
LIMIT 8;
```

---

### 2. Script de Prueba

**Archivo:** `backend/scripts/test_cabinet_14d_audit_weekly.py`

**Propósito:**
- Ejecuta la vista de auditoría y muestra resultados formateados
- Identifica automáticamente problemas críticos (C1-C5)
- Muestra gaps de claims y porcentajes de conversión

**Ejecución:**
```bash
python backend/scripts/test_cabinet_14d_audit_weekly.py
```

**Salida esperada:**
- Tabla resumida de últimas 8 semanas
- Análisis de gaps por semana
- Verificación de leads post-05/01/2026

---

### 3. Fix de Orden Semanal en UI

**Archivos modificados:**
- `backend/sql/ops/v_cabinet_financial_14d.sql`: Agregada columna `week_start`
- `backend/app/api/v1/ops_payments.py`: Actualizado `ORDER BY` en queries

**Cambios:**
- **Antes:** `ORDER BY lead_date DESC NULLS LAST, driver_id`
- **Después:** `ORDER BY week_start DESC NULLS LAST, lead_date DESC NULLS LAST, driver_id`

**Endpoint afectado:**
- `GET /api/v1/ops/payments/cabinet-financial-14d`

**Resultado:**
- La tabla de Cobranza 14d ahora ordena por semana (descendente) y luego por `lead_date` (descendente)
- El filtro `week_start` ya existía y funciona correctamente

---

### 4. Documentación de Hallazgos

**Archivo:** `docs/ops/cabinet_14d_funnel_audit_findings.md`

**Contenido:**
- Template para documentar hallazgos de la auditoría
- Guía de root cause analysis (C1-C5)
- Sección para documentar fix aplicado
- Validación post-fix

**Uso:**
- Ejecutar auditoría con script de prueba
- Completar template con hallazgos reales
- Documentar fix aplicado según root cause identificado

---

## 🔍 Proceso de Diagnóstico

### FASE A: Identificar Universo Base ✅

- **Endpoint identificado:** `GET /api/v1/ops/payments/cabinet-financial-14d`
- **Vista base:** `ops.v_cabinet_financial_14d`
- **Tabla RAW:** `public.module_ct_cabinet_leads`
- **Anchor:** `lead_created_at::date` → `event_date` en `lead_events` → `lead_date` en `v_conversion_metrics`

### FASE B: Auditoría Semanal ✅

- **Vista creada:** `ops.v_cabinet_14d_funnel_audit_weekly`
- **Script de prueba:** `test_cabinet_14d_audit_weekly.py`
- **Listo para ejecutar:** Sí

### FASE C: Root Cause Analysis ⏳

**Pendiente de ejecución:** Ejecutar script de prueba para identificar el punto exacto de ruptura.

**Hipótesis a verificar:**
1. **C1:** `leads_total post-05 = 0` → Vista base filtra por fecha
2. **C2:** `leads_with_identity post-05 ~ 0` → No pasaron por matching
3. **C3:** `leads_with_driver post-05 = 0` → No hay identity_link a drivers
4. **C4:** `drivers_with_trips_14d post-05 = 0` → No hay viajes en ventana 14d
5. **C5:** `claims_present = 0` pero `reached_m1/m5/m25 > 0` → Bug en generación de claims

### FASE D: Fix ⏳

**Pendiente:** Aplicar fix según root cause identificado en FASE C.

### FASE E: UI Orden Semanal ✅

- **Completado:** Orden por `week_start DESC, lead_date DESC` aplicado
- **Vista actualizada:** `v_cabinet_financial_14d` incluye `week_start`

---

## 📋 Próximos Pasos

1. **Ejecutar auditoría:**
   ```bash
   python backend/scripts/test_cabinet_14d_audit_weekly.py
   ```

2. **Instalar vista de auditoría:**
   ```sql
   \i backend/sql/ops/v_cabinet_14d_funnel_audit_weekly.sql
   ```

3. **Revisar resultados:**
   - Identificar semana donde se rompe el flujo
   - Determinar root cause (C1-C5)
   - Completar `docs/ops/cabinet_14d_funnel_audit_findings.md`

4. **Aplicar fix:**
   - Según root cause identificado
   - Documentar en `cabinet_14d_funnel_audit_findings.md`

5. **Validar fix:**
   - Ejecutar script de prueba nuevamente
   - Verificar que semanas post-05 aparecen correctamente
   - Confirmar que no hay gaps de claims

---

## 🔗 Referencias

- **Vista de auditoría:** `backend/sql/ops/v_cabinet_14d_funnel_audit_weekly.sql`
- **Vista base:** `backend/sql/ops/v_cabinet_financial_14d.sql`
- **Endpoint:** `backend/app/api/v1/ops_payments.py` (líneas 309-547)
- **Script de prueba:** `backend/scripts/test_cabinet_14d_audit_weekly.py`
- **Documentación:** `docs/ops/cabinet_14d_funnel_audit_findings.md`

---

## 📊 Estructura del Flujo

```
module_ct_cabinet_leads (lead_created_at)
    ↓
observational.lead_events (event_date)
    ↓
canon.identity_links (person_key)
    ↓
observational.v_conversion_metrics (lead_date, driver_id)
    ↓
ops.v_cabinet_financial_14d (lead_date, driver_id, milestones, claims)
    ↓
ops.v_cabinet_14d_funnel_audit_weekly (week_start, embudo completo)
```

**Puntos de ruptura posibles:**
1. `lead_events` no tiene eventos post-05
2. `identity_links` no tiene person_key para leads post-05
3. `v_conversion_metrics` no tiene driver_id para person_key post-05
4. `v_cabinet_financial_14d` filtra por fecha o no tiene trips 14d
5. `v_claims_payment_status_cabinet` no genera claims para milestones post-05

---

## ✅ Checklist de Validación

- [x] Vista de auditoría creada
- [x] Script de prueba creado
- [x] Orden semanal aplicado en UI
- [x] Documentación de hallazgos creada
- [ ] Auditoría ejecutada
- [ ] Root cause identificado
- [ ] Fix aplicado
- [ ] Validación post-fix completada
