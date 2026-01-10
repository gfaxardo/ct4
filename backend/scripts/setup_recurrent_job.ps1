# Script de configuración para Job Recurrente de Scout Attribution
# Windows Task Scheduler

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Configuración Job Recurrente Scout Attribution" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$scriptPath = Join-Path $PSScriptRoot "ops_refresh_scout_attribution.ps1"
$projectRoot = Split-Path (Split-Path $PSScriptRoot)

Write-Host "Script: $scriptPath" -ForegroundColor Yellow
Write-Host "Proyecto: $projectRoot" -ForegroundColor Yellow
Write-Host ""

# Verificar que el script existe
if (-not (Test-Path $scriptPath)) {
    Write-Host "[ERROR] Script no encontrado: $scriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "Para configurar el job recurrente en Windows Task Scheduler:" -ForegroundColor Green
Write-Host ""
Write-Host "1. Abre Task Scheduler (tareaschd.msc)" -ForegroundColor White
Write-Host "2. Crea una nueva tarea básica" -ForegroundColor White
Write-Host "3. Nombre: 'Scout Attribution Refresh'" -ForegroundColor White
Write-Host "4. Trigger: Recurrente cada 4 horas" -ForegroundColor White
Write-Host "5. Acción: Iniciar programa" -ForegroundColor White
Write-Host "6. Programa: powershell.exe" -ForegroundColor White
Write-Host "7. Argumentos: -ExecutionPolicy Bypass -File `"$scriptPath`"" -ForegroundColor White
Write-Host "8. Directorio de inicio: `"$projectRoot`"" -ForegroundColor White
Write-Host ""
Write-Host "O ejecuta manualmente:" -ForegroundColor Green
Write-Host "  cd `"$projectRoot`"" -ForegroundColor Yellow
Write-Host "  powershell -ExecutionPolicy Bypass -File `"$scriptPath`"" -ForegroundColor Yellow
Write-Host ""

# Probar ejecución manual
$response = Read-Host "¿Deseas probar la ejecución ahora? (S/N)"
if ($response -eq "S" -or $response -eq "s") {
    Write-Host ""
    Write-Host "Ejecutando script..." -ForegroundColor Cyan
    Set-Location $projectRoot
    & powershell -ExecutionPolicy Bypass -File $scriptPath
}

