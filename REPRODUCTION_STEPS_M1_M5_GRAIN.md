# Pasos de Reproducción: Problema de Grano Temporal M1/M5

## Objetivo
Evidenciar el problema donde M5 aparece como ✅ Alcanzado pero M1 aparece como "—", a pesar de que M1 fue alcanzado en una semana anterior.

## Pasos de Reproducción

1. **Ejecutar queries SQL de evidencia**:
   ```bash
   # Conectar a la base de datos
   psql $DATABASE_URL -f backend/scripts/sql/debug_m1_m5_grain_issue.sql
   ```
   
   O ejecutar manualmente en psql:
   ```sql
   -- PASO 1: Encontrar drivers con M5 achieved pero M1 no
   SELECT 
       'INCONSISTENCIA M5 sin M1' AS status,
       driver_id,
       driver_name,
       week_start,
       origin_tag,
       m1_achieved_flag,
       m1_achieved_date,
       m5_achieved_flag,
       m5_achieved_date,
       m1_yango_payment_status,
       m5_yango_payment_status
   FROM ops.v_payments_driver_matrix_cabinet
   WHERE m5_achieved_flag = true
       AND COALESCE(m1_achieved_flag, false) = false
   ORDER BY week_start DESC, driver_id
   LIMIT 10;
   ```

2. **Seleccionar un driver_id del resultado del PASO 1** (ej: `'abc123'`)

3. **Para ese driver, ejecutar queries de detalle** (reemplazar `'DRIVER_ID_AQUI'` con el driver_id seleccionado):
   ```sql
   -- PASO 2: Todas las filas del driver en matrix
   SELECT 
       'TODAS LAS FILAS DEL DRIVER EN MATRIX' AS status,
       driver_id,
       week_start,
       origin_tag,
       m1_achieved_flag,
       m1_achieved_date,
       m5_achieved_flag,
       m5_achieved_date,
       m25_achieved_flag,
       m25_achieved_date,
       m1_yango_payment_status,
       m5_yango_payment_status
   FROM ops.v_payments_driver_matrix_cabinet
   WHERE driver_id = 'DRIVER_ID_AQUI'
   ORDER BY week_start DESC;
   
   -- PASO 3: Milestones achieved (eventos puros)
   SELECT 
       'MILESTONES ACHIEVED (EVENTOS PUROS)' AS status,
       driver_id,
       milestone_value,
       achieved_flag,
       achieved_date,
       DATE_TRUNC('week', achieved_date)::date AS week_start_of_achieved_date,
       trips_at_achieved
   FROM ops.v_cabinet_milestones_achieved_from_trips
   WHERE driver_id = 'DRIVER_ID_AQUI'
   ORDER BY achieved_date;
   
   -- PASO 3B: Comparar week_start vs achieved_date
   SELECT 
       'COMPARACION WEEK_START vs ACHIEVED_DATE' AS status,
       m.driver_id,
       m.week_start AS matrix_week_start,
       m.m1_achieved_date,
       m.m5_achieved_date,
       DATE_TRUNC('week', m.m1_achieved_date)::date AS m1_week_start,
       DATE_TRUNC('week', m.m5_achieved_date)::date AS m5_week_start,
       CASE 
           WHEN DATE_TRUNC('week', m.m1_achieved_date)::date < m.week_start THEN 'M1 en semana anterior'
           WHEN DATE_TRUNC('week', m.m1_achieved_date)::date = m.week_start THEN 'M1 en misma semana'
           WHEN DATE_TRUNC('week', m.m1_achieved_date)::date > m.week_start THEN 'M1 en semana posterior'
           ELSE 'M1 sin fecha'
       END AS m1_week_comparison
   FROM ops.v_payments_driver_matrix_cabinet m
   WHERE m.driver_id = 'DRIVER_ID_AQUI';
   ```

4. **Obtener payload JSON del endpoint** (opcional, para verificar qué llega al frontend):
   ```bash
   # Si el backend está corriendo
   python backend/scripts/get_driver_matrix_payload.py DRIVER_ID_AQUI
   ```
   
   O usar curl:
   ```bash
   curl "http://localhost:8000/api/v1/ops/payments/driver-matrix?limit=200&offset=0" | jq '.data[] | select(.driver_id == "DRIVER_ID_AQUI")'
   ```

5. **Verificar en la UI**:
   - Abrir `/pagos/driver-matrix` o `/pagos/resumen-conductor`
   - Buscar el driver_id seleccionado
   - Confirmar que M5 aparece como ✅ Alcanzado pero M1 aparece como "—"

## Qué Buscar en los Resultados

1. **PASO 1**: Debe retornar al menos 1 driver con M5 achieved pero M1 no
2. **PASO 2**: Verificar cuántas filas tiene el driver en la vista matrix (debería ser 1 si el grano actual es solo por driver_id)
3. **PASO 3**: Verificar si hay M1 y M5 en `v_cabinet_milestones_achieved_from_trips` para ese driver
4. **PASO 3B**: Confirmar si `m1_achieved_date` está en una semana anterior a `week_start` de la fila en matrix

## Evidencia Esperada

Si la hipótesis es correcta, deberíamos ver:
- Driver con M5 achieved pero M1 no en la misma fila
- M1 existe en `v_cabinet_milestones_achieved_from_trips` pero con `achieved_date` en semana anterior
- `week_start` en matrix es de la semana de M5, no de M1
- Solo 1 fila por driver en matrix (no múltiples semanas)


