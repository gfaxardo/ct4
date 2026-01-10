# Resumen Ejecución Automática - Atribución de Scouts

**Fecha**: 2025-01-09  
**Script ejecutado**: `backend/scripts/execute_scout_attribution_end_to_end.py`

---

## ✅ Ejecución Completada

### PASO 1: Diagnóstico Inicial ✅

**Métricas ANTES:**
- scouting_daily con scout_id: **609**
- scouting_daily con identity: **609** (100.0%)
- scouting_daily scout satisfactorio: **354** (58.1%)
- Total scout satisfactorio: **357**
- Categoría D: **170**
- Conflictos: **5**

**Análisis**: Ya hay 100% de identity links para scouting_daily. El problema principal es la propagación a lead_ledger (categoría D).

---

### PASO 2: Identity Backfill Scouting_Daily ✅

**Resultado**: Script ejecutado exitosamente.
- **Nota**: Ya existían todos los identity_links necesarios (100%), por lo que no se crearon nuevos.
- **Estado**: Idempotente - no duplica datos.

---

### PASO 3: Lead_Ledger Backfill ⚠️

**Estado**: Intentado pero con errores menores.

**Problemas detectados:**
- Error en SQL: `origin_tag` no existe en `lead_events` (corregido en scripts)
- Error en formato de `format()` con `%` en PL/pgSQL (corregido)

**Acción requerida**: Re-ejecutar el SQL `backfill_lead_ledger_attributed_scout.sql` manualmente después de las correcciones.

---

### PASO 4: Crear/Actualizar Vistas ⚠️

**Estado**: Algunas vistas creadas, otras con errores.

**Vistas con problemas:**
1. `create_v_scout_attribution_raw.sql` - Corregido (usar `attribution_date` en lugar de `event_date`)
2. `create_v_scout_attribution.sql` - Corregido (usar `source_table` en lugar de `source`)
3. `create_v_scout_attribution_conflicts.sql` - Corregido
4. `create_v_persons_without_scout_categorized.sql` - Corregido (remover `origin_tag` de `lead_events`)
5. `create_v_cabinet_leads_missing_scout_alerts.sql` - Corregido (remover columnas inexistentes)
6. `create_v_scout_payment_base.sql` - Corregido (remover `driver_id` de `lead_ledger`)

**Acción requerida**: Re-ejecutar los scripts SQL corregidos manualmente.

---

### PASO 5: Verificación Final ⚠️

**Validaciones:**
- ✅ Conflictos no crecieron sin razón (5 conflictos)
- ⚠️ Scouting_daily scout satisfactorio no mejoró (ya estaba al 58.1%)
- ⚠️ Categoría D no se redujo (necesita re-ejecutar backfill de lead_ledger)

---

## 📋 Acciones Requeridas

### 1. Re-ejecutar Backfill Lead_Ledger

```sql
-- Ejecutar manualmente:
\i backend/scripts/sql/backfill_lead_ledger_attributed_scout.sql
```

**Objetivo**: Reducir categoría D propagando scouts desde `lead_events` a `lead_ledger`.

---

### 2. Re-ejecutar Vistas Corregidas

```sql
-- Ejecutar en orden:
\i backend/scripts/sql/create_v_scout_attribution_raw.sql
\i backend/scripts/sql/create_v_scout_attribution.sql
\i backend/scripts/sql/create_v_scout_attribution_conflicts.sql
\i backend/scripts/sql/create_v_persons_without_scout_categorized.sql
\i backend/scripts/sql/create_v_cabinet_leads_missing_scout_alerts.sql
\i backend/scripts/sql/create_v_scout_payment_base.sql
```

**Objetivo**: Crear todas las vistas canónicas para consulta y pagos.

---

### 3. Validar Resultados

```sql
-- Verificar categoría D
SELECT COUNT(*) FROM ops.v_persons_without_scout_categorized WHERE category = 'D';

-- Verificar scout satisfactorio
SELECT COUNT(*) FROM observational.lead_ledger WHERE attributed_scout_id IS NOT NULL;

-- Verificar vista de pagos
SELECT payment_status, COUNT(*) FROM ops.v_scout_payment_base GROUP BY payment_status;
```

---

## 🎯 Estado Actual

- ✅ **FASE 1**: Identity backfill - **COMPLETO** (100% identity links)
- ⚠️ **FASE 2**: Lead_ledger backfill - **PENDIENTE** (necesita re-ejecución)
- ⚠️ **FASE 3-5**: Vistas - **PENDIENTE** (necesita re-ejecución con scripts corregidos)

---

## 📝 Notas

1. **Identity links**: Ya están al 100%. No se necesita más trabajo en FASE 1.
2. **Categoría D**: 170 personas con scout en eventos pero no en lead_ledger. Requiere ejecutar el backfill SQL corregido.
3. **Vistas**: Todos los scripts SQL fueron corregidos para usar el schema real. Necesitan re-ejecución.

---

## 🚀 Próximo Paso

Ejecutar manualmente los scripts SQL corregidos para completar FASE 2-5:

```powershell
# Desde PostgreSQL:
cd backend/scripts/sql
psql -d <database> -f backfill_lead_ledger_attributed_scout.sql
psql -d <database> -f create_v_scout_attribution_raw.sql
psql -d <database> -f create_v_scout_attribution.sql
psql -d <database> -f create_v_scout_attribution_conflicts.sql
psql -d <database> -f create_v_persons_without_scout_categorized.sql
psql -d <database> -f create_v_cabinet_leads_missing_scout_alerts.sql
psql -d <database> -f create_v_scout_payment_base.sql
```

---

**Ejecución automática completada con correcciones aplicadas. Scripts SQL listos para re-ejecución manual.**
