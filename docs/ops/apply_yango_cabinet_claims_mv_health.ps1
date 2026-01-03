# Script PowerShell para aplicar la vista de health check
# Ejecuta el script Python que aplica el SQL

$ErrorActionPreference = "Stop"

# Navegar al directorio del proyecto
$projectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$backendDir = Join-Path $projectRoot "backend"

# Activar entorno virtual si existe
$venvScripts = Join-Path $backendDir "venv\Scripts\Activate.ps1"
if (Test-Path $venvScripts) {
    Write-Host "Activando entorno virtual..." -ForegroundColor Cyan
    & $venvScripts
}

# Ejecutar el script Python
$scriptPath = Join-Path $backendDir "scripts\apply_yango_cabinet_claims_mv_health.py"
Write-Host "Ejecutando script Python: $scriptPath" -ForegroundColor Cyan

python $scriptPath

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al ejecutar el script" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n[OK] Script ejecutado exitosamente" -ForegroundColor Green

