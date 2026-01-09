# Automatización del Proceso de Ingesta de Identidad

## Problema Identificado

El proceso de ingesta de identidad (`POST /api/v1/identity/run`) **NO está automatizado** y **NO está monitoreado en el health check**, lo que causa:

1. **`observational.lead_events` no se actualiza automáticamente**
2. **Las vistas dependientes (`v_conversion_metrics`, `v_payment_calculation`, `v_cabinet_financial_14d`) se quedan con datos antiguos**
3. **No hay alertas cuando el proceso falla o no se ejecuta**

## Estado Actual

### ❌ No Automatizado

- No hay cron job configurado
- No hay task scheduler configurado
- No hay proceso automático que ejecute la ingesta

### ❌ No Monitoreado en Health Check

El health check (`ops.v_data_health_status`) **NO incluye**:
- `observational.lead_events` (tabla crítica)
- `ops.ingestion_runs` (para verificar ejecuciones)
- Proceso de ingesta en sí

### ⚠️ Fuentes Comentadas

En `v_data_health.sql`, `module_ct_cabinet_leads` está comentado (líneas 68-71), lo que impide monitorear si hay nuevos leads.

## Soluciones Requeridas

### 1. Agregar al Health Check

**Agregar `observational.lead_events` al catálogo:**
```sql
('lead_events', 'observational', 'lead_events', 'ct_ingest',
 'event_date',
 'created_at::timestamptz'),
```

**Agregar `ops.ingestion_runs` para monitorear ejecuciones:**
```sql
('ingestion_runs', 'ops', 'ingestion_runs', 'master',
 'COALESCE(scope_date_to, completed_at::date)',
 'completed_at::timestamptz'),
```

**Agregar check de última corrida exitosa:**
- Verificar que la última corrida completada sea reciente (ej: < 24 horas)
- Alertar si no hay corridas recientes

### 2. Automatizar el Proceso

**Opción A: Script Python con Task Scheduler (Windows)**
```python
# backend/scripts/run_identity_ingestion_scheduled.py
from app.db import SessionLocal
from app.services.ingestion import IngestionService
from datetime import date, timedelta

def run_ingestion():
    db = SessionLocal()
    try:
        service = IngestionService(db)
        # Modo incremental: procesa desde la última corrida
        run = service.run_ingestion(incremental=True)
        print(f"Ingesta completada: run_id={run.id}")
    finally:
        db.close()

if __name__ == "__main__":
    run_ingestion()
```

**Configurar en Windows Task Scheduler:**
- Ejecutar cada hora o cada 6 horas
- Usar script similar a `setup_refresh_cabinet_financial_task.ps1`

**Opción B: Cron Job (Linux/Mac)**
```bash
# Ejecutar cada 6 horas
0 */6 * * * cd /path/to/CT4 && /path/to/python backend/scripts/run_identity_ingestion_scheduled.py >> /var/log/identity_ingestion.log 2>&1
```

**Opción C: Endpoint de Health Check que Ejecuta Automáticamente**

Crear un endpoint que:
1. Verifica si la última corrida es reciente
2. Si no, ejecuta automáticamente una corrida incremental
3. Se puede llamar desde un cron job o health check externo

### 3. Agregar Alertas

**En el health check, agregar regla:**
- Si la última corrida completada es > 24 horas → `YELLOW_INGESTION_STALE`
- Si la última corrida completada es > 48 horas → `RED_INGESTION_STALE`
- Si no hay corridas completadas → `RED_NO_INGESTION`

## Implementación Recomendada

### Paso 1: Agregar al Health Check

1. Agregar `lead_events` al catálogo
2. Agregar `ingestion_runs` al catálogo
3. Agregar check de última corrida exitosa

### Paso 2: Crear Script de Automatización

1. Crear `backend/scripts/run_identity_ingestion_scheduled.py`
2. Crear script PowerShell para configurar Task Scheduler
3. Documentar configuración

### Paso 3: Configurar Automatización

1. Configurar Task Scheduler (Windows) o Cron (Linux)
2. Ejecutar cada 6 horas (o según necesidad)
3. Verificar que funcione correctamente

## Verificación

Después de implementar:

1. **Verificar health check:**
   ```sql
   SELECT * FROM ops.v_data_health_status 
   WHERE source_name IN ('lead_events', 'ingestion_runs');
   ```

2. **Verificar última corrida:**
   ```sql
   SELECT MAX(completed_at) FROM ops.ingestion_runs 
   WHERE status = 'COMPLETED';
   ```

3. **Verificar lead_events actualizado:**
   ```sql
   SELECT MAX(event_date) FROM observational.lead_events;
   ```



