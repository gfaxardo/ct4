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
    [string]$BaseUrl = "http://localhost:8000"
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
    $response = Invoke-WebRequest -Uri "$BaseUrl/api/v1/yango/cabinet/claims/export?limit=10" -Method GET -UseBasicParsing -ErrorAction Stop
    $statusCode = $response.StatusCode
    $contentType = $response.Headers["Content-Type"]
    
    if ($statusCode -eq 200 -and $contentType -like "*text/csv*") {
        Write-Host "  ✓ Status: $statusCode (OK)" -ForegroundColor Green
        Write-Host "  ✓ Content-Type: $contentType" -ForegroundColor Green
        Write-Host "  ✓ Content-Length: $($response.Content.Length) bytes" -ForegroundColor Green
        $script:testsPassed++
    } else {
        Write-Host "  ✗ Status: $statusCode, Content-Type: $contentType" -ForegroundColor Red
        $script:testsFailed++
    }
} catch {
    $statusCode = $_.Exception.Response.StatusCode.value__
    Write-Host "  ✗ Error: $($_.Exception.Message)" -ForegroundColor Red
    $script:testsFailed++
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

