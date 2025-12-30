# Script para limpiar caché de Next.js
Write-Host "Limpiando caché de Next.js..." -ForegroundColor Yellow

if (Test-Path .next) {
    Remove-Item -Recurse -Force .next
    Write-Host "✓ Directorio .next eliminado" -ForegroundColor Green
} else {
    Write-Host "✓ No existe directorio .next" -ForegroundColor Gray
}

if (Test-Path node_modules\.cache) {
    Remove-Item -Recurse -Force node_modules\.cache
    Write-Host "✓ Cache de node_modules eliminado" -ForegroundColor Green
} else {
    Write-Host "✓ No existe cache en node_modules" -ForegroundColor Gray
}

Write-Host "`nCaché limpiado. Ahora ejecuta: npm run dev" -ForegroundColor Cyan


















