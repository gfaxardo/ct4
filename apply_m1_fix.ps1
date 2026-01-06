# Script para aplicar el fix de M1 achieved
# Uso: .\apply_m1_fix.ps1 [-DatabaseUrl "postgresql://user:pass@host:port/dbname"]
# Si no se proporciona DatabaseUrl, intentará leerlo de backend/app/config.py

param(
    [Parameter(Mandatory=$false)]
    [string]$DatabaseUrl
)

# Buscar psql
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue
if (-not $psqlPath) {
    $psqlPath = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
    if (-not (Test-Path $psqlPath)) {
        Write-Host "ERROR: No se encontró psql.exe" -ForegroundColor Red
        Write-Host "Por favor instala PostgreSQL o proporciona la ruta a psql.exe" -ForegroundColor Yellow
        exit 1
    }
} else {
    $psqlPath = $psqlPath.Source
}

# Si no se proporcionó DatabaseUrl, intentar leerlo de config.py
if (-not $DatabaseUrl) {
    if ($env:DATABASE_URL) {
        $DatabaseUrl = $env:DATABASE_URL
        Write-Host "DATABASE_URL encontrada en variable de entorno" -ForegroundColor Green
    } else {
        $configPath = "backend/app/config.py"
        if (Test-Path $configPath) {
            $configContent = Get-Content $configPath -Raw
            # Buscar database_url con diferentes patrones
            if ($configContent -match "database_url.*?=.*?['\`"]([^'\`"]+)['\`"]") {
                $DatabaseUrl = $matches[1]
                Write-Host "DATABASE_URL encontrada en config.py" -ForegroundColor Green
            } elseif ($configContent -match 'DATABASE_URL.*?=.*?["\x27]([^"\x27]+)["\x27]') {
                $DatabaseUrl = $matches[1]
                Write-Host "DATABASE_URL encontrada en config.py (alternativo)" -ForegroundColor Green
            }
        }
        
        if (-not $DatabaseUrl) {
            # Usar la URL por defecto del config.py (hardcoded como fallback)
            $DatabaseUrl = "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"
            Write-Host "Usando DATABASE_URL por defecto de config.py" -ForegroundColor Yellow
        }
    }
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Aplicando Fix M1 Achieved" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$hasError = $false

# 1. Aplicar vista actualizada
Write-Host "[1/3] Aplicando vista v_payments_driver_matrix_cabinet..." -ForegroundColor Yellow
& $psqlPath $DatabaseUrl -f backend/sql/ops/v_payments_driver_matrix_cabinet.sql
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Error aplicando vista v_payments_driver_matrix_cabinet" -ForegroundColor Red
    $hasError = $true
} else {
    Write-Host "✓ Vista aplicada correctamente" -ForegroundColor Green
}
Write-Host ""

    # 2. Ejecutar script de debug (opcional)
    Write-Host "[2/3] Ejecutando script de debug..." -ForegroundColor Yellow
& $psqlPath $DatabaseUrl -f backend/scripts/sql/debug_m1_achieved_gap.sql 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Debug ejecutado" -ForegroundColor Green
} else {
    Write-Host "⚠ Debug falló (continuando de todas formas)" -ForegroundColor Yellow
}
Write-Host ""

# 3. Ejecutar verificación completa
Write-Host "[3/3] Ejecutando verificación completa..." -ForegroundColor Yellow
& $psqlPath $DatabaseUrl -f backend/scripts/sql/verify_claims_achieved_source_fix.sql
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Error en verificación" -ForegroundColor Red
    $hasError = $true
} else {
    Write-Host "✓ Verificación ejecutada" -ForegroundColor Green
}
Write-Host ""

if ($hasError) {
    Write-Host "========================================" -ForegroundColor Red
    Write-Host "✗ Hubo errores durante la ejecución" -ForegroundColor Red
    Write-Host "========================================" -ForegroundColor Red
    exit 1
} else {
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "✓ Fix aplicado correctamente" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Próximos pasos:" -ForegroundColor Cyan
    Write-Host "1. Revisar los resultados de la verificación" -ForegroundColor White
    Write-Host "2. Validar en frontend que M1 se muestra como achieved" -ForegroundColor White
    Write-Host "3. Confirmar que CHECK M1-A muestra gap_count = 0" -ForegroundColor White
}

