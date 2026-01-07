# Script para configurar Windows Task Scheduler para ejecutar ingesta de identidad automáticamente
# Ejecutar como Administrador: .\setup_identity_ingestion_task.ps1

$TaskName = "CT4_Identity_Ingestion"
$ScriptPath = Join-Path $PSScriptRoot "run_identity_ingestion_scheduled.py"
$WorkingDirectory = Split-Path $PSScriptRoot -Parent
$PythonPath = (Get-Command python).Source

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configurar Ingesta de Identidad Automática" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar que el script existe
if (-not (Test-Path $ScriptPath)) {
    Write-Host "[ERROR] Script no encontrado: $ScriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "Script: $ScriptPath" -ForegroundColor Gray
Write-Host "Working Directory: $WorkingDirectory" -ForegroundColor Gray
Write-Host "Python: $PythonPath" -ForegroundColor Gray
Write-Host ""

# Verificar si la tarea ya existe
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue

if ($existingTask) {
    Write-Host "Tarea existente encontrada. Eliminando..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Crear acción (ejecutar script Python)
$action = New-ScheduledTaskAction -Execute $PythonPath -Argument "`"$ScriptPath`"" -WorkingDirectory $WorkingDirectory

# Crear trigger (cada 6 horas)
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 6) -RepetitionDuration (New-TimeSpan -Days 365)

# Configuración de la tarea
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

# Principal (usuario actual)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest

# Verificar permisos de administrador
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (-not $isAdmin) {
    Write-Host "[ERROR] Este script requiere permisos de Administrador" -ForegroundColor Red
    Write-Host ""
    Write-Host "Para ejecutar como Administrador:" -ForegroundColor Yellow
    Write-Host "  1. Cerrar esta ventana" -ForegroundColor Gray
    Write-Host "  2. Buscar 'PowerShell' en el menú inicio" -ForegroundColor Gray
    Write-Host "  3. Clic derecho -> 'Ejecutar como administrador'" -ForegroundColor Gray
    Write-Host "  4. Navegar a: cd C:\cursor\CT4\backend\scripts" -ForegroundColor Gray
    Write-Host "  5. Ejecutar: .\setup_identity_ingestion_task.ps1" -ForegroundColor Gray
    Write-Host ""
    Write-Host "O configurar manualmente en Task Scheduler:" -ForegroundColor Yellow
    Write-Host "  1. Abrir 'Programador de tareas' (Task Scheduler)" -ForegroundColor Gray
    Write-Host "  2. Crear tarea básica" -ForegroundColor Gray
    Write-Host "  3. Nombre: CT4_Identity_Ingestion" -ForegroundColor Gray
    Write-Host "  4. Trigger: Repetir cada 6 horas" -ForegroundColor Gray
    Write-Host "  5. Acción: Ejecutar programa" -ForegroundColor Gray
    Write-Host "     - Programa: $PythonPath" -ForegroundColor Gray
    Write-Host "     - Argumentos: `"$ScriptPath`"" -ForegroundColor Gray
    Write-Host "     - Directorio: $WorkingDirectory" -ForegroundColor Gray
    exit 1
}

# Registrar tarea
try {
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "Ejecuta ingesta de identidad cada 6 horas para mantener lead_events actualizado" -ErrorAction Stop
    Write-Host "[OK] Tarea configurada exitosamente: $TaskName" -ForegroundColor Green
    Write-Host ""
    Write-Host "Comandos útiles:" -ForegroundColor Cyan
    Write-Host "  Get-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
    Write-Host "  Start-ScheduledTask -TaskName $TaskName" -ForegroundColor Gray
    Write-Host "  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false" -ForegroundColor Gray
} catch {
    Write-Host "[ERROR] Error configurando tarea: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Si el error persiste, configurar manualmente en Task Scheduler GUI" -ForegroundColor Yellow
    exit 1
}

