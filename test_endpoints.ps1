# Script de Prueba Manual - Endpoints Pagos Yango
# Ejecutar desde PowerShell en el directorio del proyecto

$baseUrl = "http://localhost:8000"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Prueba de Endpoints - Pagos Yango" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Summary Endpoint
Write-Host "1. Probando Summary Endpoint..." -ForegroundColor Yellow
$summaryUrl = "$baseUrl/api/v1/yango/payments/reconciliation/summary?limit=1000"
try {
    $response = Invoke-RestMethod -Uri $summaryUrl -Method Get -ContentType "application/json"
    Write-Host "✓ Status: OK" -ForegroundColor Green
    Write-Host "  Count: $($response.count)" -ForegroundColor Gray
    Write-Host "  Filters._validation existe: $($null -ne $response.filters._validation)" -ForegroundColor Gray
    if ($response.filters._validation) {
        Write-Host "  Ledger total rows: $($response.filters._validation.ledger_total_rows)" -ForegroundColor Gray
        Write-Host "  Ledger paid rows: $($response.filters._validation.ledger_rows_is_paid_true)" -ForegroundColor Gray
        Write-Host "  Ledger paid without driver: $($response.filters._validation.ledger_rows_is_paid_true_and_driver_id_null)" -ForegroundColor Gray
    }
} catch {
    Write-Host "✗ Error: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# 2. Ledger Unmatched Endpoint
Write-Host "2. Probando Ledger Unmatched Endpoint..." -ForegroundColor Yellow
$unmatchedUrl = "$baseUrl/api/v1/yango/payments/reconciliation/ledger/unmatched?is_paid=true&limit=100"
try {
    $response = Invoke-RestMethod -Uri $unmatchedUrl -Method Get -ContentType "application/json"
    Write-Host "✓ Status: OK" -ForegroundColor Green
    Write-Host "  Total: $($response.total)" -ForegroundColor Gray
    Write-Host "  Count: $($response.count)" -ForegroundColor Gray
    Write-Host "  Rows returned: $($response.rows.Count)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Error: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# 3. Ledger Matched Endpoint (NUEVO)
Write-Host "3. Probando Ledger Matched Endpoint..." -ForegroundColor Yellow
$matchedUrl = "$baseUrl/api/v1/yango/payments/reconciliation/ledger/matched?limit=100"
try {
    $response = Invoke-RestMethod -Uri $matchedUrl -Method Get -ContentType "application/json"
    Write-Host "✓ Status: OK" -ForegroundColor Green
    Write-Host "  Total: $($response.total)" -ForegroundColor Gray
    Write-Host "  Count: $($response.count)" -ForegroundColor Gray
    Write-Host "  Rows returned: $($response.rows.Count)" -ForegroundColor Gray
} catch {
    Write-Host "✗ Error: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

# 4. Driver Detail Endpoint (NUEVO)
# Nota: Requiere un driver_id real. Si no hay, este test fallará.
Write-Host "4. Probando Driver Detail Endpoint..." -ForegroundColor Yellow
Write-Host "  (Requiere driver_id real - usando ejemplo)" -ForegroundColor Gray

# Primero obtener un driver_id del summary si existe
try {
    $summaryResponse = Invoke-RestMethod -Uri "$baseUrl/api/v1/yango/payments/reconciliation/items?limit=1" -Method Get -ContentType "application/json"
    if ($summaryResponse.rows -and $summaryResponse.rows.Count -gt 0 -and $summaryResponse.rows[0].driver_id) {
        $testDriverId = $summaryResponse.rows[0].driver_id
        $driverUrl = "$baseUrl/api/v1/yango/payments/reconciliation/driver/$testDriverId"
        try {
            $response = Invoke-RestMethod -Uri $driverUrl -Method Get -ContentType "application/json"
            Write-Host "✓ Status: OK" -ForegroundColor Green
            Write-Host "  Driver ID: $($response.driver_id)" -ForegroundColor Gray
            Write-Host "  Claims count: $($response.claims.Count)" -ForegroundColor Gray
            Write-Host "  Total Expected: $($response.summary.total_expected)" -ForegroundColor Gray
            Write-Host "  Total Paid: $($response.summary.total_paid)" -ForegroundColor Gray
        } catch {
            Write-Host "✗ Error: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "⚠ No hay driver_id disponible para probar (esto es normal si no hay claims con driver_id)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "✗ Error obteniendo driver_id de prueba: $($_.Exception.Message)" -ForegroundColor Red
}
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Pruebas completadas" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan







