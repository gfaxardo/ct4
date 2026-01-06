# Instrucciones para aplicar el fix de M1 Achieved

## Opción 1: Usar el script PowerShell (Recomendado)

```powershell
.\apply_m1_fix.ps1 -DatabaseUrl "postgresql://usuario:password@host:port/database"
```

## Opción 2: Ejecutar comandos manualmente

### Si psql está en el PATH:
```powershell
# 1. Aplicar vista actualizada
psql $env:DATABASE_URL -f backend/sql/ops/v_payments_driver_matrix_cabinet.sql

# 2. Ejecutar script de debug (opcional)
psql $env:DATABASE_URL -f backend/scripts/sql/debug_m1_achieved_gap.sql

# 3. Ejecutar verificación completa
psql $env:DATABASE_URL -f backend/scripts/sql/verify_claims_achieved_source_fix.sql
```

### Si psql NO está en el PATH (usar ruta completa):
```powershell
# Definir ruta de psql
$psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"

# O buscar automáticamente:
$psql = (Get-ChildItem -Path "C:\Program Files\PostgreSQL" -Recurse -Filter "psql.exe" -ErrorAction SilentlyContinue | Select-Object -First 1).FullName

# 1. Aplicar vista actualizada
& $psql $env:DATABASE_URL -f backend/sql/ops/v_payments_driver_matrix_cabinet.sql

# 2. Ejecutar script de debug (opcional)
& $psql $env:DATABASE_URL -f backend/scripts/sql/debug_m1_achieved_gap.sql

# 3. Ejecutar verificación completa
& $psql $env:DATABASE_URL -f backend/scripts/sql/verify_claims_achieved_source_fix.sql
```

### Si DATABASE_URL no está configurada:
```powershell
# Usar la URL por defecto del config.py
$DATABASE_URL = "postgresql://yego_user:37>MNA&-35+@168.119.226.236:5432/yego_integral"

# Luego ejecutar los comandos con $DATABASE_URL en lugar de $env:DATABASE_URL
```

## Opción 3: Si DATABASE_URL está en .env

```bash
# Cargar variables de entorno desde .env (si existe)
# Luego ejecutar:
psql $DATABASE_URL -f backend/sql/ops/v_payments_driver_matrix_cabinet.sql
psql $DATABASE_URL -f backend/scripts/sql/debug_m1_achieved_gap.sql
psql $DATABASE_URL -f backend/scripts/sql/verify_claims_achieved_source_fix.sql
```

## Verificación esperada

Después de ejecutar, deberías ver:

- **CHECK M1-A**: `gap_count = 0` y status `✓ PASS (0 gaps)`
- **CHECK M1-B**: Todos los drivers muestran `✓ ALIGNED`
- **CHECK C**: `duplicate_count = 0` (mantiene grano de 1 fila por driver)

## Notas

- El script de debug es opcional pero útil para ver el gap antes del fix
- La verificación completa incluye todos los checks (A, B, C, D, M1-A, M1-B)
- Si hay errores, revisa la conexión a la base de datos y los permisos

