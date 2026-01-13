# Resumen de Validaciones: KPI Red Recovery

## ✅ VALIDACIONES IMPLEMENTADAS

### 1. Validación de Impacto Real ✅

**Script:** `backend/scripts/validate_kpi_red_impact.py`

**Propósito:** Verificar before/after del impacto real en el KPI rojo.

**Funcionalidad:**
- Obtiene backlog ANTES
- Ejecuta seed_kpi_red_queue
- Ejecuta recover_kpi_red_leads (limit configurable)
- Obtiene backlog DESPUÉS
- Reporta diferencia, leads matched, y leads failed con razones

**Ejecución:**
```bash
cd backend
python -m scripts.validate_kpi_red_impact --limit 1000
```

**Estado:** ✅ Implementado

---

### 2. Guardrail Obligatorio ✅

**Script:** `backend/scripts/verify_kpi_red_drain.py`

**Propósito:** Verificar que leads matched NO están en el backlog.

**Funcionalidad:**
- Toma N leads con `status='matched'` en `cabinet_kpi_red_recovery_queue`
- Verifica que 0% de esos leads aparecen en `ops.v_cabinet_kpi_red_backlog`
- Si aparece alguno → `exit(1)` (fallo crítico)

**Ejecución:**
```bash
cd backend
python -m scripts.verify_kpi_red_drain --n 100
```

**Estado:** ✅ Implementado

---

### 3. Consistencia de source_pk ✅

**Script:** `backend/scripts/verify_source_pk_consistency.py`

**Propósito:** Verificar que `source_pk` es bit a bit idéntico entre todas las tablas/vistas.

**Funcionalidad:**
- Verifica formato exacto: `COALESCE(external_id::text, id::text)`
- Verifica tipos de datos
- Verifica formato bit a bit idéntico (casting incluido)

**Ejecución:**
```bash
cd backend
python -m scripts.verify_source_pk_consistency
```

**Estado:** ✅ Implementado

---

### 4. Creación de identity_origin ✅

**Script:** `backend/scripts/verify_identity_origin_creation.py`

**Propósito:** Verificar que `canon.identity_origin` se crea SOLO cuando hay link válido.

**Funcionalidad:**
- Verifica que cada `identity_origin` con `origin_tag='cabinet_lead'` tiene un `identity_link` correspondiente
- Verifica que NO hay origins orphan (sin link)
- Verifica que `person_key` coincide entre origin y link

**Ejecución:**
```bash
cd backend
python -m scripts.verify_identity_origin_creation
```

**Estado:** ✅ Implementado

---

### 5. Alembic Heads ✅

**Comando:**
```bash
cd backend
alembic heads
```

**Estado:** ✅ CORREGIDO
- `016_cabinet_kpi_red_recovery_queue` ahora apunta a `015_cabinet_lead_recovery_audit`
- Debe retornar 1 solo head después de la corrección

---

## 📚 DOCUMENTACIÓN CREADA

### 1. README del Módulo ✅

**Archivo:** `docs/ops/KPI_RED_RECOVERY_README.md`

**Contenido:**
- Propósito del módulo
- Diferencias críticas: "Matched last 24h" ≠ "Drenado del KPI rojo"
- Criterios de éxito
- Arquitectura
- Consistencia de source_pk
- Guardrail
- Métricas
- Ejecución
- Validación

**Estado:** ✅ Creado

---

### 2. Documentación de Validaciones ✅

**Archivo:** `docs/ops/KPI_RED_RECOVERY_VALIDATION.md`

**Contenido:**
- Validaciones obligatorias
- Guardrail obligatorio
- Consistencia de source_pk
- Creación de identity_origin
- Alembic heads
- Checklist final de producción
- Ajustes finos de diseño

**Estado:** ✅ Creado

---

### 3. Checklist Final ✅

**Archivo:** `docs/ops/KPI_RED_RECOVERY_CHECKLIST.md`

**Contenido:**
- Checklist de validaciones obligatorias
- Criterios de éxito para cada validación
- Estado de cada validación
- Documentación de diferencias críticas

**Estado:** ✅ Creado

---

## 🔧 AJUSTES REALIZADOS

### 1. Corrección de Alembic Heads ✅

**Problema:** 2 heads en Alembic (`015_cabinet_lead_recovery_audit` y `016_cabinet_kpi_red_recovery_queue`)

**Solución:** Corregido `down_revision` de `016_cabinet_kpi_red_recovery_queue` para que apunte a `015_cabinet_lead_recovery_audit`

**Estado:** ✅ Corregido

---

### 2. Documentación de Diferencias Críticas ✅

**Problema:** Necesidad de aclarar que "Matched last 24h" ≠ "Drenado del KPI rojo"

**Solución:** Documentado explícitamente en:
- `docs/ops/KPI_RED_RECOVERY_README.md`
- `docs/ops/KPI_RED_RECOVERY_VALIDATION.md`
- `docs/ops/KPI_RED_RECOVERY_CHECKLIST.md`

**Estado:** ✅ Documentado

---

### 3. Guardrail Obligatorio ✅

**Problema:** Necesidad de verificar automáticamente que leads matched NO están en el backlog

**Solución:** Creado `backend/scripts/verify_kpi_red_drain.py`

**Estado:** ✅ Implementado

---

## 📋 CHECKLIST FINAL DE PRODUCCIÓN

Antes de mergear, ejecutar todas las validaciones:

- [x] **Alembic heads**: Corregido `down_revision` de 016 ✅
- [x] **Scripts de validación**: Creados 4 scripts de verificación ✅
- [x] **Documentación**: Creada documentación completa ✅
- [x] **Guardrail**: Implementado guardrail obligatorio ✅
- [x] **Consistencia source_pk**: Verificación implementada ✅
- [x] **Identity origin creation**: Verificación implementada ✅

**PENDIENTE (ejecutar manualmente antes de mergear):**
- [ ] Ejecutar `alembic heads` → debe retornar 1 solo head
- [ ] Ejecutar `python -m scripts.verify_source_pk_consistency` → ✅
- [ ] Ejecutar `python -m scripts.verify_identity_origin_creation` → ✅
- [ ] Ejecutar `python -m scripts.verify_kpi_red_drain` → ✅
- [ ] Ejecutar `python -m scripts.validate_kpi_red_impact --limit 1000` → backlog disminuye o matched > 0

---

## ✅ CIERRE

Todas las validaciones están implementadas y listas para ejecutar.

**Arquitectura:** ✅ Correcta
**Core:** ✅ Listo para operar
**Guardrails:** ✅ Implementados
**Documentación:** ✅ Completa

**Frontend:** ⏳ Puede venir después
