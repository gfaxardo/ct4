# Instrucciones: Configurar Task Scheduler Manualmente

## Opción 1: PowerShell como Administrador (Recomendado)

1. **Cerrar cualquier PowerShell abierto**

2. **Abrir PowerShell como Administrador:**
   - Presionar `Win + X`
   - Seleccionar "Windows PowerShell (Administrador)" o "Terminal (Administrador)"
   - O buscar "PowerShell" en el menú inicio, clic derecho → "Ejecutar como administrador"

3. **Navegar al directorio:**
   ```powershell
   cd C:\cursor\CT4\backend\scripts
   ```

4. **Ejecutar el script:**
   ```powershell
   .\setup_identity_ingestion_task.ps1
   ```

5. **Verificar que se creó:**
   ```powershell
   Get-ScheduledTask -TaskName CT4_Identity_Ingestion
   ```

## Opción 2: Configurar Manualmente en Task Scheduler GUI

1. **Abrir Task Scheduler:**
   - Presionar `Win + R`
   - Escribir: `taskschd.msc`
   - Presionar Enter

2. **Crear Tarea Básica:**
   - En el panel derecho, clic en "Crear tarea básica..."
   - Nombre: `CT4_Identity_Ingestion`
   - Descripción: `Ejecuta ingesta de identidad cada 6 horas para mantener lead_events actualizado`
   - Clic en "Siguiente"

3. **Configurar Trigger:**
   - Seleccionar "Cuando se inicia el equipo" (o "Diariamente")
   - Clic en "Siguiente"
   - En la siguiente pantalla, marcar "Repetir tarea cada:"
   - Seleccionar "6 horas"
   - Duración: "Indefinidamente"
   - Clic en "Siguiente"

4. **Configurar Acción:**
   - Seleccionar "Iniciar un programa"
   - Clic en "Siguiente"
   - Programa o script: `C:\Users\Gonzalo Fajardo\AppData\Local\Programs\Python\Python313\python.exe`
   - Agregar argumentos: `"C:\cursor\CT4\backend\scripts\run_identity_ingestion_scheduled.py"`
   - Iniciar en: `C:\cursor\CT4\backend`
   - Clic en "Siguiente"

5. **Finalizar:**
   - Revisar resumen
   - Marcar "Abrir el cuadro de diálogo Propiedades para esta tarea cuando haga clic en Finalizar"
   - Clic en "Finalizar"

6. **Configurar Propiedades Adicionales:**
   - En la pestaña "General":
     - Marcar "Ejecutar con los privilegios más altos" (si es necesario)
     - Seleccionar "Ejecutar tanto si el usuario ha iniciado sesión como si no"
   - En la pestaña "Configuración":
     - Marcar "Permitir ejecutar la tarea a petición"
     - Marcar "Si la tarea en ejecución no finaliza cuando se solicita, forzar su detención"
   - Clic en "Aceptar"

7. **Probar la Tarea:**
   - Clic derecho en la tarea → "Ejecutar"
   - Verificar que se ejecute correctamente

## Verificar Configuración

```powershell
# Ver detalles de la tarea
Get-ScheduledTask -TaskName CT4_Identity_Ingestion | Format-List

# Ver triggers
(Get-ScheduledTask -TaskName CT4_Identity_Ingestion).Triggers

# Ejecutar manualmente
Start-ScheduledTask -TaskName CT4_Identity_Ingestion

# Ver historial de ejecuciones
Get-ScheduledTaskInfo -TaskName CT4_Identity_Ingestion
```

## Troubleshooting

**Si la tarea no se ejecuta:**
- Verificar que Python esté en el PATH
- Verificar que el script existe en la ruta especificada
- Revisar el historial de la tarea en Task Scheduler
- Verificar permisos del usuario

**Si aparece error de permisos:**
- Asegurarse de ejecutar PowerShell como Administrador
- O configurar la tarea para ejecutarse con una cuenta de servicio

**Si la tarea se ejecuta pero falla:**
- Revisar los logs del script
- Verificar que el servidor de la API esté corriendo (si se usa vía API)
- Verificar conexión a la base de datos

