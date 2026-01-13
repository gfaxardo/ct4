# KPI Red Recovery - Checklist Final de Producción

## ✅ VALIDACIONES OBLIGATORIAS

### 1. Alembic Heads ✅

**Comando:**
```bash
cd backend
alembic heads
```

**Output esperado:**
```
017_merge_heads (head)
```

**Evidencia:** Ver `docs/ops/KPI_RED_RECOVERY_EVIDENCE.md`

**Estado:** ✅ **COMPLETADO** (1 solo head)

---

### 2. Validación de Impacto Real ⏳

**Script:** `backend/scripts/validate_kpi_red_impact.py`

**Ejecución:**
```bash
cd backend
python -m scripts.validate_kpi_red_impact --limit 1000
```

**Criterio de Éxito:**
- ✅ Backlog ANTES registrado
- ✅ Backlog DESPUÉS registrado
- ✅ Diferencia calculada (backlog_delta)
- ✅ Leads matched en queue reportados
- ✅ Leads failed y razones reportados

**Estado:** ⏳ **PENDIENTE** (requiere migraciones aplicadas)

---

### 3. Guardrail Obligatorio ⏳

**Script:** `backend/scripts/verify_kpi_red_drain.py`

**Ejecución:**
```bash
cd backend
python -m scripts.verify_kpi_red_drain --n 100
```

**Criterio de Éxito:**
- ✅ 0% de leads matched están en el backlog
- ✅ `exit(0)` si todos los leads matched NO están en el backlog
- ❌ `exit(1)` si algún lead matched está en el backlog (fallo crítico)

**Estado:** ⏳ **PENDIENTE** (requiere ejecutar recovery job primero)

---

### 4. Consistencia de source_pk ⏳

**Script:** `backend/scripts/verify_source_pk_consistency.py`

**Ejecución:**
```bash
cd backend
python -m scripts.verify_source_pk_consistency
```

**Criterio de Éxito:**
- ✅ Todos los `source_pk` usan el mismo formato: `COALESCE(external_id::text, id::text)`
- ✅ Tipos de datos coinciden entre todas las tablas/vistas

**Estado:** ⏳ **PENDIENTE** (requiere migraciones aplicadas)

---

### 5. Creación de identity_origin ⏳

**Script:** `backend/scripts/verify_identity_origin_creation.py`

**Ejecución:**
```bash
cd backend
python -m scripts.verify_identity_origin_creation
```

**Criterio de Éxito:**
- ✅ 0 origins orphan (sin link)
- ✅ Todos los origins tienen links válidos
- ✅ `person_key` coincide entre origin y link

**Estado:** ⏳ **PENDIENTE** (requiere ejecutar recovery job primero)

---

### 6. ORIGIN_MISSING = 0 ⏳

**Script:** `backend/scripts/check_origin_missing.py`

**Ejecución:**
```bash
cd backend
python -m scripts.check_origin_missing
```

**Criterio de Éxito:**
- ✅ Origins orphan = 0
- ✅ Leads matched sin origin = 0

**Estado:** ⏳ **PENDIENTE** (requiere ejecutar recovery job primero)

**Implementación:** ✅ `_ensure_identity_origin()` en `backend/jobs/recover_kpi_red_leads.py`

---

## 📋 CHECKLIST FINAL DE PRODUCCIÓN

Antes de mergear, ejecutar todas las validaciones:

- [x] **Alembic heads**: `alembic heads` → 1 solo head ✅
- [ ] **Corregir nombre revisión 016**: Cambiar a `016_kpi_red_recovery_queue` (máx 32 caracteres) ✅
- [ ] **Ejecutar migraciones**: `alembic upgrade head` → ⏳ PENDIENTE
- [ ] **Consistencia source_pk**: `python -m scripts.verify_source_pk_consistency` → ⏳ PENDIENTE
- [ ] **Identity origin creation**: `python -m scripts.verify_identity_origin_creation` → ⏳ PENDIENTE
- [ ] **Sembrar cola**: `python -m jobs.seed_kpi_red_queue` → ⏳ PENDIENTE
- [ ] **Recuperar leads**: `python -m jobs.recover_kpi_red_leads --limit 1000` → ⏳ PENDIENTE
- [ ] **Guardrail**: `python -m scripts.verify_kpi_red_drain` → ⏳ PENDIENTE
- [ ] **Impacto real**: `python -m scripts.validate_kpi_red_impact --limit 1000` → ⏳ PENDIENTE
- [ ] **ORIGIN_MISSING = 0**: `python -m scripts.check_origin_missing` → ⏳ PENDIENTE
- [ ] **UI mínimo**: Agregar endpoint + componente → ⏳ PENDIENTE

---

## 📝 DOCUMENTACIÓN

### Diferencia Crítica: "Matched last 24h" ≠ "Drenado del KPI rojo"

**"Matched last 24h":**
- Cuenta TODOS los matches de identidad en las últimas 24 horas
- Fuente: `ops.identity_matching_jobs` con `status='matched'` y `last_attempt_at >= NOW() - INTERVAL '24 hours'`
- **NO** está relacionado directamente con el KPI rojo

**"KPI Red Recovery":**
- Procesa ESPECÍFICAMENTE los leads que están en el KPI rojo
- Fuente: `ops.cabinet_kpi_red_recovery_queue` con `status='matched'`
- **SÍ** está relacionado directamente con el KPI rojo

**El único KPI de éxito del recovery dirigido es:**
- `matched_out > new_backlog_in` (más leads recuperados que nuevos leads entrando)
- Y/O `backlog_end < backlog_start` (backlog disminuye)

### Si el KPI rojo NO baja

**El sistema NO está fallando.** El sistema está explicando por qué no puede bajar:

1. **Falta de datos**: `fail_reason = 'missing_identifiers'` o `'no_match_found'`
   - Los leads no tienen phone/doc/email suficientes para matching
   - **Solución**: Mejorar calidad de datos en origen

2. **Conflictos**: `fail_reason = 'conflict_multiple_candidates'`
   - Se encontraron múltiples candidatos con scores muy cercanos
   - **Solución**: Revisión manual o ajustar reglas de matching

3. **Backlog entrante mayor**: `new_backlog_in > matched_out`
   - Entran más leads nuevos al backlog de los que se recuperan
   - **Solución**: Aumentar frecuencia del job o capacidad de procesamiento

---

## 🔧 PROBLEMA CONOCIDO Y SOLUCIÓN

### Problema: Nombre de Revisión Demasiado Largo

**Error:**
```
sqlalchemy.exc.DataError: value too long for type character varying(32)
```

**Causa:**
- Nombre de revisión `016_cabinet_kpi_red_recovery_queue` (35 caracteres)
- Límite de `alembic_version.version_num`: 32 caracteres

**Solución aplicada:**
- ✅ Cambiar nombre a `016_kpi_red_recovery_queue` (26 caracteres)
- ✅ Actualizar merge migration `017_merge_heads.py`

**Próximo paso:**
- Ejecutar `alembic upgrade head`
- Verificar que las migraciones se apliquen correctamente

---

## ✅ CIERRE

**Estado actual:**
- ✅ Merge migration creada (1 head)
- ✅ Nombre de revisión corregido
- ✅ Scripts de validación creados
- ✅ ORIGIN_MISSING fix implementado
- ⏳ Pendiente: Ejecutar migraciones y validaciones
- ⏳ Pendiente: UI mínimo

**Próximos pasos:**
1. Ejecutar `alembic upgrade head`
2. Ejecutar validaciones
3. Documentar resultados
4. Agregar UI mínimo
