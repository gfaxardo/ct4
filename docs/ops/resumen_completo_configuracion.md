# Resumen Completo: Configuración de Automatización y Monitoreo

## ✅ Cambios Implementados

### 1. Health Check Actualizado

**Fuentes agregadas:**
- ✅ `observational.lead_events` - Monitoreo de eventos de leads
- ✅ `ops.ingestion_runs` - Monitoreo de ejecuciones de ingesta

**Archivo modificado:** `backend/sql/ops/v_data_health.sql`

**Estado:** ✅ Ejecutado y verificado

### 2. Scripts Creados

**Scripts disponibles:**
- ✅ `backend/scripts/run_identity_ingestion_scheduled.py` - Ejecuta ingesta en modo incremental
- ✅ `backend/scripts/run_ingestion_via_api.py` - Ejecuta ingesta vía API (para testing)
- ✅ `backend/scripts/setup_identity_ingestion_task.ps1` - Configura Task Scheduler (Windows)

### 3. Verificaciones Realizadas

**Health Check:**
- ✅ `lead_events` aparece en el catálogo
- ✅ `ingestion_runs` aparece en el catálogo
- ✅ Ambas fuentes aparecen en `v_data_freshness_status`
- ✅ Ambas fuentes aparecen en `v_data_health_status`

## ⚠️ Acciones Pendientes (Requieren Permisos de Administrador)

### 1. Configurar Task Scheduler (Windows)

**El script intentó configurarse pero requiere permisos de administrador.**

**Para configurar manualmente:**

1. **Abrir PowerShell como Administrador:**
   ```powershell
   cd C:\cursor\CT4\backend\scripts
   .\setup_identity_ingestion_task.ps1
   ```

2. **O configurar manualmente en Task Scheduler:**
   - Abrir "Programador de tareas" (Task Scheduler)
   - Crear tarea básica
   - Nombre: `CT4_Identity_Ingestion`
   - Trigger: Repetir cada 6 horas
   - Acción: Ejecutar programa
     - Programa: `python.exe`
     - Argumentos: `"C:\cursor\CT4\backend\scripts\run_identity_ingestion_scheduled.py"`
     - Directorio de inicio: `C:\cursor\CT4\backend`

### 2. Ejecutar Primera Corrida de Ingesta

**Si no hay corridas previas, ejecutar manualmente:**

**Opción A: Vía API (si el servidor está corriendo):**
```bash
python backend/scripts/run_ingestion_via_api.py
```

**Opción B: Vía Endpoint directo:**
```bash
curl -X POST "http://localhost:8000/api/v1/identity/run?date_from=2025-12-15&date_to=2026-01-07"
```

**Opción C: Desde el frontend:**
- Ir a `/identity/runs`
- Hacer clic en "Ejecutar Ingesta"
- Configurar fechas si es necesario

## 📊 Verificación del Sistema

### Verificar Health Check

```sql
SELECT * FROM ops.v_data_health_status 
WHERE source_name IN ('lead_events', 'ingestion_runs');
```

### Verificar Última Corrida

```sql
SELECT 
    id,
    status,
    scope_date_from,
    scope_date_to,
    completed_at
FROM ops.ingestion_runs
WHERE status = 'COMPLETED'
ORDER BY completed_at DESC
LIMIT 1;
```

### Verificar lead_events

```sql
SELECT 
    MAX(event_date) as max_event_date,
    COUNT(*) as total_events
FROM observational.lead_events;
```

### Verificar v_cabinet_financial_14d

```sql
SELECT 
    MAX(lead_date) as max_lead_date,
    COUNT(*) as total_drivers
FROM ops.v_cabinet_financial_14d;
```

## 🎯 Estado Actual

- ✅ Health check configurado y funcionando
- ✅ Scripts de automatización creados
- ⚠️ Task Scheduler requiere configuración manual (permisos de admin)
- ⚠️ Primera corrida de ingesta debe ejecutarse manualmente

## 📝 Próximos Pasos Recomendados

1. **Ejecutar primera corrida de ingesta** (si no hay corridas previas)
2. **Configurar Task Scheduler** (como administrador)
3. **Verificar que el health check muestre GREEN** para ambas fuentes
4. **Monitorear que las ingestas se ejecuten automáticamente cada 6 horas**

## 🔍 Troubleshooting

**Si el health check muestra RED para `ingestion_runs`:**
- No hay corridas completadas recientes
- Ejecutar una corrida manualmente

**Si el health check muestra RED para `lead_events`:**
- `lead_events` no se está actualizando
- Verificar que las ingestas se estén ejecutando
- Verificar que el proceso de ingesta esté creando eventos en `lead_events`

**Si Task Scheduler no se configura:**
- Ejecutar PowerShell como Administrador
- O configurar manualmente en Task Scheduler GUI


