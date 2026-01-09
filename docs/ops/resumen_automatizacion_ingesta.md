# Resumen: Automatización y Monitoreo de Ingesta de Identidad

## ✅ Cambios Implementados

### 1. Agregado al Health Check

**Fuentes agregadas:**
- `observational.lead_events` - Tabla crítica para métricas de conversión
- `ops.ingestion_runs` - Monitoreo de ejecuciones de ingesta

**Archivo modificado:** `backend/sql/ops/v_data_health.sql`

**Cambios:**
- Agregado al catálogo de fuentes (`v_data_sources_catalog`)
- Agregadas CTEs para monitoreo (`source_lead_events`, `source_ingestion_runs`)
- Incluidas en `v_data_freshness_status` y `v_data_health_status`

### 2. Script de Automatización

**Archivo creado:** `backend/scripts/run_identity_ingestion_scheduled.py`

**Funcionalidad:**
- Ejecuta ingesta de identidad en modo incremental
- Diseñado para ejecutarse periódicamente (cron, task scheduler)
- Logging integrado

### 3. Script de Configuración (Windows)

**Archivo creado:** `backend/scripts/setup_identity_ingestion_task.ps1`

**Funcionalidad:**
- Configura Windows Task Scheduler
- Ejecuta ingesta cada 6 horas
- Fácil de configurar y mantener

## 📋 Próximos Pasos

### Paso 1: Verificar Health Check

```sql
SELECT * FROM ops.v_data_health_status 
WHERE source_name IN ('lead_events', 'ingestion_runs');
```

### Paso 2: Configurar Automatización

**Windows:**
```powershell
cd backend\scripts
.\setup_identity_ingestion_task.ps1
```

**Linux/Mac:**
```bash
# Agregar a crontab (cada 6 horas)
0 */6 * * * cd /path/to/CT4 && /path/to/python backend/scripts/run_identity_ingestion_scheduled.py >> /var/log/identity_ingestion.log 2>&1
```

### Paso 3: Verificar Funcionamiento

1. **Verificar última corrida:**
   ```sql
   SELECT MAX(completed_at) FROM ops.ingestion_runs 
   WHERE status = 'COMPLETED';
   ```

2. **Verificar lead_events actualizado:**
   ```sql
   SELECT MAX(event_date) FROM observational.lead_events;
   ```

3. **Verificar health check:**
   - Ir a `/ops/data-health` en el frontend
   - Verificar que `lead_events` e `ingestion_runs` aparezcan
   - Verificar que el estado sea GREEN si todo está bien

## 🎯 Beneficios

1. **Monitoreo Automático:**
   - Health check alerta si `lead_events` no se actualiza
   - Health check alerta si no hay corridas recientes

2. **Actualización Automática:**
   - `lead_events` se actualiza automáticamente cada 6 horas
   - Las vistas dependientes (`v_conversion_metrics`, `v_payment_calculation`, `v_cabinet_financial_14d`) se actualizan automáticamente

3. **Visibilidad:**
   - Se puede ver en el dashboard de health cuando fue la última corrida
   - Se puede ver cuándo fue la última actualización de `lead_events`

## ⚠️ Notas Importantes

- La primera corrida debe ejecutarse manualmente con scope explícito
- Después de la primera corrida, el modo incremental funciona automáticamente
- Si hay problemas, revisar logs en Task Scheduler o archivo de log configurado



