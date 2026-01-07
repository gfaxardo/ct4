$ErrorActionPreference = 'Stop'

try {
    Write-Host "Probando endpoint: http://localhost:8000/api/v1/yango/payments/cabinet/reconciliation?limit=2&offset=0"
    Write-Host ""
    
    $response = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/yango/payments/cabinet/reconciliation?limit=2&offset=0" -Method GET -TimeoutSec 5
    
    Write-Host "=== RESPUESTA DEL ENDPOINT ==="
    Write-Host "status: $($response.status)"
    Write-Host "count: $($response.count)"
    Write-Host "total: $($response.total)"
    Write-Host "numero_de_rows: $($response.rows.Count)"
    Write-Host ""
    
    if ($response.rows.Count -gt 0) {
        Write-Host "=== PRIMERA ROW ==="
        $response.rows[0] | ConvertTo-Json -Depth 6
    } else {
        Write-Host "No hay rows en la respuesta"
    }
    
} catch {
    $statusCode = $null
    if ($_.Exception.Response) {
        $statusCode = $_.Exception.Response.StatusCode.value__
    }
    
    if ($statusCode -eq 404) {
        Write-Host "ERROR 404: Ruta no encontrada"
        Write-Host "FIX: Verificar que el router esté registrado en backend/app/api/v1/__init__.py"
    } elseif ($statusCode -eq 500) {
        Write-Host "ERROR 500: Error en SQL o servidor"
        Write-Host "FIX: Verificar logs del backend. Posiblemente la vista ops.v_cabinet_milestones_reconciled no existe"
    } elseif ($_.Exception.Message -match "conexión|connection|Unable to connect|No se puede conectar") {
        Write-Host "ERROR: Servidor no responde (backend caído o no iniciado)"
        Write-Host "FIX: Iniciar backend con: cd backend && uvicorn app.main:app --reload"
    } else {
        Write-Host "ERROR: $($_.Exception.Message)"
    }
    
    if ($statusCode) {
        Write-Host "Status Code: $statusCode"
    } else {
        Write-Host "Error de conexión"
    }
}






