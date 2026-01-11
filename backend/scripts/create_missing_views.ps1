# ============================================================================
# Script: create_missing_views.ps1
# ============================================================================
# Propósito: Crear vistas faltantes en la base de datos PostgreSQL
# Vistas a crear:
#   - ops.v_yango_collection_with_scout
#   - ops.v_claims_payment_status_cabinet
# ============================================================================

param(
    [string]$DatabaseHost = "168.119.226.236",
    [string]$DatabasePort = "5432",
    [string]$DatabaseName = "yego_integral",
    [string]$DatabaseUser = "yego_user",
    [string]$DatabasePassword = "37>MNA&-35+"
)

$ErrorActionPreference = "Stop"

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Script: Crear Vistas Faltantes en PostgreSQL" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Obtener el directorio del script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)

# Archivos SQL a ejecutar
$SqlFiles = @(
    @{
        Path = Join-Path $ProjectRoot "backend\scripts\sql\04_yango_collection_with_scout.sql"
        Name = "ops.v_yango_collection_with_scout"
        Description = "Vista de cobranza Yango con información de scout"
    },
    @{
        Path = Join-Path $ProjectRoot "backend\sql\ops\v_claims_payment_status_cabinet.sql"
        Name = "ops.v_claims_payment_status_cabinet"
        Description = "Vista de estado de pagos de claims cabinet"
    }
)

# Verificar que psql esté disponible
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psqlPath) {
    Write-Host "ERROR: psql no está disponible en PATH" -ForegroundColor Red
    Write-Host "Por favor, instala PostgreSQL Client Tools o agrega psql al PATH" -ForegroundColor Yellow
    exit 1
}

Write-Host "Verificando conexión a la base de datos..." -ForegroundColor Yellow
$env:PGPASSWORD = $DatabasePassword

# Construir comando de conexión
$ConnectionString = "-h $DatabaseHost -p $DatabasePort -U $DatabaseUser -d $DatabaseName"

# Verificar conexión
$TestQuery = "SELECT 1;"
try {
    $TestResult = & psql $ConnectionString -c $TestQuery 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Error de conexión: $TestResult"
    }
    Write-Host "✓ Conexión exitosa a la base de datos" -ForegroundColor Green
} catch {
    Write-Host "ERROR: No se pudo conectar a la base de datos" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Ejecutando archivos SQL..." -ForegroundColor Yellow
Write-Host ""

$SuccessCount = 0
$ErrorCount = 0

foreach ($SqlFile in $SqlFiles) {
    $FilePath = $SqlFile.Path
    $ViewName = $SqlFile.Name
    $Description = $SqlFile.Description
    
    Write-Host "------------------------------------------------------------------------" -ForegroundColor Cyan
    Write-Host "Procesando: $ViewName" -ForegroundColor White
    Write-Host "Descripción: $Description" -ForegroundColor Gray
    Write-Host "Archivo: $FilePath" -ForegroundColor Gray
    
    # Verificar que el archivo existe
    if (-not (Test-Path $FilePath)) {
        Write-Host "⚠ ADVERTENCIA: Archivo no encontrado: $FilePath" -ForegroundColor Yellow
        Write-Host "  Saltando esta vista..." -ForegroundColor Yellow
        $ErrorCount++
        Write-Host ""
        continue
    }
    
    # Ejecutar el archivo SQL
    try {
        Write-Host "Ejecutando SQL..." -ForegroundColor Yellow
        
        # Leer el contenido del archivo SQL
        $SqlContent = Get-Content $FilePath -Raw -Encoding UTF8
        
        # Ejecutar el SQL usando psql
        $Result = & psql $ConnectionString -c $SqlContent 2>&1
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Vista '$ViewName' creada exitosamente" -ForegroundColor Green
            $SuccessCount++
        } else {
            # Verificar si el error es porque la vista ya existe (no es crítico)
            $ErrorOutput = $Result -join "`n"
            if ($ErrorOutput -match "already exists" -or $ErrorOutput -match "does not exist" -and $ErrorOutput -match "DROP") {
                Write-Host "⚠ La vista ya existe o hay dependencias. Continuando..." -ForegroundColor Yellow
                $SuccessCount++
            } else {
                Write-Host "✗ Error al crear la vista '$ViewName'" -ForegroundColor Red
                Write-Host $ErrorOutput -ForegroundColor Red
                $ErrorCount++
            }
        }
    } catch {
        Write-Host "✗ Error al ejecutar SQL para '$ViewName'" -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        $ErrorCount++
    }
    
    Write-Host ""
}

# Resumen
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Resumen de Ejecución" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Vistas creadas exitosamente: $SuccessCount" -ForegroundColor Green
Write-Host "Errores: $ErrorCount" -ForegroundColor $(if ($ErrorCount -eq 0) { "Green" } else { "Red" })
Write-Host ""

# Verificar que las vistas existen
Write-Host "Verificando que las vistas existen..." -ForegroundColor Yellow
$VerifyQuery = @"
SELECT 
    schemaname || '.' || viewname AS view_name,
    CASE WHEN viewname IS NOT NULL THEN 'EXISTE' ELSE 'NO EXISTE' END AS status
FROM pg_views
WHERE schemaname = 'ops'
    AND viewname IN ('v_yango_collection_with_scout', 'v_claims_payment_status_cabinet')
ORDER BY viewname;
"@

try {
    $VerifyResult = & psql $ConnectionString -c $VerifyQuery 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host $VerifyResult
    } else {
        Write-Host "No se pudo verificar las vistas" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Error al verificar vistas: $($_.Exception.Message)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "Script completado" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan

# Limpiar variable de entorno
Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue

if ($ErrorCount -eq 0) {
    exit 0
} else {
    exit 1
}
