# Resultados de Ejecución: Análisis de Atribución de Scouts

## ✅ Estado: COMPLETADO

Las vistas se crearon exitosamente en la base de datos.

## 📊 Resumen de Resultados

Según la verificación ejecutada:

- **Total de atribuciones en raw:** 1,857
- **Personas distintas con scout:** 527
- **Drivers distintos con scout:** 151
- **Scouts distintos:** 26
- **Conflictos detectados:** 17

## 🎯 Vistas Creadas

1. **`ops.v_scout_attribution_raw`**
   - UNION ALL de todas las fuentes de atribución
   - Incluye: lead_ledger, lead_events, migrations, scouting_daily

2. **`ops.v_scout_attribution`**
   - Vista canónica con 1 fila por person_key/driver_id
   - Resuelve conflictos por prioridad y fecha

3. **`ops.v_scout_attribution_conflicts`**
   - Identifica casos donde un mismo driver tiene múltiples scouts
   - 17 conflictos detectados que requieren revisión manual

## 📝 Próximos Pasos

1. **Revisar conflictos:**
   ```sql
   SELECT * FROM ops.v_scout_attribution_conflicts
   ORDER BY distinct_scout_count DESC;
   ```

2. **Validar cobertura:**
   ```sql
   SELECT 
       source_table,
       COUNT(*) AS count,
       COUNT(DISTINCT person_key) AS distinct_persons
   FROM ops.v_scout_attribution
   GROUP BY source_table;
   ```

3. **Distribución por scout:**
   ```sql
   SELECT 
       scout_id,
       COUNT(*) AS attribution_count
   FROM ops.v_scout_attribution
   GROUP BY scout_id
   ORDER BY attribution_count DESC;
   ```

## ⚠️ Notas

- El diagnóstico tuvo un timeout en el bloque DO (esperado, algunas queries son pesadas)
- Las vistas se crearon correctamente a pesar del timeout en diagnóstico
- Los 17 conflictos deben resolverse manualmente o con reglas de negocio específicas



