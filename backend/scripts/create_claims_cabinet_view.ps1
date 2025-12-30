# Script para crear la vista ops.v_claims_payment_status_cabinet
# Ejecutar desde el directorio backend/

$ErrorActionPreference = "Stop"

# Leer configuración de base de datos desde config.py o usar valores por defecto
$DATABASE_URL = $env:DATABASE_URL
if (-not $DATABASE_URL) {
    # Valores por defecto (ajustar según tu configuración)
    $DB_HOST = "168.119.226.236"
    $DB_PORT = "5432"
    $DB_NAME = "yego_integral"
    $DB_USER = "yego_user"
    $DB_PASSWORD = "37>MNA&-35+"
    $DATABASE_URL = "postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
}

Write-Host "Creando vista ops.v_claims_payment_status_cabinet..." -ForegroundColor Cyan

# Extraer componentes de la URL de conexión
if ($DATABASE_URL -match "postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)") {
    $DB_USER = $matches[1]
    $DB_PASSWORD = $matches[2]
    $DB_HOST = $matches[3]
    $DB_PORT = $matches[4]
    $DB_NAME = $matches[5]
} else {
    Write-Host "Error: No se pudo parsear DATABASE_URL" -ForegroundColor Red
    exit 1
}

# Ruta al archivo SQL
$SQL_FILE = Join-Path $PSScriptRoot "..\sql\ops\v_claims_payment_status_cabinet.sql"

if (-not (Test-Path $SQL_FILE)) {
    Write-Host "Error: No se encontró el archivo SQL en: $SQL_FILE" -ForegroundColor Red
    exit 1
}

Write-Host "Ejecutando SQL desde: $SQL_FILE" -ForegroundColor Yellow
Write-Host "Conectando a: $DB_HOST:$DB_PORT/$DB_NAME como $DB_USER" -ForegroundColor Yellow

# Verificar si psql está disponible
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psqlPath) {
    Write-Host "Error: psql no está disponible. Instala PostgreSQL client tools." -ForegroundColor Red
    Write-Host "Alternativa: Ejecuta el SQL manualmente usando tu cliente PostgreSQL favorito." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Contenido del archivo SQL:" -ForegroundColor Cyan
    Get-Content $SQL_FILE
    exit 1
}

# Ejecutar SQL usando psql
$env:PGPASSWORD = $DB_PASSWORD
try {
    & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f $SQL_FILE
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n✅ Vista creada exitosamente!" -ForegroundColor Green
    } else {
        Write-Host "`n❌ Error al crear la vista. Código de salida: $LASTEXITCODE" -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "`n❌ Error al ejecutar SQL: $_" -ForegroundColor Red
    exit 1
} finally {
    Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host "`nVerificando que la vista existe..." -ForegroundColor Cyan
$checkQuery = "SELECT EXISTS (SELECT 1 FROM information_schema.views WHERE table_schema = 'ops' AND table_name = 'v_claims_payment_status_cabinet');"
$env:PGPASSWORD = $DB_PASSWORD
$result = echo $checkQuery | & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -A
Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue

if ($result -match "t|true|1") {
    Write-Host "✅ Vista verificada correctamente" -ForegroundColor Green
} else {
    Write-Host "⚠️  La vista podría no existir. Verifica manualmente." -ForegroundColor Yellow
}

