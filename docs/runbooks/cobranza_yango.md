# Runbook: Cobranza Yango Cabinet 14d

## Descripción

Vista ejecutiva principal para cobranza, control y reconciliación de Yango. Utiliza la Materialized View `ops.mv_yango_cabinet_cobranza_enriched_14d` que incluye datos financieros + atribución scout canónica.

## Refresh de Materialized View

### Refresh Automático (Scheduler)

**Configuración recomendada:**
- Frecuencia: Diaria
- Hora: 02:00 AM (bajo tráfico)
- Comando: `REFRESH MATERIALIZED VIEW CONCURRENTLY ops.mv_yango_cabinet_cobranza_enriched_14d;`

**Configurar con cron (Linux/Mac):**
```bash
# Editar crontab
crontab -e

# Agregar línea (ejecuta diariamente a las 02:00 AM)
0 2 * * * psql $DATABASE_URL -c "REFRESH MATERIALIZED VIEW CONCURRENTLY ops.mv_yango_cabinet_cobranza_enriched_14d;" >> /var/log/mv_refresh.log 2>&1
```

**Configurar con systemd timer (Linux):**
```ini
# /etc/systemd/system/mv-refresh-cobranza.service
[Unit]
Description=Refresh MV Cobranza Yango
After=network.target

[Service]
Type=oneshot
Environment="DATABASE_URL=postgresql://..."
ExecStart=/usr/bin/psql $DATABASE_URL -c "REFRESH MATERIALIZED VIEW CONCURRENTLY ops.mv_yango_cabinet_cobranza_enriched_14d;"
```

```ini
# /etc/systemd/system/mv-refresh-cobranza.timer
[Unit]
Description=Daily refresh MV Cobranza Yango
Requires=mv-refresh-cobranza.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Manejo de errores:**
- Logs: Verificar `/var/log/mv_refresh.log` o logs del sistema
- Alerta: Configurar alerta si falla 3 veces consecutivas
- Monitoreo: Verificar que MV se refresca correctamente con script de validación

### Refresh Manual

**Cuándo usar:**
- Después de actualizaciones masivas de claims
- Después de cambios en atribución scout
- Cuando se necesita refresh inmediato

**Comando:**
```bash
psql $DATABASE_URL -c "REFRESH MATERIALIZED VIEW CONCURRENTLY ops.mv_yango_cabinet_cobranza_enriched_14d;"
```

**Tiempo estimado:** 5-30 segundos (depende del tamaño de datos)

## Validación

### Script de Validación Completa

Ejecutar después de refresh o cambios importantes:

```bash
cd backend
python scripts/validate_cobranza_yango_complete.py
```

**Qué valida:**
1. Conteos MV (total, con/sin scout, %)
2. Distribución por bucket de calidad
3. Top 20 drivers con milestone pero sin scout
4. Tests HTTP de endpoints (tabla, KPI scout, KPI weekly)
5. Correlación: SUM(debt_sum semanal) == deuda global (tolerancia 0)
6. Correlación: SUM(total_rows semanal) == total_count global
7. Performance: queries con filtros < 300ms

**Output:**
- Consola: Resumen de validaciones
- JSON: `backend/reports/cobranza_yango_validation_{timestamp}.json`

### Validación de Performance (SQL)

Ejecutar para verificar índices y performance:

```bash
psql $DATABASE_URL -f backend/scripts/sql/validate_cobranza_yango_perf.sql
```

**Qué verifica:**
- EXPLAIN ANALYZE de queries típicas
- Uso de índices
- Tiempos de ejecución

## Troubleshooting

### % con Scout < 90%

**Síntoma:** Porcentaje de drivers con scout atribuido es bajo.

**Causas posibles:**
1. Falta de datos en `ops.v_scout_attribution`
2. Drivers sin `person_key` (no tienen identidad canónica)
3. MV desactualizada (necesita refresh)

**Acciones:**
1. Verificar que `ops.v_scout_attribution` tiene datos:
   ```sql
   SELECT COUNT(*) FROM ops.v_scout_attribution;
   ```
2. Verificar drivers sin person_key:
   ```sql
   SELECT COUNT(*) 
   FROM ops.mv_yango_cabinet_cobranza_enriched_14d 
   WHERE person_key IS NULL AND scout_id IS NULL;
   ```
3. Refrescar MV:
   ```sql
   REFRESH MATERIALIZED VIEW CONCURRENTLY ops.mv_yango_cabinet_cobranza_enriched_14d;
   ```

### MV no existe o está desactualizada

**Síntoma:** Endpoint retorna error o datos antiguos.

**Acciones:**
1. Verificar que MV existe:
   ```sql
   SELECT EXISTS (
       SELECT 1 FROM pg_matviews 
       WHERE schemaname = 'ops' 
       AND matviewname = 'mv_yango_cabinet_cobranza_enriched_14d'
   );
   ```
2. Si no existe, crear:
   ```bash
   psql $DATABASE_URL -f backend/sql/ops/mv_yango_cabinet_cobranza_enriched_14d.sql
   ```
3. Si existe pero está desactualizada, refrescar (ver sección Refresh)

### Performance lenta (> 300ms)

**Síntoma:** Queries con filtros tardan más de 300ms.

**Acciones:**
1. Verificar índices:
   ```sql
   SELECT indexname, indexdef 
   FROM pg_indexes 
   WHERE schemaname = 'ops' 
   AND tablename = 'mv_yango_cabinet_cobranza_enriched_14d';
   ```
2. Ejecutar EXPLAIN ANALYZE:
   ```bash
   psql $DATABASE_URL -f backend/scripts/sql/validate_cobranza_yango_perf.sql
   ```
3. Si faltan índices, crearlos según `backend/sql/ops/mv_yango_cabinet_cobranza_enriched_14d.sql`
4. Si MV está fragmentada, recrear:
   ```sql
   DROP MATERIALIZED VIEW ops.mv_yango_cabinet_cobranza_enriched_14d CASCADE;
   -- Luego ejecutar script de creación
   ```

### Correlación falla (SUM semanal != global)

**Síntoma:** Script de validación reporta discrepancias en correlación.

**Causas posibles:**
1. Datos con `week_start IS NULL` (no se incluyen en agregación semanal)
2. Errores en cálculo de `week_start`
3. Datos duplicados o inconsistentes

**Acciones:**
1. Verificar filas con week_start NULL:
   ```sql
   SELECT COUNT(*) 
   FROM ops.mv_yango_cabinet_cobranza_enriched_14d 
   WHERE week_start IS NULL;
   ```
2. Verificar cálculo de week_start:
   ```sql
   SELECT 
       lead_date,
       week_start,
       DATE_TRUNC('week', lead_date)::date AS calculated_week_start
   FROM ops.mv_yango_cabinet_cobranza_enriched_14d
   WHERE week_start != DATE_TRUNC('week', lead_date)::date
   LIMIT 10;
   ```
3. Si hay discrepancias, refrescar MV o recrear

## Endpoints

### Tabla Principal
- `GET /api/v1/ops/payments/cabinet-financial-14d`
- Filtros: `only_with_debt`, `min_debt`, `reached_milestone`, `scout_id`, `week_start`
- Paginación: `limit`, `offset`

### KPIs Scout
- `GET /api/v1/yango/cabinet/cobranza-yango/scout-attribution-metrics`
- Cache: 60 segundos
- Retorna: métricas de atribución scout + top_missing_examples

### KPIs Semanales
- `GET /api/v1/yango/cabinet/cobranza-yango/weekly-kpis`
- Filtros: mismos que tabla + `week_start_from`, `week_start_to`, `limit_weeks` (default 52)
- Retorna: agregación por semana

### Export CSV
- `GET /api/v1/ops/payments/cabinet-financial-14d/export`
- Mismos filtros que tabla principal
- Incluye campos scout y week_start

## Estructura de Datos

### MV: `ops.mv_yango_cabinet_cobranza_enriched_14d`

**Campos financieros:**
- `driver_id`, `driver_name`, `lead_date`, `iso_week`, `week_start`
- `expected_amount_m1/m5/m25`, `total_paid_yango`, `amount_due_yango`
- Flags de milestones y claims

**Campos scout:**
- `scout_id`, `scout_name`, `scout_quality_bucket`
- `is_scout_resolved`, `scout_source_table`, `scout_attribution_date`, `scout_priority`
- `person_key`

**Índices:**
- `idx_mv_cobranza_enriched_driver_id_unique` (UNIQUE, para REFRESH CONCURRENTLY)
- `idx_mv_cobranza_enriched_week_start` (week_start DESC)
- `idx_mv_cobranza_enriched_scout_id` (partial: WHERE scout_id IS NOT NULL)
- `idx_mv_cobranza_enriched_debt_partial` (partial: WHERE amount_due_yango > 0)
- `idx_mv_cobranza_enriched_milestone_flags` (reached_m1_14d, reached_m5_14d, reached_m25_14d)
- `idx_mv_cobranza_enriched_scout_quality` (partial: WHERE scout_quality_bucket IS NOT NULL)

## Referencias

- SQL MV: `backend/sql/ops/mv_yango_cabinet_cobranza_enriched_14d.sql`
- Migration week_start: `backend/sql/ops/add_week_start_to_mv_cobranza.sql`
- Script validación: `backend/scripts/validate_cobranza_yango_complete.py`
- Script performance: `backend/scripts/sql/validate_cobranza_yango_perf.sql`
