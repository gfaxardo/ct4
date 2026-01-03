# ============================================================================
# Deploy Verification Gate: Yango Cabinet Claims
# ============================================================================
# Verifica que backend y frontend estan funcionando correctamente.
# Solo usa HTTP checks, no requiere psql ni conexion directa a BD.
#
# USO:
#   .\docs\ops\deploy_verify_yango_cabinet_claims.ps1
#   .\docs\ops\deploy_verify_yango_cabinet_claims.ps1 -BackendUrl "http://localhost:8000" -FrontendUrl "http://localhost:3000"
#   .\docs\ops\deploy_verify_yango_cabinet_claims.ps1 -SkipBackend
# ============================================================================

param(
    [string]$BackendUrl = "http://localhost:8000",
    [string]$FrontendUrl = "http://localhost:3000",
    [switch]$FailFast = $true,
    [switch]$VerboseOutput,
    [switch]$SkipBackend,
    [switch]$SkipFrontend
)

$ErrorActionPreference = if ($FailFast) { "Stop" } else { "Continue" }

# Estado global
$script:allChecksPassed = $true
$script:checkCount = 0
$script:shouldExit = $false
$script:exitCode = 0

# ============================================================================
# Helper Functions
# ============================================================================

function Write-CheckHeader {
    param([string]$Name)
    $script:checkCount++
    Write-Host ""
    Write-Host "[CHECK] $Name" -ForegroundColor Yellow
}

function Write-CheckResult {
    param(
        [string]$Status,  # OK, FAIL, WARN
        [string]$Message = "",
        [string]$FixCommand = ""
    )
    
    $color = switch ($Status) {
        "OK" { "Green" }
        "FAIL" { "Red" }
        "WARN" { "Yellow" }
        default { "Gray" }
    }
    
    Write-Host "  [$Status] $Message" -ForegroundColor $color
    
    if ($FixCommand -and ($Status -eq "FAIL" -or $Status -eq "WARN")) {
        Write-Host "  [FIX] $FixCommand" -ForegroundColor Cyan
    }
    
    if ($Status -eq "FAIL") {
        $script:allChecksPassed = $false
        if ($FailFast) {
            Write-Host ""
            Write-Host "[FAIL-FAST] Deteniendo ejecucion" -ForegroundColor Red
            $script:shouldExit = $true
            $script:exitCode = 1
        }
    }
}

function Invoke-SafeWebRequest {
    param(
        [string]$Uri,
        [string]$Method = "GET",
        [hashtable]$Headers = @{}
    )
    
    try {
        $params = @{
            Uri = $Uri
            Method = $Method
            UseBasicParsing = $true
            ErrorAction = "Stop"
        }
        
        if ($Headers.Count -gt 0) {
            $params.Headers = $Headers
        }
        
        $response = Invoke-WebRequest @params
        return @{
            Success = $true
            StatusCode = $response.StatusCode
            Content = $response.Content
            Headers = $response.Headers
            Error = $null
        }
    }
    catch {
        $statusCode = $null
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode.value__
        }
        
        return @{
            Success = $false
            StatusCode = $statusCode
            Content = $null
            Headers = $null
            Error = $_.Exception.Message
        }
    }
}

function Test-JsonResponse {
    param(
        [string]$Content,
        [string[]]$RequiredKeys = @()
    )
    
    try {
        $json = $Content | ConvertFrom-Json
        
        foreach ($key in $RequiredKeys) {
            if (-not (Get-Member -InputObject $json -Name $key -ErrorAction SilentlyContinue)) {
                return $false
            }
        }
        
        return $true
    }
    catch {
        return $false
    }
}

function Test-CsvBom {
    param([byte[]]$ContentBytes)
    
    if ($ContentBytes.Length -lt 3) {
        return $false
    }
    
    # BOM utf-8-sig: EF BB BF
    return ($ContentBytes[0] -eq 0xEF -and $ContentBytes[1] -eq 0xBB -and $ContentBytes[2] -eq 0xBF)
}

# ============================================================================
# Backend Checks
# ============================================================================

function Test-BackendChecks {
    if ($SkipBackend) {
        Write-Host ""
        Write-Host "[SKIP] Backend checks skipped" -ForegroundColor DarkGray
        return
    }
    
    Write-Host ""
    Write-Host "=== BACKEND CHECKS ===" -ForegroundColor Cyan
    
    # B1: GET /api/v1/yango/cabinet/claims-to-collect?limit=1
    Write-CheckHeader "B1: GET /api/v1/yango/cabinet/claims-to-collect"
    
    $uri = "$BackendUrl/api/v1/yango/cabinet/claims-to-collect"
    $queryParams = @{ limit = "1" }
    $fullUri = $uri + "?" + (($queryParams.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "&")
    
    $result = Invoke-SafeWebRequest -Uri $fullUri
    
    if (-not $result.Success -or $result.StatusCode -ne 200) {
        Write-CheckResult -Status "FAIL" -Message "Status $($result.StatusCode): $($result.Error)" `
            -FixCommand "Verificar que backend esta corriendo en $BackendUrl"
        return
    }
    
    if (-not (Test-JsonResponse -Content $result.Content -RequiredKeys @("rows", "items"))) {
        # Acepta "rows" o "items", pero debe tener al menos uno
        $hasRows = Test-JsonResponse -Content $result.Content -RequiredKeys @("rows")
        $hasItems = Test-JsonResponse -Content $result.Content -RequiredKeys @("items")
        
        if (-not $hasRows -and -not $hasItems) {
            Write-CheckResult -Status "FAIL" -Message "Response no tiene 'rows' ni 'items' en JSON" `
                -FixCommand "Verificar formato de respuesta del endpoint"
            return
        }
    }
    
    Write-CheckResult -Status "OK" -Message "Status 200, JSON valido"
    
    # B3: GET /api/v1/yango/cabinet/claims/export?limit=1
    Write-CheckHeader "B3: GET /api/v1/yango/cabinet/claims/export"
    
    $exportUri = "$BackendUrl/api/v1/yango/cabinet/claims/export"
    $exportQueryParams = @{ limit = "1" }
    $exportFullUri = $exportUri + "?" + (($exportQueryParams.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "&")
    
    try {
        # Hacer request con UseBasicParsing para mantener RawContentStream
        $exportResponse = Invoke-WebRequest -Uri $exportFullUri -Method GET -UseBasicParsing -ErrorAction Stop
        
        if ($exportResponse.StatusCode -ne 200) {
            Write-CheckResult -Status "FAIL" -Message "Status $($exportResponse.StatusCode)" `
                -FixCommand "Verificar que endpoint /export funciona en $BackendUrl"
            return
        }
        
        $contentType = $exportResponse.Headers["Content-Type"]
        if ($contentType -notlike "*text/csv*") {
            Write-CheckResult -Status "FAIL" -Message "Content-Type no es text/csv: $contentType" `
                -FixCommand "Verificar que endpoint export devuelve CSV correctamente"
            return
        }
        
        # Leer primeros 3 bytes reales desde RawContentStream
        $exportResponse.RawContentStream.Position = 0
        $head = New-Object byte[] 3
        $bytesRead = $exportResponse.RawContentStream.Read($head, 0, 3)
        
        if ($bytesRead -lt 3) {
            Write-CheckResult -Status "FAIL" -Message "CSV tiene menos de 3 bytes" `
                -FixCommand "Verificar que endpoint export devuelve contenido valido"
            return
        }
        
        # Convertir a hexadecimal para comparacion
        $hex = "{0:X2} {1:X2} {2:X2}" -f $head[0], $head[1], $head[2]
        
        if ($hex -ne "EF BB BF") {
            Write-CheckResult -Status "FAIL" -Message "CSV no tiene BOM utf-8-sig (EF BB BF). Recibido: $hex" `
                -FixCommand "Verificar que endpoint export incluye BOM utf-8-sig"
            return
        }
        
        Write-CheckResult -Status "OK" -Message "Status 200, Content-Type text/csv, BOM presente (EF BB BF)"
    }
    catch {
        $statusCode = $null
        if ($_.Exception.Response) {
            $statusCode = [int]$_.Exception.Response.StatusCode.value__
        }
        
        Write-CheckResult -Status "FAIL" -Message "Error en request: $($_.Exception.Message) (Status: $statusCode)" `
            -FixCommand "Verificar que endpoint /export funciona en $BackendUrl"
        return
    }
    
    # B4: GET /api/v1/yango/cabinet/mv-health
    Write-CheckHeader "B4: GET /api/v1/yango/cabinet/mv-health"
    
    $healthUri = "$BackendUrl/api/v1/yango/cabinet/mv-health"
    $healthResult = Invoke-SafeWebRequest -Uri $healthUri
    
    if ($healthResult.StatusCode -eq 404) {
        Write-CheckResult -Status "WARN" -Message "Endpoint no encontrado (404) - puede que no se haya aplicado la vista SQL" `
            -FixCommand "cd backend; python scripts/apply_yango_cabinet_claims_mv_health.py"
        return
    }
    
    if (-not $healthResult.Success -or $healthResult.StatusCode -ne 200) {
        Write-CheckResult -Status "WARN" -Message "Status $($healthResult.StatusCode): $($healthResult.Error)" `
            -FixCommand "Verificar que endpoint /mv-health funciona"
        return
    }
    
    if (-not (Test-JsonResponse -Content $healthResult.Content -RequiredKeys @("status_bucket"))) {
        Write-CheckResult -Status "WARN" -Message "Response no tiene 'status_bucket' en JSON" `
            -FixCommand "Verificar formato de respuesta del endpoint"
        return
    }
    
    $healthJson = $healthResult.Content | ConvertFrom-Json
    $statusBucket = $healthJson.status_bucket
    
    if ($statusBucket -in @("OK", "WARN", "CRIT", "NO_REFRESH")) {
        Write-CheckResult -Status "OK" -Message "Status 200, status_bucket=$statusBucket"
    }
    else {
        Write-CheckResult -Status "WARN" -Message "status_bucket tiene valor inesperado: $statusBucket" `
            -FixCommand "Verificar estado de la MV en ops.v_yango_cabinet_claims_mv_health"
    }
}

# ============================================================================
# Frontend Checks
# ============================================================================

function Test-FrontendChecks {
    if ($SkipFrontend) {
        Write-Host ""
        Write-Host "[SKIP] Frontend checks skipped" -ForegroundColor DarkGray
        return
    }
    
    Write-Host ""
    Write-Host "=== FRONTEND CHECKS ===" -ForegroundColor Cyan
    
    # C1: GET FrontendUrl
    Write-CheckHeader "C1: GET $FrontendUrl"
    
    $result = Invoke-SafeWebRequest -Uri $FrontendUrl
    
    if (-not $result.Success -or $result.StatusCode -ne 200) {
        Write-CheckResult -Status "FAIL" -Message "Status $($result.StatusCode): $($result.Error)" `
            -FixCommand "Verificar que frontend esta corriendo en $FrontendUrl"
        return
    }
    
    Write-CheckResult -Status "OK" -Message "Status 200"
    
    # C2: GET FrontendUrl/pagos/yango-cabinet-claims
    Write-CheckHeader "C2: GET $FrontendUrl/pagos/yango-cabinet-claims"
    
    $pageUri = "$FrontendUrl/pagos/yango-cabinet-claims"
    $pageResult = Invoke-SafeWebRequest -Uri $pageUri
    
    # Aceptar 200, 307, 308 (redirects)
    if ($pageResult.Success -and $pageResult.StatusCode -in @(200, 307, 308)) {
        Write-CheckResult -Status "OK" -Message "Status $($pageResult.StatusCode)"
    }
    elseif ($pageResult.StatusCode -eq 404) {
        Write-CheckResult -Status "WARN" -Message "Página no encontrada (404)" `
            -FixCommand "Verificar que la ruta /pagos/yango-cabinet-claims existe en frontend"
    }
    else {
        Write-CheckResult -Status "FAIL" -Message "Status $($pageResult.StatusCode): $($pageResult.Error)" `
            -FixCommand "Verificar que frontend responde correctamente"
    }
}

# ============================================================================
# Main
# ============================================================================

Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "DEPLOY VERIFICATION: Yango Cabinet Claims" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Backend URL: $BackendUrl" -ForegroundColor Gray
Write-Host "Frontend URL: $FrontendUrl" -ForegroundColor Gray
Write-Host "Fail-Fast: $FailFast" -ForegroundColor Gray
Write-Host "Verbose Output: $VerboseOutput" -ForegroundColor Gray
Write-Host "Skip Backend: $SkipBackend" -ForegroundColor Gray
Write-Host "Skip Frontend: $SkipFrontend" -ForegroundColor Gray

Test-BackendChecks
if ($script:shouldExit) {
    exit $script:exitCode
}

Test-FrontendChecks
if ($script:shouldExit) {
    exit $script:exitCode
}

# ============================================================================
# Summary
# ============================================================================

Write-Host ""
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "SUMMARY" -ForegroundColor Cyan
Write-Host ("=" * 70) -ForegroundColor Cyan
Write-Host "Checks executed: $script:checkCount" -ForegroundColor Gray

if ($script:allChecksPassed) {
    Write-Host ""
    Write-Host "[OK] ALL CHECKS PASSED" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Verify UI manually: $FrontendUrl/pagos/yango-cabinet-claims" -ForegroundColor Gray
    Write-Host "  2. Schedule automatic refresh (see runbook)" -ForegroundColor Gray
    Write-Host "  3. Configure alerts if hours_since_ok_refresh > 24" -ForegroundColor Gray
    exit 0
}
else {
    Write-Host ""
    Write-Host "[FAIL] SOME CHECKS FAILED" -ForegroundColor Red
    Write-Host "Review errors above and fix before continuing" -ForegroundColor Yellow
    exit 1
}
