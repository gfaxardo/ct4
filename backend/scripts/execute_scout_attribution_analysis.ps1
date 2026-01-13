# ============================================================================
# Script de Ejecución: Análisis de Atribución de Scouts
# ============================================================================
# Ejecuta los scripts SQL de diagnóstico y creación de vistas
# ============================================================================

param(
    [string]$DatabaseHost = "localhost",
    [string]$DatabasePort = "5432",
    [string]$DatabaseName = "ct4",
    [string]$DatabaseUser = "postgres",
    [string]$DatabasePassword = "",
    [switch]$DiagnoseOnly = $false,
    [switch]$CreateViewsOnly = $false
)

# Configurar variables de entorno si se proporciona password
if ($DatabasePassword) {
    $env:PGPASSWORD = $DatabasePassword
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
    
    $sqlContent = Get-Content -Path $SqlFile -Raw -ErrorAction Stop
    
    # Ejecutar con psql
    $psqlArgs = @(
        "-h", $DatabaseHost
        "-p", $DatabasePort
        "-U", $DatabaseUser
        "-d", $DatabaseName
        "-f", $SqlFile
    )
    
    try {
        & psql $psqlArgs
        if ($LASTEXITCODE -eq 0) {
            Write-Host "`n✅ $Description completado exitosamente" -ForegroundColor Green
            return $true
        } else {
            Write-Host "`n❌ Error al ejecutar $Description (código: $LASTEXITCODE)" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "`n❌ Error al ejecutar $Description : $_" -ForegroundColor Red
        return $false
    }
}

# Obtener ruta del script actual
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$SqlDir = Join-Path $ProjectRoot "backend\scripts\sql"

# Verificar que psql esté disponible
try {
    $null = Get-Command psql -ErrorAction Stop
    Write-Host "✅ psql encontrado" -ForegroundColor Green
} catch {
    Write-Host "❌ ERROR: psql no está disponible en PATH" -ForegroundColor Red
    Write-Host "   Por favor, instala PostgreSQL o agrega psql al PATH" -ForegroundColor Yellow
    exit 1
}

# Verificar que los archivos SQL existan
$DiagnoseFile = Join-Path $SqlDir "diagnose_scout_attribution.sql"
$RecommendationsFile = Join-Path $SqlDir "scout_attribution_recommendations.sql"

if (-not (Test-Path $DiagnoseFile)) {
    Write-Host "❌ ERROR: No se encuentra $DiagnoseFile" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $RecommendationsFile)) {
    Write-Host "❌ ERROR: No se encuentra $RecommendationsFile" -ForegroundColor Red
    exit 1
}

Write-Host "`n========================================" -ForegroundColor Magenta
Write-Host "ANÁLISIS DE ATRIBUCIÓN DE SCOUTS" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "Host: $DatabaseHost:$DatabasePort" -ForegroundColor Gray
Write-Host "Database: $DatabaseName" -ForegroundColor Gray
Write-Host "User: $DatabaseUser" -ForegroundColor Gray
Write-Host "========================================`n" -ForegroundColor Magenta

$success = $true

# Paso 1: Ejecutar diagnóstico
if (-not $CreateViewsOnly) {
    $result = Execute-SQL -SqlFile $DiagnoseFile -Description "Diagnóstico de Atribución de Scouts"
    if (-not $result) {
        $success = $false
        Write-Host "`n⚠️  El diagnóstico tuvo errores. Revisa los resultados antes de continuar." -ForegroundColor Yellow
        $continue = Read-Host "¿Deseas continuar con la creación de vistas? (s/N)"
        if ($continue -ne "s" -and $continue -ne "S") {
            exit 1
        }
    }
}

# Paso 2: Crear vistas (solo si no es solo diagnóstico)
if (-not $DiagnoseOnly) {
    Write-Host "`n⏳ Esperando 3 segundos antes de crear vistas..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    
    $result = Execute-SQL -SqlFile $RecommendationsFile -Description "Creación de Vistas de Atribución de Scouts"
    if (-not $result) {
        $success = $false
    }
}

# Resumen final
Write-Host "`n========================================" -ForegroundColor Magenta
if ($success) {
    Write-Host "✅ PROCESO COMPLETADO" -ForegroundColor Green
    Write-Host "`nPróximos pasos:" -ForegroundColor Cyan
    Write-Host "1. Revisa los resultados del diagnóstico" -ForegroundColor White
    Write-Host "2. Valida las vistas creadas:" -ForegroundColor White
    Write-Host "   SELECT * FROM ops.v_scout_attribution LIMIT 10;" -ForegroundColor Gray
    Write-Host "   SELECT * FROM ops.v_scout_attribution_conflicts LIMIT 10;" -ForegroundColor Gray
    Write-Host "3. Verifica cobertura y conflictos" -ForegroundColor White
} else {
    Write-Host "⚠️  PROCESO COMPLETADO CON ERRORES" -ForegroundColor Yellow
    Write-Host "   Revisa los mensajes de error arriba" -ForegroundColor White
}
Write-Host "========================================`n" -ForegroundColor Magenta

exit $(if ($success) { 0 } else { 1 })





