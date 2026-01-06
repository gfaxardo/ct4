# ============================================================================
# Script PowerShell: Refresh Vista Materializada (Windows Task Scheduler)
# ============================================================================
# PROPÓSITO:
# Script para ejecutar refresh de vista materializada desde Task Scheduler
# ============================================================================
# USO:
# Configurar en Task Scheduler para ejecutar cada hora
# ============================================================================

$ErrorActionPreference = "Stop"

# Configuración
$psqlPath = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
$databaseUrl = "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"
$scriptPath = Join-Path $PSScriptRoot "..\sql\refresh_mv_driver_matrix.sql"
$logPath = Join-Path $PSScriptRoot "..\..\refresh_mv_driver_matrix.log"

# Función de logging
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    Add-Content -Path $logPath -Value $logMessage
    Write-Host $logMessage
}

try {
    Write-Log "Iniciando refresh de vista materializada"
    Write-Log "Script: $scriptPath"
    
    # Verificar que psql existe
    if (-not (Test-Path $psqlPath)) {
        throw "psql no encontrado en: $psqlPath"
    }
    
    # Verificar que script existe
    if (-not (Test-Path $scriptPath)) {
        throw "Script no encontrado en: $scriptPath"
    }
    
    # Ejecutar refresh
    $result = & $psqlPath $databaseUrl -f $scriptPath 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Refresh completado exitosamente"
        if ($result) {
            Write-Log "Output: $result"
        }
        exit 0
    } else {
        throw "Refresh falló con código: $LASTEXITCODE. Output: $result"
    }
    
} catch {
    Write-Log "ERROR: $_" "ERROR"
    Write-Log $_.ScriptStackTrace "ERROR"
    exit 1
}

