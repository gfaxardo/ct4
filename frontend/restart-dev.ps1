# Script para reiniciar el servidor de desarrollo de Next.js
Write-Host "=== Limpiando y reiniciando servidor de desarrollo ===" -ForegroundColor Cyan

# Detener procesos de Node.js en el puerto 3000
Write-Host "`n1. Deteniendo procesos en puerto 3000..." -ForegroundColor Yellow
$processes = Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($processes) {
    foreach ($pid in $processes) {
        Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
        Write-Host "   Proceso $pid detenido" -ForegroundColor Gray
    }
} else {
    Write-Host "   No hay procesos en puerto 3000" -ForegroundColor Gray
}

# Limpiar caché
Write-Host "`n2. Limpiando caché..." -ForegroundColor Yellow
if (Test-Path .next) {
    Remove-Item -Recurse -Force .next
    Write-Host "   ✓ Directorio .next eliminado" -ForegroundColor Green
} else {
    Write-Host "   ✓ No existe directorio .next" -ForegroundColor Gray
}

if (Test-Path node_modules\.cache) {
    Remove-Item -Recurse -Force node_modules\.cache
    Write-Host "   ✓ Cache de node_modules eliminado" -ForegroundColor Green
}

# Esperar un momento
Start-Sleep -Seconds 2

# Iniciar servidor
Write-Host "`n3. Iniciando servidor de desarrollo..." -ForegroundColor Yellow
Write-Host "   Ejecutando: npm run dev" -ForegroundColor Cyan
Write-Host "`n=== Presiona Ctrl+C para detener el servidor ===" -ForegroundColor Yellow
npm run dev
























