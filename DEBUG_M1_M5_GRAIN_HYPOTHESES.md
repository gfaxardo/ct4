# Hipótesis: Problema de Grano Temporal M1/M5

## Síntoma
En UI Driver Matrix y Resumen por Conductor hay filas donde:
- M5 aparece como ✅ Alcanzado (UNPAID/PAID/etc.)
- pero M1 aparece como "—"

## Hipótesis Generadas

### H1: Agregación por driver_id sin carry-forward semanal
**Descripción**: La vista `v_payments_driver_matrix_cabinet` agrega milestones por `driver_id` solamente, sin considerar `week_start`. Si M1 fue alcanzado en semana 1 y M5 en semana 2, la vista solo muestra 1 fila (probablemente con `week_start` de la semana más reciente), y M1 puede no aparecer si no hay claim asociado a esa semana.

**Evidencia esperada**:
- Query 1: Drivers con M5 achieved pero M1 no en la misma fila
- Query 2: Verificar que la vista solo tiene 1 fila por driver (no múltiples semanas)
- Query 3: Verificar que `v_cabinet_milestones_achieved_from_trips` tiene M1 y M5 en semanas diferentes

**Confianza**: ALTA (basado en código actual)

### H2: week_start calculado desde achieved_date más reciente
**Descripción**: El `week_start` se calcula desde `lead_date` o `achieved_date` más reciente. Si M5 fue alcanzado después de M1, el `week_start` será de la semana de M5, y M1 puede no aparecer si no hay claim en esa semana.

**Evidencia esperada**:
- Query 4: Comparar `week_start` en matrix vs `achieved_date` de milestones
- Query 5: Verificar si hay drivers con múltiples `achieved_date` en diferentes semanas

**Confianza**: MEDIA

### H3: Join sin considerar semana de achieved_date
**Descripción**: El join entre `deterministic_milestones_agg` y `claims_agg` no considera la semana de `achieved_date`. Si M1 fue alcanzado en semana 1 pero solo hay claim para M5 en semana 2, M1 puede no aparecer.

**Evidencia esperada**:
- Query 6: Comparar `achieved_date` de milestones vs `week_start` de claims
- Query 7: Verificar si hay milestones achieved sin claim en la misma semana

**Confidencia**: MEDIA

### H4: Grano actual es solo por driver_id, no por (driver_id, week_start)
**Descripción**: Aunque la documentación dice que el grano es por `(driver_id, week_start, origin_tag)`, la implementación actual solo agrega por `driver_id`, resultando en 1 fila por driver.

**Evidencia esperada**:
- Query 8: Contar filas por driver en la vista matrix
- Query 9: Verificar si hay drivers con múltiples semanas distintas

**Confianza**: ALTA (basado en código: `GROUP BY bc.driver_id`)

### H5: Milestones achieved en semanas anteriores no se propagan
**Descripción**: Si M1 fue alcanzado en semana 1 y M5 en semana 2, la vista actual no hace "carry-forward" de M1 a la semana 2. Solo muestra milestones de la semana más reciente.

**Evidencia esperada**:
- Query 10: Verificar si hay drivers con M1 en semana anterior y M5 en semana posterior
- Query 11: Verificar si la vista muestra M1 cuando `achieved_date` es anterior a `week_start`

**Confianza**: ALTA (es el problema principal según el usuario)

## Plan de Evidencia

1. Ejecutar queries de debug para encontrar drivers con el problema
2. Para un driver específico, mostrar:
   - Todas las filas en `v_payments_driver_matrix_cabinet`
   - Todos los milestones en `v_cabinet_milestones_achieved_from_trips`
   - Comparar `week_start` vs `achieved_date`
3. Confirmar si M1 está logrado pero en semana anterior


