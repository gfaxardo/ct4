# Script PowerShell para configurar Task Scheduler en Windows
# Ejecutar como administrador: .\setup_scheduler_identity_gap.ps1

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Configuración de Task Scheduler: Identity Gap Recovery" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Obtener ruta del proyecto
$projectPath = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$backendPath = Join-Path $projectPath "backend"

# Verificar que existe
if (-not (Test-Path $backendPath)) {
    Write-Host "Error: No se encontró el directorio backend en: $backendPath" -ForegroundColor Red
    exit 1
}

Write-Host "Directorio backend: $backendPath" -ForegroundColor Green
Write-Host ""

# Obtener ruta de Python
$pythonPath = (Get-Command python).Source
if (-not $pythonPath) {
    Write-Host "Error: Python no encontrado en PATH" -ForegroundColor Red
    exit 1
}

Write-Host "Python encontrado: $pythonPath" -ForegroundColor Green
Write-Host ""

# Crear acción
$action = New-ScheduledTaskAction `
    -Execute $pythonPath `
    -Argument "-m jobs.retry_identity_matching 500" `
    -WorkingDirectory $backendPath

# Crear trigger (diariamente a las 2 AM)
$trigger = New-ScheduledTaskTrigger -Daily -At 2am

# Crear configuración
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Hours 1)

# Crear principal (ejecutar como usuario actual)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

# Registrar tarea
try {
    Register-ScheduledTask `
        -TaskName "Identity Gap Recovery" `
        -Action $action `
        -Trigger $trigger `
        -Settings $settings `
        -Principal $principal `
        -Description "Ejecuta job de recovery de identity gap diariamente a las 2 AM" `
        -Force
    
    Write-Host "Tarea programada creada exitosamente!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Detalles:" -ForegroundColor Cyan
    Write-Host "  - Nombre: Identity Gap Recovery" -ForegroundColor White
    Write-Host "  - Frecuencia: Diariamente a las 2:00 AM" -ForegroundColor White
    Write-Host "  - Comando: python -m jobs.retry_identity_matching 500" -ForegroundColor White
    Write-Host "  - Directorio: $backendPath" -ForegroundColor White
    Write-Host ""
    Write-Host "Para verificar:" -ForegroundColor Yellow
    Write-Host "  Get-ScheduledTask -TaskName 'Identity Gap Recovery'" -ForegroundColor White
    Write-Host ""
    Write-Host "Para ejecutar manualmente:" -ForegroundColor Yellow
    Write-Host "  Start-ScheduledTask -TaskName 'Identity Gap Recovery'" -ForegroundColor White
    Write-Host ""
    Write-Host "Para eliminar:" -ForegroundColor Yellow
    Write-Host "  Unregister-ScheduledTask -TaskName 'Identity Gap Recovery' -Confirm:`$false" -ForegroundColor White
    
} catch {
    Write-Host "Error al crear la tarea programada: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Configuración completada" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
