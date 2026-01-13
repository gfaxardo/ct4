# KPI Red Recovery - Validaciones y Verificaciones

## 🔍 VALIDACIONES OBLIGATORIAS

### 1. Validación de Impacto Real

**Script:** `backend/scripts/validate_kpi_red_impact.py`

**Propósito:** Verificar que el recovery tiene impacto real en el KPI rojo.

**Ejecución:**
```bash
cd backend
python -m scripts.validate_kpi_red_impact --limit 1000
```

**Reporta:**
- Backlog ANTES
- Backlog DESPUÉS
- Diferencia (delta)
- Leads matched en queue
- Leads failed y sus razones

**Criterio de Éxito:**
- `backlog_delta > 0` (backlog disminuye)
- O al menos `matched_count > 0` (hay leads matched)

---

### 2. Guardrail Obligatorio

**Script:** `backend/scripts/verify_kpi_red_drain.py`

**Propósito:** Verificar que leads matched NO están en el backlog.

**Ejecución:**
```bash
cd backend
python -m scripts.verify_kpi_red_drain --n 100
```

**Verifica:**
- Toma N leads con `status='matched'` en `cabinet_kpi_red_recovery_queue`
- Verifica que 0% de esos leads aparecen en `ops.v_cabinet_kpi_red_backlog`
- Si aparece alguno → `exit(1)` (fallo crítico)

**Criterio de Éxito:**
- 0% de leads matched están en el backlog

**Causas Comunes de Fallo:**
1. `source_pk` mismatch (casting diferente)
2. `identity_link` no se creó correctamente
3. Vista del backlog no sincronizada
4. Race condition

---

### 3. Consistencia de source_pk

**Script:** `backend/scripts/verify_source_pk_consistency.py`

**Propósito:** Verificar que `source_pk` es bit a bit idéntico entre todas las tablas/vistas.

**Ejecución:**
```bash
cd backend
python -m scripts.verify_source_pk_consistency
```

**Verifica:**
- Formato exacto en `module_ct_cabinet_leads`: `COALESCE(external_id::text, id::text)`
- Formato exacto en `ops.v_cabinet_kpi_red_backlog.lead_source_pk`
- Formato exacto en `ops.cabinet_kpi_red_recovery_queue.lead_source_pk`
- Formato exacto en `canon.identity_links.source_pk`

**Criterio de Éxito:**
- Todos los `source_pk` usan el mismo formato
- Tipos de datos coinciden

---

### 4. Creación de identity_origin

**Script:** `backend/scripts/verify_identity_origin_creation.py`

**Propósito:** Verificar que `canon.identity_origin` se crea SOLO cuando hay link válido.

**Ejecución:**
```bash
cd backend
python -m scripts.verify_identity_origin_creation
```

**Verifica:**
- Cada `identity_origin` con `origin_tag='cabinet_lead'` tiene un `identity_link` correspondiente
- NO hay origins orphan (sin link)
- `person_key` coincide entre origin y link

**Criterio de Éxito:**
- 0 origins orphan
- Todos los origins tienen links válidos

---

### 5. Alembic Heads

**Propósito:** Verificar que solo hay 1 head en Alembic.

**Ejecución:**
```bash
cd backend
alembic heads
```

**Criterio de Éxito:**
- 1 solo head

**Si hay múltiples heads:**
- Revisar `down_revision` de las migraciones
- Ajustar `down_revision` para unificar el historial

---

## 📋 CHECKLIST FINAL DE PRODUCCIÓN

Antes de mergear, ejecutar todas las validaciones:

- [ ] **Alembic heads**: `alembic heads` → 1 solo head
- [ ] **Consistencia source_pk**: `python -m scripts.verify_source_pk_consistency` → ✅
- [ ] **Identity origin creation**: `python -m scripts.verify_identity_origin_creation` → ✅
- [ ] **Guardrail**: `python -m scripts.verify_kpi_red_drain` → ✅
- [ ] **Impacto real**: `python -m scripts.validate_kpi_red_impact` → backlog disminuye o matched > 0

---

## 🔧 AJUSTES FINOS DE DISEÑO

### Documentación Explícita

**"Matched last 24h" ≠ "Drenado del KPI rojo"**

- **"Matched last 24h"**: Cuenta TODOS los matches de identidad en las últimas 24 horas
- **"KPI Red Recovery"**: Procesa ESPECÍFICAMENTE los leads que están en el KPI rojo

**El único KPI de éxito del recovery dirigido es:**
- `matched_out > new_backlog_in`
- Y/O `backlog_end < backlog_start`

### Si el KPI rojo NO baja

**El sistema NO está fallando.** El sistema está explicando por qué no puede bajar:

1. **Falta de datos**: `fail_reason = 'missing_identifiers'` o `'no_match_found'`
2. **Conflictos**: `fail_reason = 'conflict_multiple_candidates'`
3. **Backlog entrante mayor**: `new_backlog_in > matched_out`

---

## ✅ CIERRE

Si todas las validaciones pasan:
- ✅ Arquitectura correcta
- ✅ Lista para operar
- ✅ Core negocio-grade
- ✅ Frontend puede venir después
