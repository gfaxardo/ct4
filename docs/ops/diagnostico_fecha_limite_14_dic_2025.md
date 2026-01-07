# Diagnóstico: Vista Cabinet Financial 14d solo muestra datos hasta 14/12/2025

## Problema Reportado

La vista `ops.v_cabinet_financial_14d` solo muestra datos hasta el **14/12/2025**, a pesar de que:
- Se insertaron 108 pagos nuevos (hasta el 05/01/2026)
- 97 de esos pagos tienen `driver_id` asignado
- Los pagos tienen `person_key` completo

## Cadena de Dependencias Identificada

```
1. observational.lead_events (fuente base)
   ↓ (event_date = lead_date)
2. observational.v_conversion_metrics (cabinet)
   ↓ (lead_date desde lead_events)
3. ops.v_payment_calculation (cabinet)
   ↓ (lead_date desde v_conversion_metrics)
4. ops.v_cabinet_financial_14d (vista final)
```

## Causa Raíz Identificada

**El problema está en `observational.lead_events`**: Esta tabla solo tiene eventos hasta el 14/12/2025.

Como `v_conversion_metrics` obtiene el `lead_date` desde `lead_events` (usando `MIN(event_date)`), y `v_payment_calculation` obtiene el `lead_date` desde `v_conversion_metrics`, toda la cadena se corta en `lead_events`.

## Verificación Necesaria

Para confirmar el diagnóstico, ejecutar:

```sql
-- Verificar fecha máxima en lead_events (cabinet)
SELECT 
    MAX(event_date) as max_event_date,
    COUNT(DISTINCT person_key) as total_persons,
    COUNT(DISTINCT person_key) FILTER (WHERE event_date >= '2025-12-15') as persons_since_dec15
FROM observational.lead_events
WHERE payload_json->>'origin_tag' = 'cabinet'
    OR source_table IN ('module_ct_cabinet_leads', 'module_ct_scouting_daily');
```

## Soluciones Posibles

### Opción 1: Actualizar `lead_events` con nuevos leads (RECOMENDADO)

**Problema:** `lead_events` no se está actualizando con nuevos leads después del 14/12/2025.

**Solución:**
1. Identificar qué proceso alimenta `lead_events`
2. Verificar por qué no está procesando leads después del 14/12
3. Ejecutar el proceso de ingesta para leads nuevos

**Pasos:**
- Verificar si hay nuevos leads en las tablas fuente (`module_ct_scouting_daily` o similar)
- Ejecutar corrida de ingesta para procesar leads nuevos
- Verificar que `lead_events` se actualice con nuevos eventos

### Opción 2: Usar `pay_date` como `lead_date` aproximado para pagos sin `lead_date`

**Problema:** Los pagos tienen `driver_id` y `person_key` pero no tienen `lead_date` en `v_conversion_metrics`.

**Solución:** Modificar `v_cabinet_financial_14d` para usar el `pay_date` más temprano como `lead_date` aproximado cuando no hay `lead_date` disponible.

**Pros:**
- Incluye todos los pagos con identidad completa
- Muestra pagos recientes

**Contras:**
- `pay_date` puede no ser igual a `lead_date` real
- Puede distorsionar la ventana de 14 días

### Opción 3: Usar `person_key` para obtener `lead_date` desde otras fuentes

**Solución:** Modificar `v_cabinet_financial_14d` para buscar `lead_date` desde otras fuentes usando `person_key` cuando no está disponible en `v_conversion_metrics`.

## Acción Inmediata Recomendada

1. **Verificar `lead_events`:**
   ```sql
   SELECT MAX(event_date) FROM observational.lead_events 
   WHERE payload_json->>'origin_tag' = 'cabinet';
   ```

2. **Si `lead_events` solo tiene datos hasta 14/12:**
   - Identificar qué proceso alimenta `lead_events`
   - Verificar si hay nuevos leads en tablas fuente
   - Ejecutar proceso de ingesta para leads nuevos

3. **Si `lead_events` tiene datos más recientes pero `v_conversion_metrics` no:**
   - Verificar la lógica de `v_conversion_metrics`
   - Verificar que el JOIN con `canon.identity_links` esté funcionando correctamente

## Nota Importante

La optimización realizada (usar `v_payment_calculation` directamente en lugar de `v_claims_payment_status_cabinet`) mejora el rendimiento, pero **no resuelve el problema de datos faltantes** si `lead_events` no tiene datos más recientes.

