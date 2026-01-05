# Script de verificación de rutas y limpieza de cache
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "VERIFICACIÓN DE RUTAS Y NAVBAR" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Verificar estructura de archivos
Write-Host "`n1. Verificando estructura de archivos..." -ForegroundColor Yellow
$pagosExists = Test-Path "app\pagos\page.tsx"
$liquidacionesExists = Test-Path "app\liquidaciones\page.tsx"
$layoutExists = Test-Path "app\layout.tsx"

Write-Host "  app/pagos/page.tsx: $pagosExists" -ForegroundColor $(if ($pagosExists) { "Green" } else { "Red" })
Write-Host "  app/liquidaciones/page.tsx: $liquidacionesExists" -ForegroundColor $(if ($liquidacionesExists) { "Green" } else { "Red" })
Write-Host "  app/layout.tsx: $layoutExists" -ForegroundColor $(if ($layoutExists) { "Green" } else { "Red" })

# Verificar links en layout
Write-Host "`n2. Verificando links en layout.tsx..." -ForegroundColor Yellow
$layoutContent = Get-Content "app\layout.tsx" -Raw
$hasPagos = $layoutContent -match 'href="/pagos"'
$hasLiquidaciones = $layoutContent -match 'href="/liquidaciones"'

Write-Host "  Link a /pagos: $hasPagos" -ForegroundColor $(if ($hasPagos) { "Green" } else { "Red" })
Write-Host "  Link a /liquidaciones: $hasLiquidaciones" -ForegroundColor $(if ($hasLiquidaciones) { "Green" } else { "Red" })

# Limpiar cache
Write-Host "`n3. Limpiando cache de Next.js..." -ForegroundColor Yellow
if (Test-Path ".next") {
    Remove-Item -Recurse -Force .next -ErrorAction SilentlyContinue
    Write-Host "  Cache eliminado" -ForegroundColor Green
} else {
    Write-Host "  No hay cache para eliminar" -ForegroundColor Gray
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "INSTRUCCIONES:" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "1. Reiniciar el servidor de desarrollo:" -ForegroundColor White
Write-Host "   npm run dev" -ForegroundColor Green
Write-Host "`n2. Verificar en el navegador:" -ForegroundColor White
Write-Host "   - http://localhost:3000/pagos" -ForegroundColor Green
Write-Host "   - http://localhost:3000/liquidaciones" -ForegroundColor Green
Write-Host "`n3. Verificar que el navbar muestra:" -ForegroundColor White
Write-Host "   Dashboard | Personas | Sin Resolver | Corridas | Pagos | Liquidaciones" -ForegroundColor Green
Write-Host "`nSi los links no aparecen, hacer hard refresh:" -ForegroundColor Yellow
Write-Host "   Ctrl+Shift+R (Windows) o Cmd+Shift+R (Mac)" -ForegroundColor Yellow





















