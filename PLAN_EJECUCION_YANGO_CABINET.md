# PLAN DE EJECUCIÓN: Deploy/Validación Yango Cabinet Claims
**Windows PowerShell | Copy/Paste | Zero Manual Work**

---

## CHECKLIST COMPLETO (15 pasos)

### PREPARACIÓN (1-3)

**[1] Verificar DATABASE_URL**
```powershell
if (-not $env:DATABASE_URL) { $env:DATABASE_URL = "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral" }; echo "DATABASE_URL: $env:DATABASE_URL"
```
**Output esperado:** URL de conexión PostgreSQL
**Si falla:** Usar URL hardcodeada del script o crear `.env` en `backend/`

**[2] Verificar psql disponible (opcional, solo para SQL directo)**
```powershell
Get-Command psql -ErrorAction SilentlyContinue; if ($?) { echo "psql OK" } else { echo "psql NO encontrado (scripts Python funcionan sin psql)" }
```
**Output esperado:** `psql OK` o mensaje que scripts Python funcionan sin psql
**Si falla:** Continuar, scripts Python usan SQLAlchemy

**[3] Ir a directorio proyecto**
```powershell
cd C:\cursor\CT4
```
**Output esperado:** Cambio de directorio exitoso
**Si falla:** Verificar ruta del proyecto

---

### MIGRACIÓN Y SETUP (4-7)

**[4] Aplicar migración mv_refresh_log_extended**
```powershell
cd backend; python scripts/apply_mv_refresh_log_extended.py; cd ..
```
**Output esperado:** `✓ Verificación: todas las columnas nuevas existen`
**Si falla:** Verificar DATABASE_URL y conexión a BD

**[5] Aplicar SQL health view (v_yango_cabinet_claims_mv_health)**
```powershell
if (Get-Command psql -ErrorAction SilentlyContinue) { psql "$env:DATABASE_URL" -f docs/ops/yango_cabinet_claims_mv_health.sql } else { echo "SKIP: psql no disponible (usar Python si es necesario)" }
```
**Output esperado:** `CREATE VIEW` o mensaje de skip
**Si falla:** Verificar que SQL file existe en `docs/ops/yango_cabinet_claims_mv_health.sql`

**[6] Verificar duplicados en MV (antes de crear índice único)**
```powershell
if (Get-Command psql -ErrorAction SilentlyContinue) { psql "$env:DATABASE_URL" -c "SELECT driver_id, milestone_value, COUNT(*) AS count_duplicates FROM ops.mv_yango_cabinet_claims_for_collection GROUP BY driver_id, milestone_value HAVING COUNT(*) > 1 ORDER BY count_duplicates DESC LIMIT 10;" } else { echo "SKIP: psql no disponible" }
```
**Output esperado:** 0 filas (sin duplicados) o lista de duplicados
**Si falla:** Si hay duplicados, NO crear índice único hasta resolverlos

**[7] Crear índice único (SOLO si Query 6 retornó 0 filas)**
```powershell
if (Get-Command psql -ErrorAction SilentlyContinue) { psql "$env:DATABASE_URL" -f backend/sql/ops/mv_yango_cabinet_claims_unique_index.sql } else { echo "SKIP: psql no disponible (índice se creará automáticamente si es necesario)" }
```
**Output esperado:** `CREATE UNIQUE INDEX` o mensaje de skip
**Si falla:** Si Query 6 tenía duplicados, resolver primero. Si psql falla, el script Python intentará CONCURRENTLY automáticamente.

---

### REFRESH Y HEALTH (8-10)

**[8] Refrescar MV (usa CONCURRENTLY si índice único existe)**
```powershell
cd backend; python scripts/refresh_yango_cabinet_claims_mv.py; cd ..
```
**Output esperado:** `[OK] Refresh completado exitosamente`
**Si falla:** Ver log de error. Si falla CONCURRENTLY, script automáticamente intenta sin CONCURRENTLY.

**[9] Verificar health check (status_bucket debe ser OK o WARN)**
```powershell
if (Get-Command psql -ErrorAction SilentlyContinue) { psql "$env:DATABASE_URL" -c "SELECT status_bucket, hours_since_ok_refresh, last_status FROM ops.v_yango_cabinet_claims_mv_health;" } else { echo "SKIP: verificar vía endpoint B4" }
```
**Output esperado:** `status_bucket = OK` o `WARN` (no `CRIT` ni `NO_REFRESH`)
**Si falla:** Verificar que refresh completó correctamente (paso 8)

**[10] Verificar último refresh en log**
```powershell
if (Get-Command psql -ErrorAction SilentlyContinue) { psql "$env:DATABASE_URL" -c "SELECT status, rows_after_refresh, refresh_started_at, refresh_finished_at FROM ops.mv_refresh_log WHERE schema_name = 'ops' AND mv_name = 'mv_yango_cabinet_claims_for_collection' ORDER BY refresh_started_at DESC LIMIT 1;" } else { echo "SKIP: verificar vía endpoint B4" }
```
**Output esperado:** `status = OK` o `SUCCESS`, `rows_after_refresh > 0`
**Si falla:** Verificar paso 8 (refresh)

---

### VALIDACIÓN BACKEND (11-12)

**[11] Gate deploy_verify (valida bloques B/C/D)**
```powershell
.\docs\ops\deploy_verify_yango_cabinet_claims.ps1 -FailFast
```
**Output esperado:** `✓ TODOS LOS CHECKS PASARON`
**Si falla:** Revisar output del script para identificar qué check falló (B1-B4, D1-D4, C1-C2)

**[12] Smoke test endpoints (opcional, redundante con paso 11)**
```powershell
.\docs\ops\test_yango_cabinet_endpoints.ps1 -FailFast
```
**Output esperado:** `✓ Todos los tests pasaron`
**Si falla:** Verificar que backend está corriendo en `http://localhost:8000`

---

### VALIDACIÓN FRONTEND (13-15)

**[13] Verificar que backend está corriendo**
```powershell
try { $r = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2; echo "Backend OK: $($r.StatusCode)" } catch { echo "Backend NO responde en http://localhost:8000" }
```
**Output esperado:** `Backend OK: 200`
**Si falla:** Iniciar backend: `cd backend; python -m uvicorn app.main:app --reload`

**[14] Verificar que frontend está corriendo**
```powershell
try { $r = Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 2; echo "Frontend OK: $($r.StatusCode)" } catch { echo "Frontend NO responde en http://localhost:3000" }
```
**Output esperado:** `Frontend OK: 200`
**Si falla:** Iniciar frontend: `cd frontend; npm run dev`

**[15] Verificación manual UI (abrir en navegador)**
```
Abrir: http://localhost:3000/pagos/yango-cabinet-claims
```
**Verificar:**
- Página carga sin errores
- Tabla muestra datos (o mensaje "No hay claims")
- Filtros funcionan (date_from, date_to, milestone_value, search)
- Botón "Exportar CSV" descarga archivo
- Click en fila abre drilldown modal

---

## MODO RÁPIDO (3-5 comandos) - Cuando ya está todo aplicado

```powershell
# [R1] Refresh MV
cd backend; python scripts/refresh_yango_cabinet_claims_mv.py; cd ..

# [R2] Gate deploy_verify (valida todo)
.\docs\ops\deploy_verify_yango_cabinet_claims.ps1 -FailFast

# [R3] Verificar health vía endpoint (opcional)
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/yango/cabinet/mv-health" -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json | Format-List

# [R4] Abrir UI (manual)
Start-Process "http://localhost:3000/pagos/yango-cabinet-claims"
```

---

## TROUBLESHOOTING (6 fallas típicas)

### [T1] 404 en /api/v1/yango/cabinet/mv-health

**Síntoma:**
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/yango/cabinet/mv-health" -UseBasicParsing
# Error: 404 Not Found
```

**Fix:**
```powershell
# Aplicar SQL health view
if (Get-Command psql -ErrorAction SilentlyContinue) { psql "$env:DATABASE_URL" -f docs/ops/yango_cabinet_claims_mv_health.sql } else { echo "ERROR: psql no disponible, usar Python script o aplicar SQL manualmente" }
```

**Verificación:**
```powershell
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/yango/cabinet/mv-health" -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json | Format-List
```

---

### [T2] Refresh falla con CONCURRENTLY (índice único faltante)

**Síntoma:**
```powershell
cd backend; python scripts/refresh_yango_cabinet_claims_mv.py
# Error: cannot refresh materialized view concurrently because it does not have a unique index
```

**Fix:**
```powershell
# [T2.1] Verificar duplicados primero
if (Get-Command psql -ErrorAction SilentlyContinue) { psql "$env:DATABASE_URL" -c "SELECT driver_id, milestone_value, COUNT(*) AS count_duplicates FROM ops.mv_yango_cabinet_claims_for_collection GROUP BY driver_id, milestone_value HAVING COUNT(*) > 1 LIMIT 10;" }

# [T2.2] Si Query retorna 0 filas, crear índice único
if (Get-Command psql -ErrorAction SilentlyContinue) { psql "$env:DATABASE_URL" -f backend/sql/ops/mv_yango_cabinet_claims_unique_index.sql }

# [T2.3] Si Query retorna filas, resolver duplicados primero (consultar docs/ops/yango_cabinet_claims_mv_duplicates.sql)
```

**Verificación:**
```powershell
cd backend; python scripts/refresh_yango_cabinet_claims_mv.py
# Debe decir: "Refresh completado exitosamente"
```

---

### [T3] status_bucket inválido (no es OK/WARN/CRIT/NO_REFRESH)

**Síntoma:**
```powershell
$r = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/yango/cabinet/mv-health" -UseBasicParsing; $r.Content | ConvertFrom-Json | Select-Object status_bucket
# status_bucket = "INVALID" o campo faltante
```

**Fix:**
```powershell
# [T3.1] Verificar definición de vista (debe tener CASE WHEN para status_bucket)
if (Get-Command psql -ErrorAction SilentlyContinue) { psql "$env:DATABASE_URL" -c "\d+ ops.v_yango_cabinet_claims_mv_health" }

# [T3.2] Re-aplicar SQL health view
if (Get-Command psql -ErrorAction SilentlyContinue) { psql "$env:DATABASE_URL" -f docs/ops/yango_cabinet_claims_mv_health.sql }

# [T3.3] Verificar datos en mv_refresh_log
if (Get-Command psql -ErrorAction SilentlyContinue) { psql "$env:DATABASE_URL" -c "SELECT * FROM ops.mv_refresh_log WHERE schema_name = 'ops' AND mv_name = 'mv_yango_cabinet_claims_for_collection' ORDER BY refresh_started_at DESC LIMIT 5;" }
```

**Verificación:**
```powershell
$r = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/yango/cabinet/mv-health" -UseBasicParsing; $json = $r.Content | ConvertFrom-Json; if ($json.status_bucket -in @("OK","WARN","CRIT","NO_REFRESH")) { echo "✓ status_bucket válido: $($json.status_bucket)" } else { echo "✗ status_bucket inválido: $($json.status_bucket)" }
```

---

### [T4] Export CSV sin BOM (utf-8-sig)

**Síntoma:**
```powershell
$r = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/yango/cabinet/claims/export" -UseBasicParsing; $bytes = [System.Text.Encoding]::UTF8.GetBytes($r.Content); $bom = ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF); if ($bom) { echo "✓ BOM presente" } else { echo "✗ BOM faltante" }
# ✗ BOM faltante
```

**Fix:**
```powershell
# Verificar código backend (backend/app/api/v1/yango_payments.py línea ~1134)
# Buscar: encoding='utf-8-sig' en función export_claims_csv
# Si no está, el código debe usar: response = StreamingResponse(..., headers={...}, media_type="text/csv; charset=utf-8-sig")
# NO hay fix automático, requiere cambio de código
```

**Verificación:**
```powershell
$r = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/yango/cabinet/claims/export" -UseBasicParsing; $bytes = [System.Text.Encoding]::UTF8.GetBytes($r.Content); if ($bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) { echo "✓ BOM utf-8-sig presente" } else { echo "✗ BOM faltante" }
```

---

### [T5] Frontend no carga ruta /pagos/yango-cabinet-claims

**Síntoma:**
```
Abrir: http://localhost:3000/pagos/yango-cabinet-claims
# Error 404 o página en blanco
```

**Fix:**
```powershell
# [T5.1] Verificar que ruta existe en frontend/app
if (Test-Path "frontend\app\pagos\yango-cabinet-claims\page.tsx") { echo "✓ Ruta existe" } else { echo "✗ Ruta NO existe" }

# [T5.2] Verificar que Sidebar tiene la ruta (frontend/components/Sidebar.tsx línea ~47)
Select-String -Path "frontend\components\Sidebar.tsx" -Pattern "yango-cabinet-claims"

# [T5.3] Reiniciar frontend
cd frontend; npm run dev
```

**Verificación:**
```powershell
Start-Process "http://localhost:3000/pagos/yango-cabinet-claims"
# Debe cargar sin errores 404
```

---

### [T6] psql no encontrado / DATABASE_URL vacío

**Síntoma:**
```powershell
Get-Command psql -ErrorAction SilentlyContinue
# Error: No se encuentra el comando
# O
echo $env:DATABASE_URL
# (vacío)
```

**Fix:**
```powershell
# [T6.1] DATABASE_URL: usar default o crear .env
if (-not $env:DATABASE_URL) { $env:DATABASE_URL = "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral" }
echo "DATABASE_URL: $env:DATABASE_URL"

# [T6.2] psql: NO es necesario, scripts Python funcionan sin psql
# Todos los pasos SQL pueden ejecutarse vía scripts Python o endpoints
# Ejemplo: aplicar health view vía Python script (crear temporal si es necesario)

# [T6.3] Alternativa: instalar psql (PostgreSQL client)
# Descargar: https://www.postgresql.org/download/windows/
# O usar Chocolatey: choco install postgresql
```

**Verificación:**
```powershell
# Verificar que scripts Python funcionan
cd backend; python scripts/apply_mv_refresh_log_extended.py; cd ..
# Debe funcionar sin psql
```

---

## NOTAS FINALES

- **Scripts fuente de verdad:** `docs/ops/deploy_verify_yango_cabinet_claims.ps1` y `docs/ops/test_yango_cabinet_endpoints.ps1`
- **SQL files:** `backend/sql/ops/` y `docs/ops/`
- **Endpoints backend:** `backend/app/api/v1/yango_payments.py`
- **Ruta frontend:** `frontend/app/pagos/yango-cabinet-claims/page.tsx`
- **DATABASE_URL:** Se lee de env o default en `backend/app/config.py`
- **Todos los comandos son idempotentes** (pueden ejecutarse múltiples veces)

---

## PROMPT PARA CURSOR (si ve este archivo)

Antes de sugerir comandos, buscar en el repo:
1. Rutas exactas de scripts: `glob_file_search` para `**/deploy_verify*.ps1`, `**/refresh_yango_cabinet_claims_mv.py`, `**/apply_mv_refresh_log_extended.py`
2. SQL files: `glob_file_search` para `**/yango_cabinet_claims_mv_health.sql`, `**/mv_refresh_log_extended.sql`, `**/mv_yango_cabinet_claims_unique_index.sql`
3. Endpoints: `grep` para `yango.*cabinet.*claims` en `backend/app/api`
4. Frontend routes: `grep` para `/pagos/yango-cabinet-claims` en `frontend`
5. DATABASE_URL: leer `backend/app/config.py` para default






