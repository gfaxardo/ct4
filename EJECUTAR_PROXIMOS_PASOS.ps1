# Script PowerShell para ejecutar los próximos pasos de Recovery Impact

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "EJECUCIÓN: Próximos Pasos Recovery Impact" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Cambiar al directorio backend
Set-Location "backend"

Write-Host "PASO 1: Ejecutando migración..." -ForegroundColor Yellow
Write-Host "Ejecutando: alembic upgrade head" -ForegroundColor Gray
alembic upgrade head
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error ejecutando migración" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Migración ejecutada exitosamente" -ForegroundColor Green
Write-Host ""

Write-Host "PASO 2: Creando vistas SQL..." -ForegroundColor Yellow
python execute_recovery_impact_steps.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Error creando vistas" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "✅ Todos los pasos ejecutados exitosamente" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Próximos pasos:" -ForegroundColor Yellow
Write-Host "1. Probar endpoint: GET /api/v1/yango/cabinet/identity-recovery-impact-14d"
Write-Host "2. (Opcional) Ejecutar job: python -m jobs.cabinet_recovery_impact_job 1000"
Write-Host ""
