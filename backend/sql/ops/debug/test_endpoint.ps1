# Script para hacer petición al endpoint desde PowerShell
# Ejecutar: .\test_endpoint.ps1

$url = "http://localhost:8000/api/v1/payments/cabinet/drivers?limit=100"
Write-Host "Haciendo petición a: $url" -ForegroundColor Green

try {
    $response = Invoke-RestMethod -Uri $url -Method Get -ContentType "application/json"
    Write-Host "`nRespuesta recibida exitosamente!" -ForegroundColor Green
    Write-Host "Total de drivers: $($response.total)" -ForegroundColor Cyan
    Write-Host "Count: $($response.count)" -ForegroundColor Cyan
    Write-Host "`nPrimeros 3 drivers:" -ForegroundColor Yellow
    $response.rows | Select-Object -First 3 | Format-Table driver_id, expected_total, claims_total -AutoSize
} catch {
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host "Asegúrate de que el backend esté corriendo en http://localhost:8000" -ForegroundColor Yellow
}

