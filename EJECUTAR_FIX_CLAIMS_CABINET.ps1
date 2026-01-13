# ============================================================================
# Script de Ejecución: Fix Claims Cabinet 14d (M1/M5/M25)
# ============================================================================
# Aplica el fix de claims y crea la vista de auditoría
# ============================================================================

$ErrorActionPreference = "Stop"

# Configuración de base de datos
$DB_HOST = "168.119.226.236"
$DB_PORT = "5432"
$DB_NAME = "yego_integral"
$DB_USER = "yego_user"
$DB_PASSWORD = "37>MNA&-35+"

# Ruta del proyecto
$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"
$SqlDir = Join-Path $BackendDir "sql\ops"

Write-Host "`n========================================" -ForegroundColor Magenta
Write-Host "FIX CLAIMS CABINET 14D (M1/M5/M25)" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "Host: ${DB_HOST}:${DB_PORT}" -ForegroundColor Gray
Write-Host "Database: $DB_NAME" -ForegroundColor Gray
Write-Host "User: $DB_USER" -ForegroundColor Gray
Write-Host "========================================`n" -ForegroundColor Magenta

# Verificar que psql este disponible
try {
    $null = Get-Command psql -ErrorAction Stop
    Write-Host "OK: psql encontrado" -ForegroundColor Green
} catch {
    Write-Host "ERROR: psql no esta disponible en PATH" -ForegroundColor Red
    Write-Host "   Por favor, instala PostgreSQL o agrega psql al PATH" -ForegroundColor Yellow
    exit 1
}

# Función para ejecutar SQL
function Execute-SQL {
    param(
        [string]$SqlFile,
        [string]$Description
    )
    
    Write-Host "`n========================================" -ForegroundColor Cyan
    Write-Host "Ejecutando: $Description" -ForegroundColor Cyan
    Write-Host "Archivo: $SqlFile" -ForegroundColor Gray
    Write-Host "========================================`n" -ForegroundColor Cyan
    
    if (-not (Test-Path $SqlFile)) {
        Write-Host "ERROR: No se encuentra el archivo: $SqlFile" -ForegroundColor Red
        return $false
    }
    
    $env:PGPASSWORD = $DB_PASSWORD
    try {
        & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $SqlFile
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`nOK: $Description completado exitosamente" -ForegroundColor Green
            return $true
        } else {
            Write-Host "`nERROR: Error al ejecutar $Description (codigo: $LASTEXITCODE)" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "`nERROR: Error al ejecutar $Description : $_" -ForegroundColor Red
        return $false
    } finally {
        Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
    }
}

$success = $true

# Paso 1: Aplicar fix en v_claims_payment_status_cabinet
Write-Host "`nPASO 1: Aplicando fix en ops.v_claims_payment_status_cabinet..." -ForegroundColor Yellow
$fixFile = Join-Path $SqlDir "v_claims_payment_status_cabinet.sql"
    $result = Execute-SQL -SqlFile $fixFile -Description "Fix de vista de claims"
if (-not $result) {
    $success = $false
    Write-Host "`nADVERTENCIA: Error al aplicar el fix. Revisa los mensajes arriba." -ForegroundColor Yellow
    $continue = Read-Host "¿Deseas continuar con la creación de la vista de auditoría? (s/N)"
    if ($continue -ne "s" -and $continue -ne "S") {
        exit 1
    }
}

# Paso 2: Crear vista de auditoria
Write-Host "`nPASO 2: Creando vista de auditoria ops.v_cabinet_claims_audit_14d..." -ForegroundColor Yellow
$auditFile = Join-Path $SqlDir "v_cabinet_claims_audit_14d.sql"
$result = Execute-SQL -SqlFile $auditFile -Description "Creación de vista de auditoría"
if (-not $result) {
    $success = $false
}

# Paso 3: Validar el fix
Write-Host "`nPASO 3: Validando el fix..." -ForegroundColor Yellow
$validateFile = Join-Path $SqlDir "validate_claims_fix.sql"
if (Test-Path $validateFile) {
    $result = Execute-SQL -SqlFile $validateFile -Description "Validación del fix"
    if (-not $result) {
        $success = $false
    }
} else {
    Write-Host "ADVERTENCIA: Archivo de validacion no encontrado: $validateFile" -ForegroundColor Yellow
}

# Resumen final
Write-Host "`n========================================" -ForegroundColor Magenta
if ($success) {
    Write-Host "PROCESO COMPLETADO" -ForegroundColor Green
    Write-Host "`nProximos pasos:" -ForegroundColor Cyan
    Write-Host "1. Verifica los resultados de la validacion arriba" -ForegroundColor White
    Write-Host "2. Consulta la vista de auditoria:" -ForegroundColor White
    Write-Host "   SELECT * FROM ops.v_cabinet_claims_audit_14d WHERE missing_claim_bucket != 'NONE' LIMIT 10;" -ForegroundColor Gray
    Write-Host "3. Usa el endpoint de auditoria:" -ForegroundColor White
    Write-Host "   GET /api/v1/ops/payments/cabinet-financial-14d/claims-audit-summary" -ForegroundColor Gray
    Write-Host "4. Monitorea que los missing claims bajan significativamente" -ForegroundColor White
} else {
    Write-Host "PROCESO COMPLETADO CON ERRORES" -ForegroundColor Yellow
    Write-Host "   Revisa los mensajes de error arriba" -ForegroundColor White
}
Write-Host "========================================`n" -ForegroundColor Magenta

exit $(if ($success) { 0 } else { 1 })
