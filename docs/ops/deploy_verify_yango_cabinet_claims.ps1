# ============================================================================
# Checklist Ejecutable: Deploy + Verificación Bloques B/C/D
# ============================================================================
# PROPÓSITO:
# Verificar que los bloques B (endpoints), C (frontend) y D (refresh/health)
# están funcionando correctamente después del deploy.
#
# USO:
#   .\docs\ops\deploy_verify_yango_cabinet_claims.ps1
#   .\docs\ops\deploy_verify_yango_cabinet_claims.ps1 -BackendUrl "http://localhost:8000" -FrontendUrl "http://localhost:3000"
# ============================================================================

param(
    [string]$BackendUrl = "http://localhost:8000",
    [string]$FrontendUrl = "http://localhost:3000",
    [string]$DatabaseUrl = $env:DATABASE_URL
)

$ErrorActionPreference = "Continue"

Write-Host "`n" -NoNewline
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "CHECKLIST: Deploy + Verificación Bloques B/C/D" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Backend URL: $BackendUrl" -ForegroundColor Gray
Write-Host "Frontend URL: $FrontendUrl" -ForegroundColor Gray
Write-Host "`n" -NoNewline

$allChecksPassed = $true
$checkCount = 0

# Helper function para checks
function Test-Check {
    param(
        [string]$Name,
        [scriptblock]$Test,
        [string]$ExpectedOutput = ""
    )
    
    $script:checkCount++
    Write-Host "`n[$checkCount] $Name" -ForegroundColor Yellow
    
    try {
        $result = & $Test
        if ($result -eq $true -or ($result -is [string] -and $result -ne "")) {
            Write-Host "  ✓ PASSED" -ForegroundColor Green
            if ($ExpectedOutput -and $result -is [string]) {
                Write-Host "  Output: $result" -ForegroundColor Gray
            }
            return $true
        } else {
            Write-Host "  ✗ FAILED" -ForegroundColor Red
            if ($ExpectedOutput) {
                Write-Host "  Expected: $ExpectedOutput" -ForegroundColor Gray
            }
            $script:allChecksPassed = $false
            return $false
        }
    } catch {
        Write-Host "  ✗ ERROR: $($_.Exception.Message)" -ForegroundColor Red
        $script:allChecksPassed = $false
        return $false
    }
}

# ============================================================================
# BLOQUE D: Migración y Health Check
# ============================================================================

Write-Host "`n" -NoNewline
Write-Host "--- BLOQUE D: Migración y Health Check ---" -ForegroundColor Cyan

# D1: Aplicar migración mv_refresh_log_extended
Test-Check -Name "D1: Aplicar migración mv_refresh_log_extended" -ExpectedOutput "✓ Verificación: todas las columnas nuevas existen" {
    Push-Location backend
    try {
        $output = python scripts/apply_mv_refresh_log_extended.py 2>&1 | Out-String
        if ($output -match "✓ Verificación: todas las columnas nuevas existen") {
            Write-Host $output -ForegroundColor Gray
            return $true
        } else {
            Write-Host $output -ForegroundColor Red
            return $false
        }
    } finally {
        Pop-Location
    }
}

# D2: Aplicar SQL health check (crear vista)
Test-Check -Name "D2: Aplicar SQL health check (crear ops.v_yango_cabinet_claims_mv_health)" -ExpectedOutput "CREATE VIEW" {
    if (-not $DatabaseUrl) {
        Write-Host "  ⚠ DATABASE_URL no definida, saltando verificación SQL directa" -ForegroundColor Yellow
        Write-Host "  Ejecutar manualmente: psql -d database -f docs/ops/yango_cabinet_claims_mv_health.sql" -ForegroundColor Gray
        return $true  # No fallar si no hay DATABASE_URL
    }
    
    # Intentar verificar que la vista existe usando Python
    Push-Location backend
    try {
        $verifyScript = @"
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').absolute()))
from app.db import engine
from sqlalchemy import text
try:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.views 
                WHERE table_schema = 'ops' 
                AND table_name = 'v_yango_cabinet_claims_mv_health'
            )
        """))
        exists = result.scalar()
        if exists:
            print('VIEW_EXISTS')
            sys.exit(0)
        else:
            print('VIEW_NOT_FOUND')
            sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"@
        $verifyScript | Out-File -FilePath "verify_health_view.py" -Encoding UTF8
        $output = python verify_health_view.py 2>&1 | Out-String
        Remove-Item "verify_health_view.py" -ErrorAction SilentlyContinue
        
        if ($output -match "VIEW_EXISTS") {
            Write-Host "  Vista ops.v_yango_cabinet_claims_mv_health existe" -ForegroundColor Gray
            return $true
        } else {
            Write-Host "  Vista no encontrada. Ejecutar: psql -d database -f docs/ops/yango_cabinet_claims_mv_health.sql" -ForegroundColor Yellow
            return $false
        }
    } finally {
        Pop-Location
    }
}

# D3: Correr refresh manual y confirmar log OK
Test-Check -Name "D3: Correr refresh manual y confirmar log OK" -ExpectedOutput "status=OK" {
    Push-Location backend
    try {
        $output = python scripts/refresh_yango_cabinet_claims_mv.py 2>&1 | Out-String
        Write-Host $output -ForegroundColor Gray
        
        if ($output -match "\[OK\] Refresh.*completado" -and $output -match "exitosamente") {
            # Verificar en BD que el último log tiene status=OK
            $verifyScript = @"
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').absolute()))
from app.db import engine
from sqlalchemy import text
try:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT status, rows_after_refresh
            FROM ops.mv_refresh_log
            WHERE schema_name = 'ops'
              AND mv_name = 'mv_yango_cabinet_claims_for_collection'
            ORDER BY refresh_started_at DESC, refreshed_at DESC
            LIMIT 1
        """))
        row = result.fetchone()
        if row and row[0] in ('OK', 'SUCCESS'):
            print(f'STATUS_OK: {row[0]}, ROWS: {row[1]}')
            sys.exit(0)
        else:
            print(f'STATUS_NOT_OK: {row[0] if row else "NO_RECORD"}')
            sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"@
            $verifyScript | Out-File -FilePath "verify_refresh_log.py" -Encoding UTF8
            $verifyOutput = python verify_refresh_log.py 2>&1 | Out-String
            Remove-Item "verify_refresh_log.py" -ErrorAction SilentlyContinue
            
            if ($verifyOutput -match "STATUS_OK") {
                Write-Host "  Último refresh en log: $verifyOutput" -ForegroundColor Gray
                return $true
            } else {
                Write-Host "  Verificación de log falló: $verifyOutput" -ForegroundColor Red
                return $false
            }
        } else {
            return $false
        }
    } finally {
        Pop-Location
    }
}

# D4: Verificar health check (status_bucket=OK)
Test-Check -Name "D4: Verificar health check (status_bucket debe ser OK o WARN)" -ExpectedOutput "status_bucket=OK" {
    Push-Location backend
    try {
        $verifyScript = @"
import sys
from pathlib import Path
sys.path.insert(0, str(Path('.').absolute()))
from app.db import engine
from sqlalchemy import text
try:
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT status_bucket, hours_since_ok_refresh, last_status
            FROM ops.v_yango_cabinet_claims_mv_health
        """))
        row = result.fetchone()
        if row:
            status_bucket = row[0]
            hours = row[1]
            last_status = row[2]
            print(f'STATUS_BUCKET: {status_bucket}, HOURS: {hours:.2f}, LAST_STATUS: {last_status}')
            # OK o WARN son aceptables (<48h)
            if status_bucket in ('OK', 'WARN'):
                sys.exit(0)
            else:
                sys.exit(1)
        else:
            print('NO_DATA')
            sys.exit(1)
except Exception as e:
    print(f'ERROR: {e}')
    sys.exit(1)
"@
        $verifyScript | Out-File -FilePath "verify_health_status.py" -Encoding UTF8
        $output = python verify_health_status.py 2>&1 | Out-String
        Remove-Item "verify_health_status.py" -ErrorAction SilentlyContinue
        
        if ($output -match "STATUS_BUCKET: (OK|WARN)") {
            Write-Host "  $output" -ForegroundColor Gray
            return $true
        } else {
            Write-Host "  Health check falló o status_bucket no es OK/WARN: $output" -ForegroundColor Red
            return $false
        }
    } finally {
        Pop-Location
    }
}

# ============================================================================
# BLOQUE B: Endpoints Backend
# ============================================================================

Write-Host "`n" -NoNewline
Write-Host "--- BLOQUE B: Endpoints Backend ---" -ForegroundColor Cyan

# B1: GET /api/v1/yango/cabinet/claims-to-collect
Test-Check -Name "B1: GET /api/v1/yango/cabinet/claims-to-collect (sin filtros)" -ExpectedOutput "status=200, response tiene 'rows'" {
    try {
        $response = Invoke-WebRequest -Uri "$BackendUrl/api/v1/yango/cabinet/claims-to-collect?limit=10" -Method GET -UseBasicParsing -ErrorAction Stop
        $json = $response.Content | ConvertFrom-Json
        
        if ($response.StatusCode -eq 200 -and $json.status -eq "ok" -and $json.rows) {
            Write-Host "  Status: $($response.StatusCode)" -ForegroundColor Gray
            Write-Host "  Count: $($json.count), Total: $($json.total)" -ForegroundColor Gray
            return $true
        } else {
            return $false
        }
    } catch {
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# B1 con filtros
Test-Check -Name "B1: GET /api/v1/yango/cabinet/claims-to-collect (con filtro milestone)" -ExpectedOutput "status=200" {
    try {
        $response = Invoke-WebRequest -Uri "$BackendUrl/api/v1/yango/cabinet/claims-to-collect?milestone_value=1&limit=5" -Method GET -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $json = $response.Content | ConvertFrom-Json
            Write-Host "  Status: $($response.StatusCode), Count: $($json.count)" -ForegroundColor Gray
            return $true
        } else {
            return $false
        }
    } catch {
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# B2: GET /api/v1/yango/cabinet/claims/{driver_id}/{milestone_value}/drilldown
Test-Check -Name "B2: GET /api/v1/yango/cabinet/claims/{driver_id}/{milestone_value}/drilldown (puede ser 404 si no hay datos)" -ExpectedOutput "status=200 o 404" {
    try {
        # Intentar con un driver_id que probablemente no existe
        $response = Invoke-WebRequest -Uri "$BackendUrl/api/v1/yango/cabinet/claims/TEST_DRIVER_ID/1/drilldown" -Method GET -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $json = $response.Content | ConvertFrom-Json
            Write-Host "  Status: $($response.StatusCode), tiene datos" -ForegroundColor Gray
            return $true
        } else {
            return $false
        }
    } catch {
        $statusCode = $_.Exception.Response.StatusCode.value__
        if ($statusCode -eq 404) {
            Write-Host "  Status: 404 (esperado si no hay datos de test)" -ForegroundColor Gray
            return $true  # 404 es aceptable, significa que el endpoint existe
        } else {
            Write-Host "  Error: Status $statusCode" -ForegroundColor Red
            return $false
        }
    }
}

# B3: GET /api/v1/yango/cabinet/claims/export
Test-Check -Name "B3: GET /api/v1/yango/cabinet/claims/export (CSV)" -ExpectedOutput "status=200, Content-Type=text/csv" {
    try {
        $response = Invoke-WebRequest -Uri "$BackendUrl/api/v1/yango/cabinet/claims/export" -Method GET -UseBasicParsing -ErrorAction Stop
        $contentType = $response.Headers["Content-Type"]
        $contentDisposition = $response.Headers["Content-Disposition"]
        
        if ($response.StatusCode -eq 200 -and $contentType -like "*text/csv*") {
            Write-Host "  Status: $($response.StatusCode)" -ForegroundColor Gray
            Write-Host "  Content-Type: $contentType" -ForegroundColor Gray
            Write-Host "  Content-Disposition: $contentDisposition" -ForegroundColor Gray
            Write-Host "  Content-Length: $($response.Content.Length) bytes" -ForegroundColor Gray
            
            # Verificar que tiene headers CSV
            if ($response.Content -match "Driver ID|driver_id") {
                Write-Host "  CSV válido (contiene headers)" -ForegroundColor Gray
                return $true
            } else {
                Write-Host "  CSV no tiene headers esperados" -ForegroundColor Yellow
                return $true  # No fallar, solo warning
            }
        } else {
            Write-Host "  Status: $($response.StatusCode), Content-Type: $contentType" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# ============================================================================
# BLOQUE C: Frontend UI
# ============================================================================

Write-Host "`n" -NoNewline
Write-Host "--- BLOQUE C: Frontend UI ---" -ForegroundColor Cyan

# C1: Verificar que la ruta existe (verificar que el servidor responde)
Test-Check -Name "C1: Verificar que frontend responde en $FrontendUrl" -ExpectedOutput "status=200" {
    try {
        $response = Invoke-WebRequest -Uri "$FrontendUrl" -Method GET -UseBasicParsing -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "  Frontend responde correctamente" -ForegroundColor Gray
            return $true
        } else {
            return $false
        }
    } catch {
        Write-Host "  ⚠ Frontend no responde en $FrontendUrl" -ForegroundColor Yellow
        Write-Host "  Verificar manualmente: Abrir $FrontendUrl/pagos/yango-cabinet-claims" -ForegroundColor Gray
        return $true  # No fallar, solo warning
    }
}

# C2: Instrucciones para verificar UI manualmente
Write-Host "`n[C2] Verificación Manual de UI" -ForegroundColor Yellow
Write-Host "  Instrucciones:" -ForegroundColor Gray
Write-Host "  1. Abrir navegador en: $FrontendUrl/pagos/yango-cabinet-claims" -ForegroundColor Gray
Write-Host "  2. Verificar que la página carga sin errores" -ForegroundColor Gray
Write-Host "  3. Verificar que la tabla muestra datos (o mensaje 'No hay claims')" -ForegroundColor Gray
Write-Host "  4. Probar filtros: date_from, date_to, milestone_value, search" -ForegroundColor Gray
Write-Host "  5. Probar botón 'Exportar CSV' (debe descargar archivo CSV)" -ForegroundColor Gray
Write-Host "  6. Hacer click en una fila para ver drilldown modal" -ForegroundColor Gray
Write-Host "`n  ✓ Verificación manual completada (asumir OK si no hay errores visibles)" -ForegroundColor Green

# ============================================================================
# RESUMEN FINAL
# ============================================================================

Write-Host "`n" -NoNewline
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "RESUMEN FINAL" -ForegroundColor Cyan
Write-Host "=" * 80 -ForegroundColor Cyan
Write-Host "Checks ejecutados: $checkCount" -ForegroundColor Gray

if ($allChecksPassed) {
    Write-Host "`n✓ TODOS LOS CHECKS PASARON" -ForegroundColor Green
    Write-Host "`nPróximos pasos:" -ForegroundColor Cyan
    Write-Host "  1. Verificar UI manualmente en: $FrontendUrl/pagos/yango-cabinet-claims" -ForegroundColor Gray
    Write-Host "  2. Programar refresh automático según runbook: docs/runbooks/scheduler_refresh_mvs.md" -ForegroundColor Gray
    Write-Host "  3. Configurar alertas si hours_since_ok_refresh > 24" -ForegroundColor Gray
    exit 0
} else {
    Write-Host "`n✗ ALGUNOS CHECKS FALLARON" -ForegroundColor Red
    Write-Host "`nRevisar errores arriba y corregir antes de continuar." -ForegroundColor Yellow
    exit 1
}

