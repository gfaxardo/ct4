# Script PowerShell para crear el índice único
# Ejecuta el script Python que aplica el SQL con autocommit

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
$scriptPath = Join-Path $backendDir "scripts\create_yango_cabinet_claims_unique_index.py"
Write-Host "Ejecutando script Python: $scriptPath" -ForegroundColor Cyan
Write-Host "NOTA: Este script usa autocommit para permitir CREATE INDEX CONCURRENTLY" -ForegroundColor Yellow

python $scriptPath

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error al ejecutar el script" -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host "`n[OK] Script ejecutado exitosamente" -ForegroundColor Green


