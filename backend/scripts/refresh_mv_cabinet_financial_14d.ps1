# Script PowerShell para refrescar la vista materializada
# Alternativa al script Python

$ErrorActionPreference = "Stop"

# Configuración de base de datos
$dbHost = "168.119.226.236"
$dbPort = "5432"
$dbName = "yego_integral"
$dbUser = "yego_user"
$dbPassword = "37>MNA&-35+"

Write-Host "=" * 70
Write-Host "REFRESH: ops.mv_cabinet_financial_14d"
Write-Host "=" * 70

try {
    $env:PGPASSWORD = $dbPassword
    
    Write-Host "Refrescando vista materializada..." -ForegroundColor Yellow
    $startTime = Get-Date
    
    $refreshQuery = "REFRESH MATERIALIZED VIEW ops.mv_cabinet_financial_14d;"
    $refreshQuery | & psql -h $dbHost -p $dbPort -U $dbUser -d $dbName -q
    
    if ($LASTEXITCODE -eq 0) {
        $elapsed = (Get-Date) - $startTime
        
        # Verificar que se refrescó correctamente
        $verifyQuery = "SELECT COUNT(*) FROM ops.mv_cabinet_financial_14d;"
        $count = ($verifyQuery | & psql -h $dbHost -p $dbPort -U $dbUser -d $dbName -t -A).Trim()
        
        Write-Host "[OK] Vista materializada refrescada exitosamente!" -ForegroundColor Green
        Write-Host "     Tiempo: $($elapsed.TotalSeconds.ToString('F2')) segundos" -ForegroundColor Gray
        Write-Host "     Filas: $count" -ForegroundColor Gray
        Write-Host "=" * 70
    } else {
        Write-Host "[ERROR] Error al refrescar la vista materializada." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "[ERROR] Error: $_" -ForegroundColor Red
    exit 1
} finally {
    $env:PGPASSWORD = $null
}




