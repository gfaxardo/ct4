# Diagnóstico: v_cabinet_financial_14d solo muestra datos hasta 14/12/2025

## Problema Reportado

La vista `ops.v_cabinet_financial_14d` solo muestra datos hasta el **14/12/2025**, a pesar de que:
- Se insertaron 108 pagos nuevos (hasta el 05/01/2026)
- 97 de esos pagos tienen `driver_id` asignado
- Los pagos tienen `person_key` completo

## Análisis de la Cadena de Dependencias

### Flujo de Datos:

```
1. ops.yango_payment_status_ledger (pagos insertados)
   ↓ (requiere driver_id o person_key)
2. ops.v_yango_payments_ledger_latest_enriched (enriquecimiento)
   ↓ (requiere driver_id_final)
3. ops.v_claims_payment_status_cabinet (claims con pagos)
   ↓ (requiere lead_date desde v_payment_calculation)
4. ops.v_cabinet_financial_14d (vista final)
```

### Puntos de Filtrado:

1. **`v_claims_payment_status_cabinet`**:
   - Requiere `lead_date` desde `v_payment_calculation`
   - `v_payment_calculation` obtiene `lead_date` desde `v_conversion_metrics` con `origin_tag = 'cabinet'`
   - Si un driver no tiene `lead_date` en `v_conversion_metrics` (cabinet), no aparecerá en claims

2. **`v_cabinet_financial_14d`**:
   - Requiere `lead_date` desde `v_conversion_metrics` (cabinet)
   - Solo incluye drivers que tienen `lead_date` en `v_conversion_metrics` con `origin_tag = 'cabinet'`
   - Si un driver no tiene `lead_date`, no aparecerá en la vista

## Causa Raíz

Los pagos insertados tienen `driver_id` o `person_key`, pero:
- Los drivers pueden no tener `lead_date` en `v_conversion_metrics` con `origin_tag = 'cabinet'`
- O los drivers pueden tener `lead_date` pero solo hasta el 14/12/2025

## Soluciones Posibles

### Opción 1: Incluir pagos usando `pay_date` como `lead_date` aproximado

Modificar `v_cabinet_financial_14d` para incluir también pagos que tienen `driver_id` o `person_key` pero no tienen `lead_date` en `v_conversion_metrics`, usando el `pay_date` como `lead_date` aproximado.

**Pros:**
- Incluye todos los pagos con identidad completa
- Muestra pagos recientes

**Contras:**
- `pay_date` puede no ser igual a `lead_date` real
- Puede distorsionar la ventana de 14 días

### Opción 2: Verificar y corregir `v_conversion_metrics`

Verificar por qué los drivers con pagos recientes no tienen `lead_date` en `v_conversion_metrics` (cabinet) y corregir la fuente de datos.

**Pros:**
- Mantiene la integridad de los datos
- `lead_date` es la fecha real del lead

**Contras:**
- Requiere corregir la fuente upstream
- Puede tomar tiempo

### Opción 3: Usar `lead_date` desde claims cuando no está en conversion_metrics

Modificar `v_cabinet_financial_14d` para usar `lead_date` desde `v_claims_payment_status_cabinet` cuando el driver no está en `v_conversion_metrics`.

**Pros:**
- Usa `lead_date` real (desde claims)
- Incluye drivers con pagos pero sin conversion_metrics

**Contras:**
- Puede incluir drivers que no son realmente de cabinet
- Requiere validación adicional

## Recomendación

**Opción 3** es la más práctica: usar `lead_date` desde `v_claims_payment_status_cabinet` cuando el driver no está en `v_conversion_metrics`, pero solo para drivers que tienen pagos con `driver_id` o `person_key` completo.

Esto asegura que:
- Todos los pagos con identidad completa aparezcan en la vista
- Se use `lead_date` real cuando esté disponible
- Se mantenga la integridad de la ventana de 14 días



