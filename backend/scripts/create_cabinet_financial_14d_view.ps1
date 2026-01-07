# Script para crear la vista ops.v_cabinet_financial_14d
# Ejecuta el archivo SQL en PostgreSQL

$ErrorActionPreference = "Stop"

# Configuración de base de datos (desde config.py)
$dbHost = "168.119.226.236"
$dbPort = "5432"
$dbName = "yego_integral"
$dbUser = "yego_user"
$dbPassword = "37>MNA&-35+"

# Ruta del archivo SQL
$sqlFile = Join-Path $PSScriptRoot "..\sql\ops\v_cabinet_financial_14d.sql"

if (-not (Test-Path $sqlFile)) {
    Write-Host "ERROR: No se encontró el archivo SQL: $sqlFile" -ForegroundColor Red
    exit 1
}

Write-Host "Creando vista ops.v_cabinet_financial_14d..." -ForegroundColor Yellow
Write-Host "Archivo SQL: $sqlFile" -ForegroundColor Gray

# Leer contenido del archivo SQL
$sqlContent = Get-Content $sqlFile -Raw -Encoding UTF8

# Ejecutar con psql
$env:PGPASSWORD = $dbPassword

try {
    $sqlContent | & psql -h $dbHost -p $dbPort -U $dbUser -d $dbName -f -
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ Vista creada exitosamente!" -ForegroundColor Green
        Write-Host "`nVerificando..." -ForegroundColor Yellow
        
        # Verificar que la vista existe
        $verifyQuery = "SELECT COUNT(*) FROM ops.v_cabinet_financial_14d LIMIT 1;"
        $verifyResult = $verifyQuery | & psql -h $dbHost -p $dbPort -U $dbUser -d $dbName -t -A
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Vista verificada. La vista existe y es accesible." -ForegroundColor Green
        } else {
            Write-Host "⚠️  Vista creada pero no se pudo verificar." -ForegroundColor Yellow
        }
    } else {
        Write-Host "`n❌ Error al crear la vista. Revisa los mensajes de error arriba." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "`n❌ Error al ejecutar psql: $_" -ForegroundColor Red
    Write-Host "`nAsegúrate de tener psql instalado y en el PATH." -ForegroundColor Yellow
    Write-Host "O ejecuta el SQL manualmente desde un cliente PostgreSQL." -ForegroundColor Yellow
    exit 1
} finally {
    $env:PGPASSWORD = $null
}

Write-Host "`n✅ Proceso completado." -ForegroundColor Green


