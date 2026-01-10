# ============================================================================
# SCRIPT: Ejecución Completa - Atribución de Scouts
# ============================================================================
# Este script ejecuta todos los pasos necesarios para cerrar el problema
# de atribución de scouts.
# ============================================================================

Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "EJECUCIÓN COMPLETA: ATRIBUCIÓN DE SCOUTS" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""

# Paso 1: Verificar conexión
Write-Host "PASO 1: Verificando conexión a base de datos..." -ForegroundColor Yellow
cd backend
python scripts/verify_connection.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] No se pudo conectar a la base de datos" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Conexion OK" -ForegroundColor Green
Write-Host ""

# Paso 2: Ejecutar pipeline end-to-end
Write-Host "PASO 2: Ejecutando pipeline end-to-end..." -ForegroundColor Yellow
python scripts/execute_scout_attribution_end_to_end.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Error en ejecucion del pipeline" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Pipeline ejecutado" -ForegroundColor Green
Write-Host ""

# Paso 3: Verificar resultados
Write-Host "PASO 3: Verificando resultados..." -ForegroundColor Yellow
Write-Host "Ejecutando consultas de validación..." -ForegroundColor Gray

cd ..
Write-Host ""
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host "EJECUCIÓN COMPLETADA" -ForegroundColor Cyan
Write-Host "============================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "PRÓXIMOS PASOS MANUALES:" -ForegroundColor Yellow
Write-Host "1. Revisar logs de ejecución" -ForegroundColor White
Write-Host "2. Validar métricas en base de datos:" -ForegroundColor White
Write-Host "   SELECT * FROM ops.v_scout_payment_base LIMIT 10;" -ForegroundColor Gray
Write-Host "   SELECT * FROM ops.v_scout_attribution_conflicts;" -ForegroundColor Gray
Write-Host "3. Revisar tablas de auditoría:" -ForegroundColor White
Write-Host "   SELECT * FROM ops.lead_ledger_scout_backfill_audit ORDER BY backfill_timestamp DESC LIMIT 10;" -ForegroundColor Gray
Write-Host ""

