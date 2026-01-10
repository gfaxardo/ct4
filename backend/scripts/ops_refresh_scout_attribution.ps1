# Job Recurrente: Scout Attribution Refresh (Windows)
# ===================================================
# Ejecuta refresh de scout attribution cada 4 horas (configurable).
#
# USO:
#   # Ejecutar una vez ahora
#   .\backend\scripts\ops_refresh_scout_attribution.ps1
#
#   # Programar con Task Scheduler:
#   # Acción: PowerShell -File "C:\path\to\CT4\backend\scripts\ops_refresh_scout_attribution.ps1"
#   # Frecuencia: Cada 4 horas

$ErrorActionPreference = "Stop"

# Cambiar al directorio del proyecto
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

# Ejecutar script Python
$pythonScript = Join-Path $scriptDir "run_scout_attribution_refresh.py"

Write-Host "Ejecutando scout attribution refresh..." -ForegroundColor Cyan
& python $pythonScript

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Scout attribution refresh completado" -ForegroundColor Green
    exit 0
} else {
    Write-Host "❌ Error en scout attribution refresh" -ForegroundColor Red
    exit 1
}

