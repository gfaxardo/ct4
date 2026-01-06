# CT4 Ops Health — Guía de Ejecución Manual

## Prerrequisitos

### 1. Verificar Entorno Virtual

**Windows PowerShell:**
```powershell
# Navegar al directorio del proyecto
cd C:\cursor\CT4

# Activar entorno virtual
.\backend\venv\Scripts\Activate.ps1

# Si hay problemas de política de ejecución:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Windows CMD:**
```cmd
cd C:\cursor\CT4
backend\venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
cd /path/to/CT4
source backend/venv/bin/activate
```

### 2. Verificar Dependencias

```bash
# Verificar que Python esté usando el venv
python --version
which python  # Linux/Mac
where python  # Windows

# Verificar dependencias instaladas
pip list | findstr "pydantic sqlalchemy"  # Windows
pip list | grep -E "pydantic|sqlalchemy"  # Linux/Mac
```

Si faltan dependencias:
```bash
pip install -r backend/requirements.txt
```

### 3. Verificar Conexión a Base de Datos

El script necesita acceso a la base de datos. Verificar que `DATABASE_URL` esté configurada:

**Opción A: Desde app.config (recomendado)**
```bash
# Verificar que app.config.py existe y tiene DATABASE_URL
cat backend/app/config.py | grep DATABASE_URL
```

**Opción B: Variable de entorno**
```powershell
# Windows PowerShell
$env:DATABASE_URL = "postgresql://user:password@host:port/database"

# Windows CMD
set DATABASE_URL=postgresql://user:password@host:port/database

# Linux/Mac
export DATABASE_URL="postgresql://user:password@host:port/database"
```

---

## Ejecución Paso a Paso

### Paso 1: Navegar al Directorio del Proyecto

```powershell
# Windows
cd C:\cursor\CT4

# Linux/Mac
cd /path/to/CT4
```

### Paso 2: Activar Entorno Virtual

```powershell
# Windows PowerShell
.\backend\venv\Scripts\Activate.ps1

# Deberías ver (venv) al inicio del prompt
```

### Paso 3: Verificar que Estás en el Entorno Correcto

```bash
python --version
# Debería mostrar Python 3.x.x

pip list | findstr "sqlalchemy"
# Debería mostrar SQLAlchemy instalado
```

### Paso 4: Ejecutar el Script de Auditoría

```bash
python backend/scripts/run_ops_health_audit.py
```

### Paso 5: Observar la Salida

El script mostrará:

```
======================================================================
CT4 OPS HEALTH — AUDITORÍA AUTOMÁTICA
======================================================================

Inicio: 2026-01-01 21:57:33

======================================================================
FASE 1: DISCOVERY
======================================================================
  Ejecutando discovery_objects.py...
✓ discovery_objects.py completado
    [OK] Discovery completado. Resultados guardados en: ...
      Total de objetos encontrados: 169

  Ejecutando discovery_dependencies.py...
✓ discovery_dependencies.py completado
    [OK] Discovery de dependencias completado. Resultados guardados en: ...
      Total de dependencias encontradas: 163

  Ejecutando discovery_usage_backend.py...
✓ discovery_usage_backend.py completado
    [OK] Discovery completado. Resultados guardados en: ...
      Total de objetos usados: 73

======================================================================
FASE 2: SOURCE REGISTRY
======================================================================
  Ejecutando populate_source_registry.py...
✓ populate_source_registry.py completado
    [OK] Registry poblado exitosamente
      Nuevos registros: 42
      Registros actualizados: 127

======================================================================
FASE 3: VALIDACIONES
======================================================================
### A. Coverage Real
  Objetos en DB no registrados...
✓ Objetos en DB no registrados: 0
  Objetos registrados pero no existentes...
✓ Objetos registrados pero no existentes: 0

### B. Health Checks
  Obteniendo health checks...
✓ Obteniendo health checks: 13

### C. Estado Global
  Obteniendo estado global...
✓ Obteniendo estado global: 1

### D. Objetos Usados Sin Registro
  Obteniendo objetos usados sin registro...
✓ Objetos usados sin registro: 0

### E. Impactos Críticos
  RAW stale afectando MVs críticas...
✓ RAW stale afectando MVs críticas: 0
  MVs con refresh fallido...
✓ MVs con refresh fallido: 0
  MVs no pobladas...
✓ MVs no pobladas: 0
  MVs críticas sin refresh log...
✓ MVs críticas sin refresh log: 1

======================================================================
FASE 4: GENERACIÓN DE REPORTES
======================================================================
✓ Reporte Markdown generado: docs/backend/OPS_HEALTH_AUDIT_REPORT.md
✓ Reporte JSON generado: docs/backend/OPS_HEALTH_AUDIT_REPORT.json

======================================================================
RESUMEN FINAL
======================================================================
Estado: OK / WARNING / CRITICAL

  Errores: 0
  Advertencias: 2
  OK: 11

  Objetos descubiertos: 169
  Objetos registrados: 169
  Objetos no registrados: 0
  Objetos usados sin registro: 0

✅ SISTEMA SALUDABLE
   (o ⚠️ SISTEMA CON ADVERTENCIAS o ❌ SISTEMA EN ESTADO CRÍTICO)

Reportes disponibles en:
  - docs/backend/OPS_HEALTH_AUDIT_REPORT.md
  - docs/backend/OPS_HEALTH_AUDIT_REPORT.json
```

### Paso 6: Revisar los Reportes Generados

**Reporte Markdown (legible):**
```bash
# Windows
notepad docs\backend\OPS_HEALTH_AUDIT_REPORT.md

# Linux/Mac
cat docs/backend/OPS_HEALTH_AUDIT_REPORT.md
```

**Reporte JSON (estructurado):**
```bash
# Windows PowerShell
Get-Content docs\backend\OPS_HEALTH_AUDIT_REPORT.json | ConvertFrom-Json | ConvertTo-Json -Depth 10

# Linux/Mac (requiere jq)
cat docs/backend/OPS_HEALTH_AUDIT_REPORT.json | jq .
```

---

## Interpretación de Resultados

### Exit Code

El script retorna códigos de salida:

- **0**: OK - Sistema saludable
- **1**: WARNING - Hay advertencias pero no errores críticos
- **2**: CRITICAL - Hay errores críticos que requieren atención inmediata

**Verificar exit code:**
```powershell
# Windows PowerShell
python backend/scripts/run_ops_health_audit.py
echo $LASTEXITCODE

# Linux/Mac
python backend/scripts/run_ops_health_audit.py
echo $?
```

### Estados del Sistema

#### ✅ OK (Exit Code 0)
- No hay errores ni advertencias
- Todos los checks están en estado OK
- Sistema completamente saludable

**Acción:** Ninguna acción requerida.

#### ⚠️ WARNING (Exit Code 1)
- Hay advertencias pero no errores críticos
- Puede haber objetos no registrados
- Puede haber MVs sin refresh log

**Acción:** Revisar reporte y corregir advertencias en las próximas horas/días.

#### ❌ CRITICAL (Exit Code 2)
- Hay errores críticos
- Fuentes RAW stale afectando producción
- MVs fallidas o no pobladas
- Fuentes críticas sin monitoreo

**Acción:** Revisar reporte inmediatamente y corregir errores críticos.

---

## Solución de Problemas

### Error: "No module named 'pydantic_settings'"

**Solución:**
```bash
pip install -r backend/requirements.txt
```

### Error: "DATABASE_URL no está definida"

**Solución:**
```powershell
# Verificar que app.config.py existe
Test-Path backend\app\config.py

# O definir variable de entorno
$env:DATABASE_URL = "postgresql://user:password@host:port/database"
```

### Error: "UnicodeEncodeError"

**Solución:**
El script ya maneja esto automáticamente, pero si persiste:
```powershell
# Windows PowerShell
$OutputEncoding = [System.Text.Encoding]::UTF8
chcp 65001
```

### Error: "can't execute an empty query"

**Solución:**
Verificar que los archivos SQL existen:
```bash
Test-Path backend\sql\ops\discovery_objects.sql
Test-Path backend\sql\ops\discovery_dependencies.sql
```

### Error: "discovery_objects.py falló"

**Solución:**
Ejecutar manualmente para ver el error completo:
```bash
python backend/scripts/discovery_objects.py
```

### Error: "populate_source_registry.py falló"

**Solución:**
Verificar que los CSVs de discovery existen:
```bash
Test-Path backend\sql\ops\discovery_objects.csv
Test-Path backend\sql\ops\discovery_dependencies.csv
Test-Path backend\sql\ops\discovery_usage_backend.csv
```

Si no existen, ejecutar discovery primero:
```bash
python backend/scripts/discovery_objects.py
python backend/scripts/discovery_dependencies.py
python backend/scripts/discovery_usage_backend.py
```

---

## Ejecución Individual de Scripts

Si necesitas ejecutar los scripts por separado:

### 1. Discovery de Objetos
```bash
python backend/scripts/discovery_objects.py
# Genera: backend/sql/ops/discovery_objects.csv
```

### 2. Discovery de Dependencias
```bash
python backend/scripts/discovery_dependencies.py
# Genera: backend/sql/ops/discovery_dependencies.csv
```

### 3. Discovery de Uso
```bash
python backend/scripts/discovery_usage_backend.py
# Genera: backend/sql/ops/discovery_usage_backend.csv
```

### 4. Población del Registry
```bash
python backend/scripts/populate_source_registry.py
# Actualiza: ops.source_registry
```

---

## Validación Post-Ejecución

### Verificar CSVs Generados
```bash
# Windows
Get-ChildItem backend\sql\ops\discovery_*.csv

# Linux/Mac
ls -lh backend/sql/ops/discovery_*.csv
```

### Verificar Registry en DB
```sql
-- Conectar a PostgreSQL
psql -h <host> -p <port> -U <user> -d <database>

-- Verificar registros
SELECT COUNT(*) FROM ops.source_registry;

-- Ver algunos registros
SELECT schema_name, object_name, criticality, layer 
FROM ops.source_registry 
ORDER BY criticality DESC, schema_name, object_name 
LIMIT 10;
```

### Verificar Health Checks
```sql
SELECT check_key, severity, status, message 
FROM ops.v_health_checks 
WHERE status != 'OK' 
ORDER BY severity, check_key;
```

### Verificar Estado Global
```sql
SELECT * FROM ops.v_health_global;
```

---

## Automatización (Opcional)

### Cron Job (Linux/Mac)

```bash
# Editar crontab
crontab -e

# Ejecutar diariamente a las 2 AM
0 2 * * * cd /path/to/CT4 && /path/to/venv/bin/python backend/scripts/run_ops_health_audit.py >> /var/log/ops-health-audit.log 2>&1
```

### Task Scheduler (Windows)

1. Abrir "Programador de tareas"
2. Crear tarea básica
3. Configurar:
   - **Nombre:** CT4 Ops Health Audit
   - **Activador:** Diariamente a las 2:00 AM
   - **Acción:** Iniciar programa
   - **Programa:** `C:\cursor\CT4\backend\venv\Scripts\python.exe`
   - **Argumentos:** `backend\scripts\run_ops_health_audit.py`
   - **Iniciar en:** `C:\cursor\CT4`

### Script PowerShell para Automatización

```powershell
# save_ops_health_audit.ps1
$ErrorActionPreference = "Stop"

# Activar venv
& "C:\cursor\CT4\backend\venv\Scripts\Activate.ps1"

# Ejecutar auditoría
& python "C:\cursor\CT4\backend\scripts\run_ops_health_audit.py"

# Verificar exit code
if ($LASTEXITCODE -eq 2) {
    Write-Host "CRITICAL: Revisar reportes inmediatamente" -ForegroundColor Red
    # Enviar alerta (email, Slack, etc.)
}
```

---

## Comandos Rápidos de Referencia

```powershell
# 1. Activar venv
.\backend\venv\Scripts\Activate.ps1

# 2. Ejecutar auditoría completa
python backend/scripts/run_ops_health_audit.py

# 3. Ver reporte Markdown
notepad docs\backend\OPS_HEALTH_AUDIT_REPORT.md

# 4. Ver reporte JSON (formateado)
Get-Content docs\backend\OPS_HEALTH_AUDIT_REPORT.json | ConvertFrom-Json | ConvertTo-Json -Depth 10

# 5. Verificar exit code
echo $LASTEXITCODE
```

---

## Referencias

- [Documentación del Script de Auditoría](OPS_HEALTH_AUDIT_SCRIPT.md)
- [Arquitectura del Sistema](OPS_HEALTH_SYSTEM_ARCHITECTURE.md)
- [Guía de Ejecución](OPS_HEALTH_EXECUTION_GUIDE.md)








