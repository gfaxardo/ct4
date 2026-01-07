# ============================================================================
# Script de Backup del Proyecto CT4
# ============================================================================
# PROPÓSITO:
# Crear backup completo del repositorio y opcionalmente de la base de datos
# 
# USO:
#   .\scripts\backup_project.ps1
#   .\scripts\backup_project.ps1 -IncludeDatabase
# ============================================================================

param(
    [switch]$IncludeDatabase = $false
)

$ErrorActionPreference = "Stop"

# Configuración
$BackupDir = "backups"
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupName = "CT4_backup_$Timestamp"
$BackupPath = Join-Path $BackupDir $BackupName

# Crear directorio de backups si no existe
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
    Write-Host "✓ Directorio de backups creado: $BackupDir" -ForegroundColor Green
}

Write-Host "`n=== Iniciando Backup del Proyecto CT4 ===" -ForegroundColor Cyan
Write-Host "Timestamp: $Timestamp" -ForegroundColor Gray
Write-Host "Directorio de backup: $BackupPath`n" -ForegroundColor Gray

# 1. Backup del repositorio completo (zip)
Write-Host "[1/2] Creando backup del repositorio..." -ForegroundColor Yellow

$RepoZip = "$BackupPath.zip"
$ExcludePatterns = @(
    "node_modules",
    "venv",
    "__pycache__",
    "*.pyc",
    ".git",
    "backups",
    "*.log"
)

# Obtener ruta del script (directorio raíz del proyecto)
$ScriptDir = Split-Path -Parent $PSScriptRoot
$ProjectRoot = if ($ScriptDir) { $ScriptDir } else { $PWD }

# Crear archivo temporal con lista de exclusiones
$ExcludeFile = Join-Path $env:TEMP "backup_exclude_$Timestamp.txt"
$ExcludePatterns | ForEach-Object { Add-Content -Path $ExcludeFile -Value $_ }

try {
    # Usar Compress-Archive (más simple pero menos control)
    # Alternativa: usar 7zip si está disponible
    $TempBackupDir = Join-Path $env:TEMP "backup_temp_$Timestamp"
    if (Test-Path $TempBackupDir) {
        Remove-Item -Recurse -Force $TempBackupDir
    }
    New-Item -ItemType Directory -Path $TempBackupDir | Out-Null
    
    # Copiar archivos excluyendo patrones
    Get-ChildItem -Path $ProjectRoot -Recurse | Where-Object {
        $item = $_
        $shouldExclude = $false
        foreach ($pattern in $ExcludePatterns) {
            if ($item.FullName -like "*\$pattern\*" -or $item.Name -like $pattern) {
                $shouldExclude = $true
                break
            }
        }
        -not $shouldExclude
    } | Copy-Item -Destination {
        $_.FullName.Replace($ProjectRoot, $TempBackupDir)
    } -Force -ErrorAction SilentlyContinue
    
    Compress-Archive -Path "$TempBackupDir\*" -DestinationPath $RepoZip -Force
    Remove-Item -Recurse -Force $TempBackupDir
    
    $ZipSize = (Get-Item $RepoZip).Length / 1MB
    Write-Host "✓ Backup del repositorio creado: $RepoZip ($([math]::Round($ZipSize, 2)) MB)" -ForegroundColor Green
} catch {
    Write-Host "✗ Error al crear backup del repositorio: $_" -ForegroundColor Red
    if (Test-Path $TempBackupDir) {
        Remove-Item -Recurse -Force $TempBackupDir -ErrorAction SilentlyContinue
    }
    throw
} finally {
    if (Test-Path $ExcludeFile) {
        Remove-Item $ExcludeFile -ErrorAction SilentlyContinue
    }
}

# 2. Backup de base de datos (opcional)
if ($IncludeDatabase) {
    Write-Host "`n[2/2] Creando backup de la base de datos..." -ForegroundColor Yellow
    
    # Leer variables de entorno desde .env o config
    $DbHost = $env:DB_HOST
    $DbPort = $env:DB_PORT ?? "5432"
    $DbName = $env:DB_NAME
    $DbUser = $env:DB_USER
    $DbPassword = $env:DB_PASSWORD
    
    if (-not $DbHost -or -not $DbName -or -not $DbUser) {
        Write-Host "⚠ Variables de entorno de DB no configuradas. Saltando backup de DB." -ForegroundColor Yellow
        Write-Host "  Configurar: DB_HOST, DB_NAME, DB_USER, DB_PASSWORD" -ForegroundColor Gray
    } else {
        $DbBackupFile = "$BackupPath.sql"
        
        # Verificar si pg_dump está disponible
        $pgDumpPath = Get-Command pg_dump -ErrorAction SilentlyContinue
        if (-not $pgDumpPath) {
            Write-Host "⚠ pg_dump no encontrado en PATH. Saltando backup de DB." -ForegroundColor Yellow
            Write-Host "  Instalar PostgreSQL client tools para habilitar backup de DB." -ForegroundColor Gray
        } else {
            try {
                # Crear variable de entorno temporal para la contraseña
                $env:PGPASSWORD = $DbPassword
                
                $pgDumpArgs = @(
                    "-h", $DbHost,
                    "-p", $DbPort,
                    "-U", $DbUser,
                    "-d", $DbName,
                    "-F", "c",  # Formato custom (compressed)
                    "-f", $DbBackupFile,
                    "--no-owner",
                    "--no-privileges"
                )
                
                & pg_dump $pgDumpArgs
                
                if ($LASTEXITCODE -eq 0) {
                    $DbSize = (Get-Item $DbBackupFile).Length / 1MB
                    Write-Host "✓ Backup de DB creado: $DbBackupFile ($([math]::Round($DbSize, 2)) MB)" -ForegroundColor Green
                } else {
                    Write-Host "✗ Error al crear backup de DB (exit code: $LASTEXITCODE)" -ForegroundColor Red
                }
            } catch {
                Write-Host "✗ Error al ejecutar pg_dump: $_" -ForegroundColor Red
            } finally {
                # Limpiar variable de entorno
                Remove-Item Env:\PGPASSWORD -ErrorAction SilentlyContinue
            }
        }
    }
} else {
    Write-Host "`n[2/2] Backup de base de datos omitido (usar -IncludeDatabase para incluir)" -ForegroundColor Gray
}

# Resumen
Write-Host "`n=== Backup Completado ===" -ForegroundColor Cyan
Write-Host "Ubicación: $BackupPath.zip" -ForegroundColor Green
if ($IncludeDatabase -and (Test-Path "$BackupPath.sql")) {
    Write-Host "DB Backup: $BackupPath.sql" -ForegroundColor Green
}
Write-Host "`nPara restaurar:" -ForegroundColor Yellow
Write-Host "  1. Descomprimir: Expand-Archive -Path `"$BackupPath.zip`" -DestinationPath `".`"" -ForegroundColor Gray
if ($IncludeDatabase -and (Test-Path "$BackupPath.sql")) {
    Write-Host "  2. Restaurar DB: pg_restore -h HOST -U USER -d DBNAME `"$BackupPath.sql`"" -ForegroundColor Gray
}
Write-Host ""









