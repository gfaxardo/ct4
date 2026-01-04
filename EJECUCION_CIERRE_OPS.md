# EJECUCIÓN CIERRE OPERATIVO - Yango Cabinet Claims

---

## SETUP INICIAL

**COMANDO:**
```powershell
cd C:\cursor\CT4
if (-not $env:DATABASE_URL) { $env:DATABASE_URL = "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral" }
echo "DATABASE_URL=$env:DATABASE_URL"
```

**OUTPUT ESPERADO:**
```
DATABASE_URL setado a default
DATABASE_URL=postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral
```

**SI FALLA → COMANDO DE CORRECCIÓN:**
```
# Verificar conexión manual:
python -c "import os; from sqlalchemy import create_engine; engine = create_engine(os.getenv('DATABASE_URL', 'postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral')); conn = engine.connect(); print('OK')"
```

---

## PASO 1: Aplicar migración mv_refresh_log_extended

**COMANDO:**
```powershell
cd backend; python scripts/apply_mv_refresh_log_extended.py; cd ..
```

**OUTPUT ESPERADO:**
```
INFO:__main__:Leyendo SQL: ...\backend\sql\ops\mv_refresh_log_extended.sql
INFO:__main__:Ejecutando SQL...
INFO:__main__:✓ Extensión de ops.mv_refresh_log aplicada
INFO:__main__:✓ Verificación: todas las columnas nuevas existen
INFO:__main__:  Columnas: host, meta, refresh_finished_at, refresh_started_at, rows_after_refresh
```

**SI FALLA → COMANDO DE CORRECCIÓN:**
```
# Verificar que Python tiene acceso a BD:
cd backend; python -c "from app.config import settings; from sqlalchemy import create_engine; engine = create_engine(settings.database_url); conn = engine.connect(); print('Conexión OK')"; cd ..
```

---

## PASO 2: Crear vista de health check

**COMANDO:**
```powershell
if (Get-Command psql -ErrorAction SilentlyContinue) { psql "$env:DATABASE_URL" -f docs/ops/yango_cabinet_claims_mv_health.sql } else { echo "SKIP: psql no disponible, vista se creará vía Python si es necesario" }
```

**OUTPUT ESPERADO:**
```
CREATE VIEW
```
O si psql no está:
```
SKIP: psql no disponible, vista se creará vía Python si es necesario
```

**SI FALLA → COMANDO DE CORRECCIÓN:**
```
# Verificar que SQL file existe:
Test-Path docs/ops/yango_cabinet_claims_mv_health.sql

# Si psql falla, aplicar vía Python (crear script temporal):
cd backend; python -c "from app.db import engine; from sqlalchemy import text; sql = open('../docs/ops/yango_cabinet_claims_mv_health.sql', 'r', encoding='utf-8').read(); engine.connect().execute(text(sql)); engine.connect().commit(); print('Vista creada')"; cd ..
```

---

## PASO 3: Verificar duplicados en MV

**COMANDO:**
```powershell
if (Get-Command psql -ErrorAction SilentlyContinue) { psql "$env:DATABASE_URL" -c "SELECT driver_id, milestone_value, COUNT(*) AS count_duplicates FROM ops.mv_yango_cabinet_claims_for_collection GROUP BY driver_id, milestone_value HAVING COUNT(*) > 1 ORDER BY count_duplicates DESC LIMIT 10;" } else { cd backend; python -c "from app.db import engine; from sqlalchemy import text; result = engine.connect().execute(text(\"SELECT driver_id, milestone_value, COUNT(*) AS count_duplicates FROM ops.mv_yango_cabinet_claims_for_collection GROUP BY driver_id, milestone_value HAVING COUNT(*) > 1 ORDER BY count_duplicates DESC LIMIT 10\")); rows = result.fetchall(); print(f'Duplicados encontrados: {len(rows)}'); [print(f'{r[0]} | {r[1]} | {r[2]}') for r in rows]"; cd .. }
```

**OUTPUT ESPERADO:**
```
(0 rows)
```
O lista vacía si no hay duplicados.

**SI FALLA → COMANDO DE CORRECCIÓN:**
```
# Si hay duplicados, NO crear índice único. Revisar:
if (Get-Command psql -ErrorAction SilentlyContinue) { psql "$env:DATABASE_URL" -f docs/ops/yango_cabinet_claims_mv_duplicates.sql } else { echo "Ver duplicados manualmente en BD" }
```

---

## PASO 4: Crear índice único (SOLO si Paso 3 retornó 0 filas)

**COMANDO:**
```powershell
if (Get-Command psql -ErrorAction SilentlyContinue) { psql "$env:DATABASE_URL" -f backend/sql/ops/mv_yango_cabinet_claims_unique_index.sql } else { echo "SKIP: psql no disponible, índice se creará automáticamente si es necesario en refresh" }
```

**OUTPUT ESPERADO:**
```
CREATE UNIQUE INDEX
```
O mensaje de skip si psql no está.

**SI FALLA → COMANDO DE CORRECCIÓN:**
```
# Si falla por duplicados, resolver primero (Paso 3 debe retornar 0 filas)
# Si falla por psql, continuar (script de refresh intentará CONCURRENTLY automáticamente)
echo "Índice se creará automáticamente durante refresh si no hay duplicados"
```

---

## PASO 5: Refrescar MV manualmente

**COMANDO:**
```powershell
cd backend; python scripts/refresh_yango_cabinet_claims_mv.py; cd ..
```

**OUTPUT ESPERADO:**
```
[OK] Refresh completado exitosamente
```
O similar con mensaje de éxito.

**SI FALLA → COMANDO DE CORRECCIÓN:**
```
# Si falla CONCURRENTLY por índice faltante, el script automáticamente intenta sin CONCURRENTLY
# Si falla por otro error, revisar logs:
cd backend; python scripts/refresh_yango_cabinet_claims_mv.py 2>&1 | Select-Object -Last 20
```

---

## PASO 6: Ejecutar gate deploy_verify (fail-fast)

**COMANDO:**
```powershell
.\docs\ops\deploy_verify_yango_cabinet_claims.ps1 -FailFast
```

**OUTPUT ESPERADO:**
```
================================================================================
CHECKLIST: Deploy + Verificación Bloques B/C/D
...
[1] D1: Aplicar migración mv_refresh_log_extended
  ✓ PASSED
...
✓ TODOS LOS CHECKS PASARON
```

**SI FALLA → COMANDO DE CORRECCIÓN:**
```
# Revisar qué check falló en el output
# Ejecutar sin fail-fast para ver todos los errores:
.\docs\ops\deploy_verify_yango_cabinet_claims.ps1 -FailFast:$false
```

---

## PASO 7: Ejecutar smoke tests de endpoints

**COMANDO:**
```powershell
.\docs\ops\test_yango_cabinet_endpoints.ps1 -FailFast
```

**OUTPUT ESPERADO:**
```
=== Validación de Endpoints Yango Cabinet Claims ===
...
[TEST] B1.1: Listado básico (sin filtros)
  ✓ Status: 200 (OK)
...
=== Resumen ===
Tests pasados: 5
Tests fallidos: 0

✓ Todos los tests pasaron
```

**SI FALLA → COMANDO DE CORRECCIÓN:**
```
# Verificar que backend está corriendo:
try { Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 2 } catch { echo "Backend NO responde. Iniciar: cd backend; python -m uvicorn app.main:app --reload" }

# Si backend no responde, iniciarlo y repetir test
```

---

## MODO RÁPIDO (uso diario)

```powershell
cd C:\cursor\CT4
cd backend; python scripts/refresh_yango_cabinet_claims_mv.py; cd ..
.\docs\ops\deploy_verify_yango_cabinet_claims.ps1 -FailFast
Invoke-WebRequest -Uri "http://localhost:8000/api/v1/yango/cabinet/mv-health" -UseBasicParsing | Select-Object -ExpandProperty Content | ConvertFrom-Json | Format-List
```

---

## CHECK UI (30 segundos)

1. Abrir: `http://localhost:3000/pagos/yango-cabinet-claims`
2. Verificar: página carga sin 404
3. Verificar: tabla muestra datos o mensaje "No hay claims"
4. Verificar: filtros funcionan (date_from, milestone_value, search)
5. Verificar: botón "Exportar CSV" descarga archivo
6. Verificar: click en fila abre drilldown modal

**Si falla:**
```powershell
# Verificar frontend corriendo:
try { Invoke-WebRequest -Uri "http://localhost:3000" -UseBasicParsing -TimeoutSec 2 } catch { echo "Frontend NO responde. Iniciar: cd frontend; npm run dev" }

# Verificar ruta existe:
Test-Path frontend\app\pagos\yango-cabinet-claims\page.tsx
```


