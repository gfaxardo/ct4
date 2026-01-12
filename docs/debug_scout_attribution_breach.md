# Debug: Brecha de Drivers "Sin Scout" en Cobranza Yango

## Problema

En la vista `/pagos/cobranza-yango` (Cobranza Yango – Cabinet Financial 14d) hay una brecha grande de drivers con "Sin scout". Muchos drivers con metas operativas (M1/M5/M25) deberían tener scout, pero aparecen sin scout.

## Hipótesis a Validar

### H1: Join requiere lead_date exacto (demasiado restrictivo)
**Descripción**: El LEFT JOIN LATERAL en el endpoint requiere `driver_id = cf.driver_id AND lead_date = cf.lead_date`, lo cual puede ser demasiado restrictivo. Si un driver tiene scout atribuido pero en un lead_date diferente, no se muestra.

**Evidencia esperada en logs**: Si hay drivers con scout por `driver_id` pero no por `(driver_id, lead_date)`, esto confirma H1.

### H2: Drivers sin person_key (problema de identidad C0)
**Descripción**: Los drivers no tienen `person_key` asignado (gaps de identidad), por lo que no se puede hacer el join a `observational.lead_ledger` que requiere `person_key`.

**Evidencia esperada en logs**: Si hay drivers con milestones pero sin `person_key`, esto confirma H2.

### H3: Atribución scout a nivel person_key pero no a nivel driver_id
**Descripción**: La atribución scout existe a nivel `person_key` en `observational.lead_ledger`, pero no se propaga correctamente a nivel `driver_id` en `ops.v_yango_collection_with_scout`.

**Evidencia esperada en logs**: Si hay drivers con `person_key` y scout en `lead_ledger`, pero sin scout en `v_yango_collection_with_scout`, esto confirma H3.

### H4: Falta de datos en lead_ledger
**Descripción**: No hay suficientes datos en `observational.lead_ledger` con `attributed_scout_id` no nulo.

**Evidencia esperada en logs**: Si hay drivers con `person_key` pero sin scout en `lead_ledger`, esto confirma H4.

### H5: Múltiples lead_date por driver_id
**Descripción**: Un mismo `driver_id` tiene múltiples `lead_date`, y el join toma el incorrecto o no encuentra match.

**Evidencia esperada en logs**: Si hay muchos drivers con múltiples `lead_date`, esto sugiere H5.

## Instrumentación

Se ha añadido logging en el endpoint `/api/v1/ops/payments/cabinet-financial-14d` que captura:

1. **AFTER_QUERY_SCOUT_ATTRIBUTION**: Después de ejecutar la query principal
   - `rows_returned`: Total de filas retornadas
   - `rows_with_scout`: Cantidad de filas con scout_id no nulo
   - `rows_without_scout`: Cantidad de filas sin scout_id
   - `rows_with_milestones`: Cantidad de filas con milestones (M1/M5/M25)
   - `rows_with_milestones_no_scout`: Cantidad de filas con milestones pero sin scout
   - `pct_with_scout`: Porcentaje de filas con scout

2. **BEFORE_QUERY**: Antes de ejecutar la query principal
   - `view_name`: Nombre de la vista usada
   - `max_lead_date`: Fecha máxima en la vista

## Script SQL de Diagnóstico

Se ha creado `backend/scripts/sql/diagnostic_scout_attribution_breach.sql` que ejecuta:

- Sanity checks: Conteos base
- Test H1: Join por driver_id SOLO vs driver_id+lead_date
- Test H2: Drivers sin person_key
- Test H3: Scout por person_key vs por collection_view
- Test H4: Cobertura de lead_ledger
- Test H5: Múltiples lead_date por driver_id

## Próximos Pasos

1. Ejecutar el script SQL de diagnóstico para obtener evidencia inicial
2. Reproducir el problema accediendo a `/pagos/cobranza-yango`
3. Analizar los logs en `.cursor/debug.log`
4. Confirmar/rechazar hipótesis basado en evidencia
5. Implementar fix canónico
