# Script PowerShell para ejecutar Scout Attribution Fix en Windows
# Encoding: UTF-8

$ErrorActionPreference = "Continue"

Write-Host "=============================================================================="
Write-Host "SCOUT ATTRIBUTION FIX - EJECUCION AUTOMATIZADA (Windows)"
Write-Host "=============================================================================="
Write-Host ""

# Verificar que estamos en el directorio correcto
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendPath = Join-Path $scriptPath ".."

Write-Host "Directorio del script: $scriptPath"
Write-Host "Directorio backend: $backendPath"
Write-Host ""

# Cambiar al directorio del script
Set-Location $scriptPath

# Verificar que existe Python
try {
    $pythonVersion = python --version
    Write-Host "[OK] Python encontrado: $pythonVersion"
} catch {
    Write-Host "[ERROR] Python no encontrado. Instalar Python primero."
    exit 1
}

# Ejecutar script Python
Write-Host ""
Write-Host "Ejecutando script Python..."
Write-Host ""

$scriptFile = Join-Path $scriptPath "execute_scout_attribution_fix.py"

if (-Not (Test-Path $scriptFile)) {
    Write-Host "[ERROR] No se encuentra el archivo: $scriptFile"
    exit 1
}

python $scriptFile

$exitCode = $LASTEXITCODE

Write-Host ""
Write-Host "=============================================================================="
if ($exitCode -eq 0) {
    Write-Host "[OK] PROCESO COMPLETADO"
} else {
    Write-Host "[ERROR] PROCESO COMPLETADO CON ERRORES (codigo: $exitCode)"
}
Write-Host "=============================================================================="

exit $exitCode

