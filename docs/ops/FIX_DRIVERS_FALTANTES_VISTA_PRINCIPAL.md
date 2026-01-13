# Fix: Drivers con Identity y Milestones que no aparecían en Vista Principal

## Problema Identificado

Algunos leads que tenían:
- ✅ `person_key` (identidad)
- ✅ `driver_id` (driver)
- ✅ `trips_14d > 0` (milestones alcanzados)

**NO aparecían** en la vista principal `ops.v_cabinet_financial_14d` (DRIVER-first).

## Causa Raíz

La vista principal `v_cabinet_financial_14d` dependía únicamente de:
1. `observational.v_conversion_metrics` (con `origin_tag = 'cabinet'`)
2. `ops.v_payment_calculation` (con `origin_tag = 'cabinet'`)

Ambas vistas dependen de `observational.lead_events`. Si un lead tenía `person_key` pero **no tenía un evento en `lead_events`**, no aparecía en `v_conversion_metrics` ni en `v_payment_calculation`, y por tanto no aparecía en la vista principal.

## Solución Implementada

Se modificó `ops.v_cabinet_financial_14d` para agregar una tercera fuente de datos:

**`limbo_base`**: Drivers desde `ops.v_cabinet_leads_limbo` que tienen:
- `person_key IS NOT NULL`
- `driver_id IS NOT NULL`
- `trips_14d > 0`
- `lead_date IS NOT NULL`
- **Y que NO están** en `v_conversion_metrics` ni en `v_payment_calculation`

Estos drivers se agregan a `all_drivers_base` mediante un `UNION`, asegurando que todos los drivers con identity y milestones aparezcan en la vista principal.

## Resultados

### Antes del Fix
- Drivers en vista principal: **697**
- Leads con identity+driver+trips que NO aparecían: **5**

### Después del Fix
- Drivers en vista principal: **702** (+5)
- Leads con identity+driver+trips que NO aparecían: **0** ✅

## Archivos Modificados

1. **`backend/sql/ops/v_cabinet_financial_14d.sql`**
   - Agregado CTE `limbo_base` para incluir drivers desde `v_cabinet_leads_limbo`
   - Modificado `all_drivers_base` para incluir `limbo_base` mediante `UNION`
   - Actualizados comentarios de la vista

2. **`backend/scripts/apply_fix_missing_drivers.py`** (nuevo)
   - Script para aplicar el fix y verificar resultados

3. **`backend/scripts/diagnose_missing_drivers.py`** (nuevo)
   - Script de diagnóstico para identificar drivers faltantes

## Validación

Para verificar que el fix funciona correctamente:

```bash
cd backend
python scripts/diagnose_missing_drivers.py
```

Debería mostrar:
- Drivers en vista principal: 702+
- Leads con identity+driver+trips que NO están en vista principal: 0

## Notas Técnicas

- El fix mantiene la compatibilidad con la lógica existente
- No rompe endpoints existentes
- La vista sigue siendo auditable (documenta todas sus fuentes)
- El grano sigue siendo 1 fila por `driver_id` (GARANTIZADO)

## Fecha de Implementación

2026-01-XX
