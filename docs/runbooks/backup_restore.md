# Runbook: Backup y Restauración del Proyecto CT4

## Propósito

Este runbook documenta el proceso de backup y restauración del proyecto CT4 para prevenir pérdida de código y datos.

---

## Backup Automático

### Script de Backup

El proyecto incluye un script PowerShell para crear backups completos:

```powershell
# Backup del repositorio solamente
.\scripts\backup_project.ps1

# Backup del repositorio + base de datos
.\scripts\backup_project.ps1 -IncludeDatabase
```

### Ubicación de Backups

Los backups se guardan en el directorio `backups/` (gitignored):

```
backups/
  ├── CT4_backup_20250115_143022.zip    # Backup del repo
  └── CT4_backup_20250115_143022.sql    # Backup de DB (si se incluye)
```

### Frecuencia Recomendada

- **Diario**: Antes de cambios importantes o al final del día
- **Semanal**: Backup completo (repo + DB) cada lunes
- **Pre-deploy**: Siempre antes de hacer deploy a producción

---

## Backup Manual

### 1. Backup del Repositorio

#### Opción A: Usar Git (Recomendado)

```powershell
# Verificar estado
git status

# Crear commit de trabajo en progreso
git add .
git commit -m "WIP: trabajo en progreso"

# Push a remoto
git push origin master
```

#### Opción B: Zip Manual

```powershell
# Crear zip excluyendo node_modules, venv, etc.
Compress-Archive -Path * -DestinationPath "backup_manual_$(Get-Date -Format 'yyyyMMdd').zip" -Exclude @("node_modules", "venv", "__pycache__", ".git")
```

### 2. Backup de Base de Datos

#### Requisitos

- PostgreSQL client tools instalados (`pg_dump`)
- Variables de entorno configuradas:
  - `DB_HOST`: Host de la base de datos
  - `DB_PORT`: Puerto (default: 5432)
  - `DB_NAME`: Nombre de la base de datos
  - `DB_USER`: Usuario de la base de datos
  - `DB_PASSWORD`: Contraseña

#### Comando Manual

```powershell
# Backup comprimido (formato custom)
$env:PGPASSWORD = "tu_password"
pg_dump -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_USER -d $env:DB_NAME -F c -f "backup_db_$(Get-Date -Format 'yyyyMMdd').sql"

# Backup SQL plano (más grande pero más portable)
pg_dump -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_USER -d $env:DB_NAME -f "backup_db_$(Get-Date -Format 'yyyyMMdd').sql"
```

#### Desde Docker Compose

Si usas docker-compose, puedes hacer backup del contenedor:

```powershell
# Backup desde contenedor PostgreSQL
docker exec -t ct4_postgres pg_dump -U yego_user yego_integral > backup_db_$(Get-Date -Format 'yyyyMMdd').sql
```

---

## Restauración

### 1. Restaurar Repositorio

#### Desde Git (Recomendado)

```powershell
# Clonar desde remoto
git clone https://github.com/gfaxardo/ct4.git
cd ct4

# O si ya existe el repo, hacer pull
git pull origin master
```

#### Desde Zip

```powershell
# Descomprimir backup
Expand-Archive -Path "backups/CT4_backup_20250115_143022.zip" -DestinationPath "."

# Restaurar dependencias
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

cd ..\frontend
npm install
```

### 2. Restaurar Base de Datos

#### Backup Custom (Comprimido)

```powershell
$env:PGPASSWORD = "tu_password"
pg_restore -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_USER -d $env:DB_NAME -c "backup_db_20250115.sql"
```

#### Backup SQL Plano

```powershell
$env:PGPASSWORD = "tu_password"
psql -h $env:DB_HOST -p $env:DB_PORT -U $env:DB_USER -d $env:DB_NAME -f "backup_db_20250115.sql"
```

#### Desde Docker Compose

```powershell
# Restaurar en contenedor
cat backup_db_20250115.sql | docker exec -i ct4_postgres psql -U yego_user yego_integral
```

---

## Verificación Post-Restauración

### 1. Verificar Repositorio

```powershell
# Verificar que el repo está limpio
git status

# Verificar que los archivos críticos existen
Test-Path "backend/app/main.py"
Test-Path "frontend/app/layout.tsx"
Test-Path "docs/ops/yango_cabinet_claims_to_collect.sql"
```

### 2. Verificar Base de Datos

```sql
-- Verificar que las vistas críticas existen
SELECT table_name 
FROM information_schema.views 
WHERE table_schema = 'ops' 
  AND table_name IN (
    'v_yango_cabinet_claims_exigimos',
    'mv_yango_cabinet_claims_for_collection',
    'v_yango_cabinet_claims_exec_summary'
  );

-- Verificar que hay datos
SELECT COUNT(*) FROM ops.v_yango_cabinet_claims_exigimos;
```

### 3. Verificar Aplicación

```powershell
# Backend
cd backend
.\venv\Scripts\activate
uvicorn app.main:app --reload

# Frontend (otra terminal)
cd frontend
npm run dev
```

---

## Troubleshooting

### Error: "pg_dump no encontrado"

**Solución**: Instalar PostgreSQL client tools:
- Windows: Descargar desde https://www.postgresql.org/download/windows/
- O usar chocolatey: `choco install postgresql`

### Error: "No se puede conectar a la base de datos"

**Solución**: Verificar:
1. Variables de entorno configuradas correctamente
2. Firewall permite conexión al puerto 5432
3. Servicio PostgreSQL está corriendo

### Error: "Espacio en disco insuficiente"

**Solución**: 
1. Limpiar backups antiguos: `Remove-Item backups/CT4_backup_*.zip -Force`
2. Mover backups a almacenamiento externo
3. Usar backup incremental de Git en lugar de zip completo

---

## Mejores Prácticas

1. **Versionado Git**: Siempre hacer commit y push antes de cambios grandes
2. **Backups Automáticos**: Configurar tarea programada para backups diarios
3. **Backups Remotos**: Subir backups críticos a almacenamiento en la nube
4. **Documentación**: Documentar cambios importantes en commits descriptivos
5. **Pruebas de Restauración**: Probar restauración periódicamente para validar backups

---

## Referencias

- Script de backup: `scripts/backup_project.ps1`
- Documentación PostgreSQL: https://www.postgresql.org/docs/
- Git documentation: https://git-scm.com/doc









