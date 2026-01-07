# ✅ TODO Final - Sistema de Ingesta Automatizado

## ✅ COMPLETADO

### 1. Health Check
- ✅ `lead_events` agregado al monitoreo
- ✅ `ingestion_runs` agregado al monitoreo
- ✅ Ambas fuentes aparecen en dashboard de health

### 2. Scripts de Automatización
- ✅ `run_identity_ingestion_scheduled.py` - Script de ejecución
- ✅ `setup_identity_ingestion_task.ps1` - Script de configuración
- ✅ `run_ingestion_via_api.py` - Script de testing

### 3. Task Scheduler
- ✅ Tarea `CT4_Identity_Ingestion` creada
- ✅ Configurada para ejecutarse cada 6 horas
- ✅ Estado: Ready (lista para ejecutar)

## 🎯 Próximos Pasos Recomendados

### 1. Probar la Tarea Manualmente

```powershell
# Ejecutar la tarea manualmente para verificar que funciona
Start-ScheduledTask -TaskName CT4_Identity_Ingestion

# Ver el resultado
Get-ScheduledTaskInfo -TaskName CT4_Identity_Ingestion
```

### 2. Verificar que se Ejecute Automáticamente

La tarea está configurada para ejecutarse cada 6 horas. Para verificar:

```powershell
# Ver próximas ejecuciones
Get-ScheduledTask -TaskName CT4_Identity_Ingestion | Get-ScheduledTaskInfo

# Ver historial
Get-WinEvent -LogName Microsoft-Windows-TaskScheduler/Operational | 
    Where-Object {$_.Message -like "*CT4_Identity_Ingestion*"} | 
    Select-Object -First 10 TimeCreated, Message
```

### 3. Monitorear en Dashboard

1. Ir a: `http://localhost:3000/ops/data-health`
2. Verificar que `lead_events` e `ingestion_runs` aparezcan
3. Verificar que el estado sea GREEN si todo está bien

### 4. Ejecutar Primera Corrida (Si es Necesario)

Si no hay corridas previas o si `lead_events` está desactualizado:

```bash
# Opción 1: Vía script
python backend/scripts/run_ingestion_via_api.py

# Opción 2: Vía API directa
curl -X POST "http://localhost:8000/api/v1/identity/run?date_from=2025-12-15&date_to=2026-01-07"
```

## 📊 Verificación Periódica

### Diaria
- Verificar dashboard de health
- Verificar que `lead_events` se actualice
- Verificar que las ingestas se ejecuten

### Semanal
- Revisar logs de Task Scheduler
- Verificar que no haya errores en las ingestas
- Revisar estadísticas de `ingestion_runs`

## 🔧 Troubleshooting

### Si la tarea no se ejecuta automáticamente:
1. Verificar que Task Scheduler esté corriendo
2. Verificar permisos de la tarea
3. Revisar historial de ejecuciones en Task Scheduler

### Si la ingesta falla:
1. Verificar logs del script
2. Verificar conexión a base de datos
3. Verificar que el servidor API esté corriendo (si se usa vía API)

### Si `lead_events` no se actualiza:
1. Verificar que las ingestas se estén ejecutando
2. Verificar que el proceso de ingesta esté creando eventos
3. Revisar logs de `IngestionService`

## ✅ Estado Actual

**Sistema completamente configurado y listo para usar.**

La tarea `CT4_Identity_Ingestion` está creada y configurada para ejecutarse automáticamente cada 6 horas. El health check monitoreará el estado del sistema y alertará si hay problemas.

