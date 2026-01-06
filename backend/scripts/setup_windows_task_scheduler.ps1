# ============================================================================
# Script PowerShell: Configurar Task Scheduler para Refresh Automático
# ============================================================================
# PROPÓSITO:
# Configurar automáticamente Task Scheduler para refrescar vista materializada
# cada hora
# ============================================================================
# USO:
# Ejecutar como Administrador: .\setup_windows_task_scheduler.ps1
# ============================================================================

# Requiere ejecutar como Administrador
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "ERROR: Este script requiere privilegios de Administrador" -ForegroundColor Red
    Write-Host "Ejecutar: Start-Process powershell -Verb RunAs" -ForegroundColor Yellow
    exit 1
}

$ErrorActionPreference = "Stop"

# Configuración
$taskName = "RefreshDriverMatrixMV"
$taskDescription = "Refrescar vista materializada ops.mv_payments_driver_matrix_cabinet cada hora"
$scriptPath = Join-Path $PSScriptRoot "refresh_mv_windows_task.ps1"
$workingDir = Split-Path $scriptPath -Parent

# Verificar que script existe
if (-not (Test-Path $scriptPath)) {
    Write-Host "ERROR: Script no encontrado en: $scriptPath" -ForegroundColor Red
    exit 1
}

try {
    Write-Host "Configurando Task Scheduler..." -ForegroundColor Cyan
    
    # Eliminar tarea si existe
    $existingTask = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "Eliminando tarea existente..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
    
    # Crear acción (ejecutar script PowerShell)
    $action = New-ScheduledTaskAction `
        -Execute "PowerShell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`"" `
        -WorkingDirectory $workingDir
    
    # Crear trigger (cada hora)
    $trigger = New-ScheduledTaskTrigger `
        -Once `
        -At (Get-Date) `
        -RepetitionInterval (New-TimeSpan -Hours 1) `
        -RepetitionDuration (New-TimeSpan -Days 9999)
    
    # Crear configuración
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RunOnlyIfNetworkAvailable `
        -RestartCount 3 `
        -RestartInterval (New-TimeSpan -Minutes 1)
    
    # Crear principal (ejecutar como usuario actual)
    $principal = New-ScheduledTaskPrincipal `
        -UserId $env:USERNAME `
        -LogonType Interactive `
        -RunLevel Highest
    
    # Registrar tarea
    Register-ScheduledTask `
        -TaskName $taskName `
        -Description $taskDescription `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Force | Out-Null
    
    Write-Host "`n✅ Tarea creada exitosamente!" -ForegroundColor Green
    Write-Host "`nDetalles de la tarea:" -ForegroundColor Cyan
    Write-Host "  Nombre: $taskName" -ForegroundColor White
    Write-Host "  Descripción: $taskDescription" -ForegroundColor White
    Write-Host "  Frecuencia: Cada hora" -ForegroundColor White
    Write-Host "  Script: $scriptPath" -ForegroundColor White
    
    Write-Host "`nPara verificar:" -ForegroundColor Yellow
    Write-Host "  Get-ScheduledTask -TaskName $taskName" -ForegroundColor White
    Write-Host "`nPara ejecutar manualmente:" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName $taskName" -ForegroundColor White
    Write-Host "`nPara eliminar:" -ForegroundColor Yellow
    Write-Host "  Unregister-ScheduledTask -TaskName $taskName -Confirm:`$false" -ForegroundColor White
    
} catch {
    Write-Host "ERROR: $_" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor Red
    exit 1
}

