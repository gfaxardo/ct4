# ✅ Solución: Problema de origin_tag en lead_events

## 🔍 Problema Identificado

Los eventos de `module_ct_scouting_daily` se creaban con `origin_tag: "scouting"` en el `payload_json`, pero:

1. `v_conversion_metrics` usa `payload_json->>'origin_tag'` PRIMERO
2. Si es `'scouting'`, los eventos NO aparecen en `v_conversion_metrics` con `origin_tag='cabinet'`
3. `v_payment_calculation` filtra por `origin_tag='cabinet'`
4. Por lo tanto, estos eventos NO aparecen en `v_cabinet_financial_14d`

## ✅ Solución Implementada

### 1. Código Corregido

**Archivo:** `backend/app/services/lead_attribution.py` (línea 369)

**Cambio:**
```python
# ANTES:
"origin_tag": "scouting",

# DESPUÉS:
"origin_tag": "cabinet",  # CORREGIDO: scouting_daily debe ser 'cabinet'
```

### 2. Eventos Existentes Corregidos

**Script ejecutado:** `backend/scripts/sql/fix_existing_lead_events_origin_tag.sql`

**Acción:** Actualiza todos los eventos existentes de `scouting_daily` para que tengan `origin_tag='cabinet'` en el `payload_json`.

## 📊 Verificación

Después de aplicar el fix:

```sql
-- Verificar eventos con origin_tag='cabinet'
SELECT COUNT(*) FROM observational.lead_events
WHERE source_table = 'module_ct_scouting_daily'
    AND payload_json->>'origin_tag' = 'cabinet'
    AND event_date >= '2025-12-15';

-- Verificar v_conversion_metrics
SELECT MAX(lead_date) FROM observational.v_conversion_metrics
WHERE origin_tag = 'cabinet';

-- Verificar v_cabinet_financial_14d
SELECT MAX(lead_date) FROM ops.v_cabinet_financial_14d;
```

## 🎯 Resultado Esperado

Después de aplicar el fix:
- Los eventos de `scouting_daily` tendrán `origin_tag='cabinet'`
- Aparecerán en `v_conversion_metrics` con `origin_tag='cabinet'`
- Aparecerán en `v_payment_calculation` con `origin_tag='cabinet'`
- Aparecerán en `v_cabinet_financial_14d` con fechas más recientes

## ⚠️ Nota Importante

Este fix corrige el problema para eventos FUTUROS. Los eventos existentes también se actualizaron mediante el script SQL.

Si aún hay eventos con `origin_tag='scouting'`, ejecutar nuevamente:
```sql
UPDATE observational.lead_events
SET payload_json = jsonb_set(
    COALESCE(payload_json, '{}'::jsonb),
    '{origin_tag}',
    '"cabinet"'
)
WHERE source_table = 'module_ct_scouting_daily'
    AND payload_json->>'origin_tag' = 'scouting';
```



