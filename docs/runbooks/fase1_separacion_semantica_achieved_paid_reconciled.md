# FASE 1 — Separación Semántica ACHIEVED vs PAID vs RECONCILED

**Fecha:** 2025-01-XX  
**Proyecto:** CT4 — Resolver inconsistencia "M5 pagado sin M1 pagado"  
**Estado:** ✅ COMPLETADA

---

## Objetivo

Crear una arquitectura explícita que separe:
- **ACHIEVED** (operativo - milestones logrados)
- **PAID** (pagos Yango - milestones pagados)
- **RECONCILED** (cruce explícito entre ambos)

Sin modificar vistas existentes ni reglas. Solo CREATE VIEW (read-only).

---

## Entregables

### 1. `ops.v_cabinet_milestones_achieved`

**Archivo:** `backend/sql/ops/v_cabinet_milestones_achieved.sql`

**Propósito:** Vista canónica C2 que expone SOLO milestones ACHIEVED (operativos - viajes logrados) sin mezclar con información de pagos.

**Fuente:** `ops.v_payment_calculation` (vista canónica C2)

**Grano:** `(driver_id, milestone_value)` - 1 fila por milestone alcanzado

**Filtros:**
- `origin_tag = 'cabinet'`
- `rule_scope = 'partner'` (Yango, no scouts)
- `milestone_trips IN (1, 5, 25)`
- `milestone_achieved = true`
- `driver_id IS NOT NULL`

**Campos principales:**
- `driver_id`, `person_key`, `milestone_value`
- `achieved_date` - Fecha en que se alcanza el milestone
- `achieved_trips_in_window` - Viajes acumulados
- `expected_amount` - Monto según regla (NO es pago real)
- `window_days`, `rule_id`, etc.

**Sin campos de pago:** No incluye información de pagos, solo milestones logrados.

---

### 2. `ops.v_cabinet_milestones_paid`

**Archivo:** `backend/sql/ops/v_cabinet_milestones_paid.sql`

**Propósito:** Vista canónica C4 que expone SOLO milestones PAID (pagos reconocidos por Yango) sin mezclar con información de milestones alcanzados.

**Fuente:** `ops.v_yango_payments_ledger_latest_enriched` (ledger enriquecido)

**Grano:** `(driver_id, milestone_value)` - 1 fila por milestone pagado

**Filtros:**
- `is_paid = true`
- `milestone_value IN (1, 5, 25)`
- `driver_id_final IS NOT NULL` (requiere identidad)

**Campos principales:**
- `driver_id`, `person_key`, `milestone_value`
- `pay_date` - Fecha del pago reconocido
- `payment_key` - Clave única del pago
- `identity_status`, `match_rule`, `match_confidence`
- `driver_id_original`, `driver_id_enriched`
- `raw_driver_name`, `driver_name_normalized`

**Sin campos de achieved:** No incluye información de milestones logrados, solo pagos.

**Nota importante:** Por negocio puede existir `paid_m5=true` con `paid_m1=false` (Yango paga M5 y no paga M1, y luego puede enmendar).

---

### 3. `ops.v_cabinet_milestones_reconciled`

**Archivo:** `backend/sql/ops/v_cabinet_milestones_reconciled.sql`

**Propósito:** Vista de reconciliación que hace JOIN explícito entre ACHIEVED (operativo) y PAID (pagos Yango). Expone `reconciliation_status` que categoriza cada milestone en 4 estados mutuamente excluyentes.

**Fuentes:**
- `ops.v_cabinet_milestones_achieved` (ACHIEVED)
- `ops.v_cabinet_milestones_paid` (PAID)

**JOIN:** FULL OUTER JOIN para capturar ambos casos (ACHIEVED sin PAID y PAID sin ACHIEVED)

**Grano:** `(driver_id, milestone_value)` - 1 fila por combinación posible

**Reconciliation Status (mutuamente excluyente):**
- **OK** - Milestone alcanzado y pagado
- **ACHIEVED_NOT_PAID** - Milestone alcanzado pero no pagado
- **PAID_WITHOUT_ACHIEVEMENT** - Milestone pagado pero no alcanzado
- **NOT_APPLICABLE** - Ni alcanzado ni pagado (no debería aparecer en producción)

**Campos:**
- Todos los campos de ACHIEVED (prefijo `achieved_*`)
- Todos los campos de PAID (prefijo `paid_*`)
- `reconciliation_status` - Estado de reconciliación

---

### 4. Comentarios SQL en Vistas Existentes

**Archivo:** `backend/sql/ops/fase1_comentarios_vistas_mezclan_conceptos.sql`

**Propósito:** Agregar comentarios SQL claros en vistas existentes que mezclan ACHIEVED y PAID, sin modificar la lógica existente.

**Vistas documentadas:**

1. **`ops.v_claims_payment_status_cabinet`**
   - Comentario: Esta vista MEZCLA ACHIEVED con PAID
   - Campos documentados: `milestone_value` (ACHIEVED), `paid_flag` (PAID)

2. **`ops.v_payments_driver_matrix_cabinet`**
   - Comentario: Los campos `m1_achieved_flag`, etc. provienen de una vista que mezcla conceptos
   - Campos documentados: `m1_achieved_flag`, `m5_achieved_flag`, `m25_achieved_flag`, `m1_yango_payment_status`, etc.

3. **`ops.v_yango_cabinet_claims_for_collection`**
   - Comentario: Basada en una vista que mezcla ACHIEVED con PAID
   - Campos documentados: `yango_payment_status`

**Reglas:**
- SOLO agregar comentarios (COMMENT ON VIEW / COMMENT ON COLUMN)
- NO modificar lógica SQL
- NO agregar columnas nuevas
- Mantener compatibilidad hacia atrás

---

## Ubicación de Archivos

```
backend/sql/ops/
├── v_cabinet_milestones_achieved.sql          # Vista ACHIEVED
├── v_cabinet_milestones_paid.sql              # Vista PAID
├── v_cabinet_milestones_reconciled.sql        # Vista RECONCILED
└── fase1_comentarios_vistas_mezclan_conceptos.sql  # Comentarios SQL
```

---

## Uso de las Vistas

### Consultar milestones logrados (operativo)
```sql
SELECT *
FROM ops.v_cabinet_milestones_achieved
WHERE driver_id = 'DRIVER_ID_AQUI';
```

### Consultar milestones pagados (pagos Yango)
```sql
SELECT *
FROM ops.v_cabinet_milestones_paid
WHERE driver_id = 'DRIVER_ID_AQUI';
```

### Reconciliación (diagnóstico de inconsistencias)
```sql
-- M5 pagado sin M1 pagado
SELECT *
FROM ops.v_cabinet_milestones_reconciled
WHERE reconciliation_status = 'PAID_WITHOUT_ACHIEVEMENT'
  AND milestone_value = 5;

-- Milestones alcanzados pero no pagados
SELECT *
FROM ops.v_cabinet_milestones_reconciled
WHERE reconciliation_status = 'ACHIEVED_NOT_PAID';
```

---

## Separación Semántica

### Antes (vistas mezcladas)
- `ops.v_claims_payment_status_cabinet` → Mezcla ACHIEVED + PAID
- `ops.v_payments_driver_matrix_cabinet` → Campos ambiguos `m1_achieved_flag` (¿logrado o pagado?)

### Después (vistas separadas)
- `ops.v_cabinet_milestones_achieved` → SOLO ACHIEVED
- `ops.v_cabinet_milestones_paid` → SOLO PAID
- `ops.v_cabinet_milestones_reconciled` → JOIN explícito con status claro

---

## Capas Canónicas

| Capa | Vista | Concepto |
|------|-------|----------|
| C2 - Elegibilidad | `ops.v_cabinet_milestones_achieved` | ACHIEVED (operativo) |
| C4 - Pagos | `ops.v_cabinet_milestones_paid` | PAID (pagos Yango) |
| C3 - Claims | `ops.v_cabinet_milestones_reconciled` | RECONCILED (cruce explícito) |

---

## Validación

### Queries read-only para validar

**1. Verificar que las vistas existen:**
```sql
SELECT table_name
FROM information_schema.views
WHERE table_schema = 'ops'
  AND table_name IN (
    'v_cabinet_milestones_achieved',
    'v_cabinet_milestones_paid',
    'v_cabinet_milestones_reconciled'
  );
```

**2. Verificar conteos por reconciliation_status:**
```sql
SELECT 
    reconciliation_status,
    COUNT(*) AS count_rows,
    COUNT(DISTINCT driver_id) AS unique_drivers
FROM ops.v_cabinet_milestones_reconciled
GROUP BY reconciliation_status
ORDER BY reconciliation_status;
```

**3. Verificar que no hay regresiones:**
```sql
-- Comparar conteos entre vista antigua y nueva (solo para ACHIEVED)
SELECT 
    'v_claims_payment_status_cabinet' AS source,
    COUNT(*) AS total_claims
FROM ops.v_claims_payment_status_cabinet
UNION ALL
SELECT 
    'v_cabinet_milestones_achieved' AS source,
    COUNT(*) AS total_claims
FROM ops.v_cabinet_milestones_achieved;
```

---

## Próximos Pasos

1. ✅ FASE 0 — Inventario: COMPLETADA
2. ✅ FASE 1 — Separación Semántica: COMPLETADA
3. ⏭️ FASE 2 — Diagnóstico: Crear queries de diagnóstico para M5 sin M1
4. ⏭️ FASE 3 — Documentación: Crear runbook completo de ACHIEVED vs PAID

---

**Fin de FASE 1**





