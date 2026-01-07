# Script para configurar Windows Task Scheduler para refrescar la vista materializada
# ops.mv_cabinet_financial_14d diariamente

$ErrorActionPreference = "Stop"

# Configuración
$TaskName = "RefreshCabinetFinancial14d"
$ScriptPath = Join-Path $PSScriptRoot "refresh_mv_cabinet_financial_14d.py"
$PythonPath = (Get-Command python).Source
$WorkingDirectory = (Get-Item $PSScriptRoot).Parent.FullName

Write-Host "Configurando tarea programada: $TaskName" -ForegroundColor Yellow
Write-Host "Script: $ScriptPath" -ForegroundColor Gray
Write-Host "Python: $PythonPath" -ForegroundColor Gray
Write-Host "Directorio: $WorkingDirectory" -ForegroundColor Gray

# Verificar que el script existe
if (-not (Test-Path $ScriptPath)) {
    Write-Host "ERROR: No se encontró el script: $ScriptPath" -ForegroundColor Red
    exit 1
}

# Eliminar tarea existente si existe
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "Eliminando tarea existente..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Crear acción (ejecutar Python con el script)
$action = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptPath`"" -WorkingDirectory $WorkingDirectory

# Crear trigger (diariamente a las 2:00 AM)
$trigger = New-ScheduledTaskTrigger -Daily -At 2:00AM

# Configuración de la tarea
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Crear principal (ejecutar como usuario actual)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

# Registrar la tarea
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Refresca la vista materializada ops.mv_cabinet_financial_14d diariamente a las 2:00 AM"
    
    Write-Host "`n[OK] Tarea programada creada exitosamente!" -ForegroundColor Green
    Write-Host "`nDetalles de la tarea:" -ForegroundColor Yellow
    Write-Host "  Nombre: $TaskName" -ForegroundColor Gray
    Write-Host "  Ejecución: Diariamente a las 2:00 AM" -ForegroundColor Gray
    Write-Host "  Script: $ScriptPath" -ForegroundColor Gray
    Write-Host "`nPara verificar la tarea:" -ForegroundColor Yellow
    Write-Host "  Get-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
    Write-Host "`nPara ejecutar manualmente:" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
    Write-Host "`nPara eliminar la tarea:" -ForegroundColor Yellow
    Write-Host "  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false" -ForegroundColor Gray
    
} catch {
    Write-Host "`n[ERROR] Error al crear la tarea programada: $_" -ForegroundColor Red
    Write-Host "`nAsegúrate de ejecutar PowerShell como Administrador." -ForegroundColor Yellow
    exit 1
}

Write-Host "`n[OK] Proceso completado." -ForegroundColor Green


