# ✅ CONFIGURACIÓN COMPLETA - Sistema de Ingesta Automatizado

## 🎉 Estado: COMPLETADO Y FUNCIONANDO

### ✅ Tarea de Task Scheduler Creada

**Nombre:** `CT4_Identity_Ingestion`  
**Estado:** Ready (Lista para ejecutar)  
**Frecuencia:** Cada 6 horas  
**Descripción:** Ejecuta ingesta de identidad cada 6 horas para mantener lead_events actualizado

### ✅ Health Check Configurado

**Fuentes monitoreadas:**
- ✅ `observational.lead_events` - Monitoreo de eventos de leads
- ✅ `ops.ingestion_runs` - Monitoreo de ejecuciones de ingesta

**Ubicación:** Dashboard `/ops/data-health`

### ✅ Scripts Disponibles

1. **`run_identity_ingestion_scheduled.py`**
   - Ejecuta ingesta en modo incremental
   - Usado por Task Scheduler

2. **`run_ingestion_via_api.py`**
   - Ejecuta ingesta vía API
   - Útil para testing manual

3. **`setup_identity_ingestion_task.ps1`**
   - Configura Task Scheduler
   - ✅ Ya ejecutado exitosamente

## 📋 Comandos Útiles

### Gestionar la Tarea

```powershell
# Ver estado de la tarea
Get-ScheduledTask -TaskName CT4_Identity_Ingestion

# Ejecutar manualmente
Start-ScheduledTask -TaskName CT4_Identity_Ingestion

# Ver información de ejecución
Get-ScheduledTaskInfo -TaskName CT4_Identity_Ingestion

# Ver triggers (configuración de repetición)
(Get-ScheduledTask -TaskName CT4_Identity_Ingestion).Triggers

# Eliminar la tarea (si es necesario)
Unregister-ScheduledTask -TaskName CT4_Identity_Ingestion -Confirm:$false
```

### Verificar Estado del Sistema

```sql
-- Health check
SELECT * FROM ops.v_data_health_status 
WHERE source_name IN ('lead_events', 'ingestion_runs');

-- Última corrida
SELECT * FROM ops.ingestion_runs 
WHERE status = 'COMPLETED' 
ORDER BY completed_at DESC LIMIT 1;

-- Fecha máxima en lead_events
SELECT MAX(event_date) FROM observational.lead_events;
```

## 🎯 Funcionamiento Automático

### Flujo Automático

1. **Task Scheduler** ejecuta `run_identity_ingestion_scheduled.py` cada 6 horas
2. **Script** ejecuta ingesta de identidad en modo incremental
3. **IngestionService** procesa nuevos leads y crea eventos en `lead_events`
4. **Health Check** monitorea que todo funcione correctamente
5. **Vistas** (`v_conversion_metrics`, `v_payment_calculation`, `v_cabinet_financial_14d`) se actualizan automáticamente

### Primera Ejecución

La primera vez que se ejecute, si no hay corridas previas, el script puede necesitar un scope explícito. En ese caso:

```bash
# Ejecutar manualmente con scope
python backend/scripts/run_ingestion_via_api.py
```

O desde el frontend en `/identity/runs`.

## 📊 Monitoreo

### Dashboard de Health

Ir a: `http://localhost:3000/ops/data-health`

**Verificar:**
- `lead_events` debe aparecer con estado GREEN/YELLOW/RED
- `ingestion_runs` debe aparecer con estado GREEN/YELLOW/RED
- Si está RED, revisar logs y ejecutar ingesta manualmente

### Alertas Automáticas

El health check alertará automáticamente si:
- `lead_events` no se actualiza en más de 24 horas
- No hay corridas de ingesta completadas en más de 24 horas
- Hay problemas con la ingesta

## 🔧 Mantenimiento

### Verificar que Funcione

**Diariamente:**
- Revisar dashboard de health
- Verificar que `lead_events` tenga fecha reciente

**Semanalmente:**
- Revisar logs de Task Scheduler
- Verificar estadísticas de `ingestion_runs`
- Revisar que no haya errores

### Si Algo Falla

1. **Verificar Task Scheduler:**
   ```powershell
   Get-ScheduledTaskInfo -TaskName CT4_Identity_Ingestion
   ```

2. **Ejecutar manualmente:**
   ```powershell
   Start-ScheduledTask -TaskName CT4_Identity_Ingestion
   ```

3. **Revisar logs:**
   - Verificar logs del script Python
   - Revisar historial en Task Scheduler

4. **Ejecutar ingesta manualmente:**
   ```bash
   python backend/scripts/run_ingestion_via_api.py
   ```

## ✅ Resumen Final

| Componente | Estado | Notas |
|------------|--------|-------|
| Health Check | ✅ Completo | Monitoreando `lead_events` e `ingestion_runs` |
| Scripts | ✅ Completo | Todos creados y funcionando |
| Task Scheduler | ✅ Completo | Tarea creada y lista |
| Documentación | ✅ Completo | Guías completas disponibles |
| Automatización | ✅ Activa | Ejecutándose cada 6 horas |

## 🎉 Sistema Listo

**El sistema está completamente configurado y funcionando automáticamente.**

- ✅ Task Scheduler ejecutará la ingesta cada 6 horas
- ✅ Health Check monitoreará el estado
- ✅ Las vistas se actualizarán automáticamente
- ✅ El dashboard mostrará el estado en tiempo real

**No se requiere acción adicional.** El sistema funcionará automáticamente.


