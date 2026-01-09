# Setup Data Health - Observabilidad de Ingestas

## Paso 1: Verificar Tablas Existentes

Ejecutar primero:
```sql
\i backend/sql/ops/check_data_health_tables.sql
```

Esto listará qué tablas existen y cuáles faltan.

## Paso 2: Comentar CTEs de Tablas que NO Existen

Si alguna tabla opcional NO existe, editar `v_data_health.sql` y comentar:

### Para freshness_status:
- Si `raw.module_ct_cabinet_payments` no existe: comentar CTE `source_raw_module_ct_cabinet_payments` y su línea en UNION ALL
- Si `public.module_ct_cabinet_migrations` no existe: comentar CTE `source_module_ct_cabinet_migrations` y su línea en UNION ALL
- Si `public.module_ct_scout_drivers` no existe: comentar CTE `source_module_ct_scout_drivers` y su línea en UNION ALL
- Si `public.module_ct_cabinet_payments` no existe: comentar CTE `source_module_ct_cabinet_payments` y su línea en UNION ALL
- Si `public.module_ct_scouts_list` no existe: comentar CTE `source_module_ct_scouts_list` y su línea en UNION ALL

### Para ingestion_daily:
- Comentar las CTEs correspondientes `source_*_daily` y sus líneas en UNION ALL

## Paso 3: Ejecutar Vistas

```sql
\i backend/sql/ops/v_data_health.sql
```

## Paso 4: Validar

```sql
SELECT * FROM ops.v_data_sources_catalog ORDER BY source_name;
SELECT * FROM ops.v_data_freshness_status ORDER BY source_name;
SELECT * FROM ops.v_data_health_status ORDER BY source_type, source_name;
SELECT * FROM ops.v_data_ingestion_daily 
  WHERE metric_date >= CURRENT_DATE - 30 
  ORDER BY source_name, metric_type, metric_date DESC;
```

## Fuentes Incluidas

### Confirmadas (siempre incluidas):
- `summary_daily` (activity)
- `yango_payment_ledger` (ledger)
- `module_ct_cabinet_leads` (ct_ingest)
- `module_ct_scouting_daily` (ct_ingest)
- `drivers` (master)

### Opcionales (comentar si no existen):
- `raw_module_ct_cabinet_payments` (upstream) - CRÍTICA si existe
- `module_ct_cabinet_migrations` (ct_ingest)
- `module_ct_scout_drivers` (ct_ingest)
- `module_ct_cabinet_payments` (ct_ingest)
- `module_ct_scouts_list` (master)




