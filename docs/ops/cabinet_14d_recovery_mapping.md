# Cabinet 14d Recovery Mapping - Estructura Actual

## FASE 0 - SCAN DEL REPO

Este documento mapea la estructura actual del sistema para conectar Recovery (Brechas de Identidad) con Cobranza Cabinet 14d.

---

## 1. Tabla Fuente de Leads Cabinet

**Tabla:** `public.module_ct_cabinet_leads`

**Campos clave:**
- `id` (INTEGER, PK): ID interno
- `external_id` (VARCHAR, nullable): ID externo (si existe)
- `lead_created_at` (TIMESTAMP WITHOUT TIME ZONE): Fecha de creación del lead (lead_date)
- `park_phone` (VARCHAR, nullable): Teléfono
- `first_name`, `middle_name`, `last_name` (VARCHAR, nullable): Nombre
- `asset_plate_number` (VARCHAR, nullable): Placa

**lead_id:** `COALESCE(external_id, id::TEXT)` (usado como source_pk en identity_links)

**lead_date:** `lead_created_at::DATE`

---

## 2. Tabla/Vista Canónica de Claims Cabinet 14d

**Vista principal:** `ops.v_yango_payments_claims_cabinet_14d`

**Fuente base:** `ops.v_payment_calculation` (vista canónica C2)

**Cómo se determina "tiene claims" hoy:**
- Un lead tiene claim si existe un registro en `ops.v_yango_payments_claims_cabinet_14d` con:
  - `origin_tag = 'cabinet'`
  - `rule_scope = 'partner'` (Yango)
  - `milestone_value IN (1, 5, 25)`
  - `milestone_achieved = true`
  - `driver_id IS NOT NULL`
  - `lead_date` dentro de la ventana de 14 días

**Granularidad:** 1 fila por (driver_id, person_key, lead_date, milestone_value)

**Condición de "has_claim":**
```sql
EXISTS (
    SELECT 1 
    FROM ops.v_yango_payments_claims_cabinet_14d c
    WHERE c.person_key = lead_person_key
      AND c.lead_date = cabinet_lead_date
      AND c.origin_tag = 'cabinet'
      AND c.milestone_achieved = true
)
```

---

## 3. Vínculo Lead → Person Key

**Tabla canónica:** `canon.identity_links`

**Estructura:**
- `source_table` = `'module_ct_cabinet_leads'`
- `source_pk` = lead_id (COALESCE(external_id, id::TEXT))
- `person_key` = UUID (FK a canon.identity_registry)
- `linked_at` = TIMESTAMP (cuándo se creó el vínculo)

**Cómo se usa:**
```sql
SELECT il.person_key
FROM canon.identity_links il
WHERE il.source_table = 'module_ct_cabinet_leads'
  AND il.source_pk = :lead_id
```

**Estado actual:** El vínculo existe cuando el matching engine encuentra una identidad para un lead.

---

## 4. Tabla Identity Origin

**Tabla:** `canon.identity_origin`

**Estructura:**
- `person_key` (UUID, PK, FK a canon.identity_registry)
- `origin_tag` (ENUM): 'cabinet_lead', 'scout_registration', 'migration', 'legacy_external'
- `origin_source_id` (VARCHAR): ID del origen (para cabinet_lead = lead_id)
- `origin_created_at` (TIMESTAMPTZ)
- `origin_confidence` (NUMERIC)
- `decided_by` (ENUM): 'system' o 'manual'
- `resolution_status` (ENUM)

**Para Cabinet Leads:**
- `origin_tag = 'cabinet_lead'`
- `origin_source_id = lead_id` (COALESCE(external_id, id::TEXT))
- `person_key` = el person_key del lead

**Estado actual:** No todos los identity_links tienen identity_origin correspondiente.

---

## 5. Vista de Identity Gap Analysis (Actual)

**Vista:** `ops.v_identity_gap_analysis`

**Grano:** 1 fila por lead_id

**Gap Reasons:**
- `no_identity`: Lead sin person_key (no tiene identity_link)
- `no_origin`: Lead tiene person_key pero NO tiene identity_origin con origin_tag='cabinet_lead' y origin_source_id=lead_id
- `inconsistent_origin`: Lead tiene origin pero origin_source_id != lead_id
- `resolved`: Lead tiene identity + origin correcto

**Endpoint actual:** `/api/v1/ops/identity-gaps`

---

## 6. Problema Identificado

El módulo "Brechas de Identidad (Recovery)" muestra matches, pero la card roja "Leads sin Identidad ni Claims" (Cabinet 14d) no baja.

**Causa probable:**
- El matching engine crea `canon.identity_links` para los leads
- Pero NO se crea automáticamente `canon.identity_origin` con origin_tag='cabinet_lead'
- Por lo tanto, aunque el lead tenga person_key, no tiene origin correcto
- Y sin origin correcto, los claims no se generan correctamente (o la vista de claims no los detecta)

---

## 7. Solución Propuesta

**Tabla puente de auditoría:**
- `ops.cabinet_lead_recovery_audit`: Registra cuándo y cómo se recuperó un lead

**Vista de identidad efectiva:**
- `ops.v_cabinet_lead_identity_effective`: Determina si un lead tiene identidad efectiva (person_key + origin)

**Vista de impacto de recovery:**
- `ops.v_cabinet_identity_recovery_impact_14d`: Mide el impacto del recovery sobre cobranza (ventana 14d)

**Job permanente:**
- `cabinet_recovery_impact_job.py`: Asegura que cuando se encuentra un person_key para un lead, se crea:
  1. El vínculo en `canon.identity_links` (ya existe)
  2. El registro en `canon.identity_origin` (falta)
  3. El registro en `ops.cabinet_lead_recovery_audit` (nuevo)

---

## 8. Endpoints Actuales Relacionados

**Identity Gaps:**
- `GET /api/v1/ops/identity-gaps`: Lista leads con brechas de identidad

**Cabinet Claims:**
- `GET /api/v1/yango/payments/claims/cabinet-14d`: Lista claims cabinet 14d (probablemente existe, verificar)

---

## 9. Notas Importantes

- **NO inventar person_key**: Solo usar person_key existentes de canon.identity_registry
- **NO recalcular elegibilidad/claims/pagos**: Solo conectar recovery con precondiciones (identidad+origen)
- **Todo auditable, idempotente, no destructivo**
- **Recovery solo puede:**
  - Crear vínculo canónico entre Lead Cabinet y person_key existente (via canon.identity_links)
  - Upsert canon.identity_origin (cabinet_lead + origin_source_id=lead_id)
  - Registrar en ops.cabinet_lead_recovery_audit
