# Script para probar los endpoints que están fallando con el enum

$baseUrl = "http://127.0.0.1:8000"

Write-Host "Probando endpoint: /api/v1/identity/stats/drivers-without-leads" -ForegroundColor Cyan
try {
    $response1 = Invoke-WebRequest -Uri "$baseUrl/api/v1/identity/stats/drivers-without-leads" -Method GET -ErrorAction Stop
    Write-Host "Status: $($response1.StatusCode)" -ForegroundColor Green
    Write-Host "Response: $($response1.Content)" -ForegroundColor Green
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response Body: $responseBody" -ForegroundColor Yellow
    }
}

Write-Host "`nProbando endpoint: /api/v1/identity/orphans/metrics" -ForegroundColor Cyan
try {
    $response2 = Invoke-WebRequest -Uri "$baseUrl/api/v1/identity/orphans/metrics" -Method GET -ErrorAction Stop
    Write-Host "Status: $($response2.StatusCode)" -ForegroundColor Green
    Write-Host "Response: $($response2.Content)" -ForegroundColor Green
} catch {
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = New-Object System.IO.StreamReader($_.Exception.Response.GetResponseStream())
        $responseBody = $reader.ReadToEnd()
        Write-Host "Response Body: $responseBody" -ForegroundColor Yellow
    }
}

Write-Host "`nPeticiones completadas. Revisa los logs en el terminal de uvicorn." -ForegroundColor Yellow
