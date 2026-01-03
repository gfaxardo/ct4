# ============================================================================
# Script de Validación: Endpoints Yango Cabinet Claims
# ============================================================================
# PROPÓSITO:
# Validación mínima (smoke tests) de los endpoints de Yango Cabinet Claims
# usando curl o Invoke-WebRequest.
#
# USO:
#   .\docs\ops\test_yango_cabinet_endpoints.ps1
#   .\docs\ops\test_yango_cabinet_endpoints.ps1 -BaseUrl "http://localhost:8000"
# ============================================================================

param(
    [string]$BaseUrl = "http://localhost:8000",
    [switch]$FailFast = $false
)

$ErrorActionPreference = "Continue"

Write-Host "`n=== Validación de Endpoints Yango Cabinet Claims ===" -ForegroundColor Cyan
Write-Host "Base URL: $BaseUrl`n" -ForegroundColor Gray

$testsPassed = 0
$testsFailed = 0

# Helper function
function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Method = "GET",
        [int]$ExpectedStatus = 200
    )
    
    Write-Host "[TEST] $Name" -ForegroundColor Yellow
    Write-Host "  URL: $Url" -ForegroundColor Gray
    
    try {
        $response = Invoke-WebRequest -Uri $Url -Method $Method -UseBasicParsing -ErrorAction Stop
        $statusCode = $response.StatusCode
        
        if ($statusCode -eq $ExpectedStatus) {
            Write-Host "  ✓ Status: $statusCode (OK)" -ForegroundColor Green
            $script:testsPassed++
            return $true
        } else {
            Write-Host "  ✗ Status: $statusCode (esperado: $ExpectedStatus)" -ForegroundColor Red
            $script:testsFailed++
            return $false
        }
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -eq $ExpectedStatus) {
            Write-Host "  ✓ Status: $statusCode (OK - esperado)" -ForegroundColor Green
            $script:testsPassed++
            return $true
        } else {
            Write-Host "  ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
            Write-Host "    Status: $statusCode" -ForegroundColor Red
            $script:testsFailed++
            return $false
        }
    }
}

# B1: GET /api/v1/yango/cabinet/claims-to-collect
Write-Host "`n--- B1: Claims to Collect ---" -ForegroundColor Cyan
Test-Endpoint `
    -Name "B1.1: Listado básico (sin filtros)" `
    -Url "$BaseUrl/api/v1/yango/cabinet/claims-to-collect?limit=10"

Test-Endpoint `
    -Name "B1.2: Con filtro milestone" `
    -Url "$BaseUrl/api/v1/yango/cabinet/claims-to-collect?milestone_value=1&limit=10"

Test-Endpoint `
    -Name "B1.3: Con filtro fecha" `
    -Url "$BaseUrl/api/v1/yango/cabinet/claims-to-collect?date_from=2024-01-01&limit=10"

# B2: GET /api/v1/yango/cabinet/claims/{driver_id}/{milestone_value}/drilldown
Write-Host "`n--- B2: Drilldown ---" -ForegroundColor Cyan
# Nota: Requiere driver_id y milestone_value reales de la DB
# Este test puede fallar si no hay datos, pero valida que el endpoint existe
Test-Endpoint `
    -Name "B2.1: Drilldown (puede fallar si no hay datos)" `
    -Url "$BaseUrl/api/v1/yango/cabinet/claims/TEST_DRIVER_ID/1/drilldown" `
    -ExpectedStatus 404

# B3: GET /api/v1/yango/cabinet/claims/export
Write-Host "`n--- B3: Export CSV ---" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/api/v1/yango/cabinet/claims/export" -Method GET -UseBasicParsing -ErrorAction Stop
    $statusCode = $response.StatusCode
    $contentType = $response.Headers["Content-Type"]
    $contentDisposition = $response.Headers["Content-Disposition"]
    
    if ($statusCode -eq 200 -and $contentType -like "*text/csv*") {
        Write-Host "  ✓ Status: $statusCode (OK)" -ForegroundColor Green
        Write-Host "  ✓ Content-Type: $contentType" -ForegroundColor Green
        Write-Host "  ✓ Content-Disposition: $contentDisposition" -ForegroundColor Green
        Write-Host "  ✓ Content-Length: $($response.Content.Length) bytes" -ForegroundColor Green
        
        # Verificar que el contenido es CSV válido (tiene headers)
        if ($response.Content -match "Driver ID") {
            Write-Host "  ✓ CSV válido (contiene headers)" -ForegroundColor Green
        }
        
        $script:testsPassed++
    } else {
        Write-Host "  ✗ Status: $statusCode, Content-Type: $contentType" -ForegroundColor Red
        $script:testsFailed++
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "  ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "    Status: $statusCode" -ForegroundColor Red
    $script:testsFailed++
}

# B4: GET /api/v1/yango/cabinet/mv-health (opcional)
Write-Host "`n--- B4: MV Health Check (opcional) ---" -ForegroundColor Cyan
try {
    $response = Invoke-WebRequest -Uri "$BaseUrl/api/v1/yango/cabinet/mv-health" -Method GET -UseBasicParsing -ErrorAction Stop
    $statusCode = $response.StatusCode
    
    if ($statusCode -eq 200) {
        $json = $response.Content | ConvertFrom-Json
        Write-Host "  ✓ Status: $statusCode (OK)" -ForegroundColor Green
        
        # Validar que exista status_bucket
        if (-not $json.status_bucket) {
            Write-Host "  ✗ status_bucket no presente en response" -ForegroundColor Red
            $script:testsFailed++
            if ($FailFast) {
                Write-Host "  ⛔ FAIL-FAST: Deteniendo ejecución" -ForegroundColor Red
                exit 1
            }
        } else {
            # Validar que status_bucket esté en valores válidos
            $validStatusBuckets = @("OK", "WARN", "CRIT", "NO_REFRESH")
            if ($validStatusBuckets -contains $json.status_bucket) {
                Write-Host "  ✓ status_bucket: $($json.status_bucket) (válido)" -ForegroundColor Green
            } else {
                Write-Host "  ✗ status_bucket: '$($json.status_bucket)' no es válido (esperado: $($validStatusBuckets -join ', '))" -ForegroundColor Red
                $script:testsFailed++
                if ($FailFast) {
                    Write-Host "  ⛔ FAIL-FAST: Deteniendo ejecución" -ForegroundColor Red
                    exit 1
                }
            }
        }
        
        # Validar hours_since_ok_refresh (opcional, puede ser null)
        if ($null -ne $json.hours_since_ok_refresh) {
            Write-Host "  ✓ hours_since_ok_refresh: $($json.hours_since_ok_refresh)" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ hours_since_ok_refresh es null (puede ser normal si no hay refresh)" -ForegroundColor Yellow
        }
        
        $script:testsPassed++
    } else {
        Write-Host "  ✗ Status: $statusCode (esperado: 200)" -ForegroundColor Red
        $script:testsFailed++
        if ($FailFast) {
            Write-Host "  ⛔ FAIL-FAST: Deteniendo ejecución" -ForegroundColor Red
            exit 1
        }
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    # 404 es aceptable si no se aplicó el SQL de health check
    if ($statusCode -eq 404) {
        Write-Host "  ⚠ Status: 404 (vista no existe - ejecutar: psql -d database -f docs/ops/yango_cabinet_claims_mv_health.sql)" -ForegroundColor Yellow
        Write-Host "  (Este test es opcional y 404 es aceptable)" -ForegroundColor Gray
        # No contar como fallido si es 404
    } else {
        Write-Host "  ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "    Status: $statusCode" -ForegroundColor Red
        $script:testsFailed++
        if ($FailFast) {
            Write-Host "  ⛔ FAIL-FAST: Deteniendo ejecución" -ForegroundColor Red
            exit 1
        }
    }
}

# Resumen
Write-Host "`n=== Resumen ===" -ForegroundColor Cyan
Write-Host "Tests pasados: $testsPassed" -ForegroundColor Green
Write-Host "Tests fallidos: $testsFailed" -ForegroundColor $(if ($testsFailed -eq 0) { "Green" } else { "Red" })

if ($testsFailed -eq 0) {
    Write-Host "`n✓ Todos los tests pasaron" -ForegroundColor Green
    exit 0
} else {
    Write-Host "`n✗ Algunos tests fallaron" -ForegroundColor Red
    exit 1
}

