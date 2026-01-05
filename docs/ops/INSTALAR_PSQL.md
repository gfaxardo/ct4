# Cómo Instalar psql en Windows

## Opción 1: Instalador de PostgreSQL (Recomendado)

### Pasos:

1. **Descargar PostgreSQL**:
   - Visita: https://www.postgresql.org/download/windows/
   - Descarga el instalador de EnterpriseDB (versión más reciente)

2. **Ejecutar el instalador**:
   - Durante la instalación, en la pantalla "Select Components":
     - ✅ Marca: **Command Line Tools**
     - ❌ Desmarca: **PostgreSQL Server** (si solo necesitas el cliente)
     - ❌ Desmarca: **pgAdmin 4** (opcional, interfaz gráfica)

3. **Configurar PATH**:
   - Después de instalar, agrega la ruta al PATH:
     - Ruta típica: `C:\Program Files\PostgreSQL\16\bin`
     - O busca en: `C:\Program Files\PostgreSQL\<versión>\bin`

   **Cómo agregar al PATH:**
   - Presiona `Win + R`, escribe `sysdm.cpl` y presiona Enter
   - Ve a la pestaña "Opciones avanzadas"
   - Haz clic en "Variables de entorno"
   - En "Variables del sistema", selecciona "Path" y haz clic en "Editar"
   - Haz clic en "Nuevo" y agrega: `C:\Program Files\PostgreSQL\16\bin`
   - Haz clic en "Aceptar" en todas las ventanas

4. **Verificar instalación**:
   ```powershell
   psql --version
   ```

## Opción 2: Chocolatey (Si tienes Chocolatey instalado)

```powershell
choco install postgresql --params '/Password:postgres' --version=16.0.0
```

O solo las herramientas de línea de comandos:
```powershell
choco install postgresql-tools
```

## Opción 3: Usar el Script Python (Ya implementado)

Si no quieres instalar psql, ya tienes scripts de Python que hacen lo mismo:

```powershell
# Ejecutar script SQL usando Python
cd backend
.\venv\Scripts\Activate.ps1
python scripts\apply_yango_cabinet_claims_mv_health.py
```

O usar el script de PowerShell:
```powershell
.\docs\ops\apply_yango_cabinet_claims_mv_health.ps1
```

## Verificar que psql funciona

Después de instalar y configurar el PATH, abre una **nueva** ventana de PowerShell y ejecuta:

```powershell
psql --version
```

Si ves la versión, está funcionando correctamente.

## Uso de psql con tu base de datos

Una vez instalado, puedes usar:

```powershell
# Conectar directamente
psql "$env:DATABASE_URL"

# O ejecutar un archivo SQL
psql "$env:DATABASE_URL" -f docs/ops/yango_cabinet_claims_mv_health.sql

# O con variables explícitas
psql -h 168.119.226.236 -p 5432 -U yego_user -d yego_integral -f docs/ops/yango_cabinet_claims_mv_health.sql
```

## Nota sobre la contraseña

Si usas `psql` directamente, te pedirá la contraseña. La contraseña es: `37>MNA&-35+`

Para evitar escribirla cada vez, puedes crear un archivo `.pgpass` en tu directorio home:
- Windows: `C:\Users\<tu_usuario>\.pgpass`
- Contenido: `168.119.226.236:5432:yego_integral:yego_user:37>MNA&-35+`
- Permisos: Solo lectura para el usuario (en Windows, clic derecho > Propiedades > Seguridad)



