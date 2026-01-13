# Crear Vista v_payments_driver_matrix_cabinet - Instrucciones Manuales

## Opción 1: Usar psql desde PowerShell

```powershell
# Navegar al directorio del script
cd C:\Users\Pc\Documents\Cursor Proyectos\ct4\backend\scripts

# Ejecutar el script
.\create_driver_matrix_view.ps1
```

## Opción 2: Ejecutar SQL manualmente con psql

```powershell
# Conectarse a PostgreSQL
$env:PGPASSWORD = "37>MNA&-35+"
psql -h 168.119.226.236 -p 5432 -U yego_user -d yego_integral

# Dentro de psql, ejecutar:
\i C:/Users/Pc/Documents/Cursor\ Proyectos/ct4/backend/sql/ops/v_payments_driver_matrix_cabinet.sql

# O copiar y pegar el contenido del archivo SQL directamente
```

## Opción 3: Usar un cliente gráfico (pgAdmin, DBeaver, etc.)

1. Conectarse a la base de datos:
   - Host: 168.119.226.236
   - Port: 5432
   - Database: yego_integral
   - User: yego_user
   - Password: 37>MNA&-35+

2. Abrir el archivo SQL:
   - `backend/sql/ops/v_payments_driver_matrix_cabinet.sql`

3. Ejecutar el script completo

## Opción 4: Desde Python (usando SQLAlchemy)

```python
from app.db import engine
from sqlalchemy import text

# Leer archivo SQL
with open('backend/sql/ops/v_payments_driver_matrix_cabinet.sql', 'r', encoding='utf-8') as f:
    sql_content = f.read()

# Ejecutar
with engine.connect() as conn:
    conn.execute(text(sql_content))
    conn.commit()
```

## Verificación

Después de crear la vista, verifica que existe:

```sql
-- Verificar que la vista existe
SELECT COUNT(*) FROM ops.v_payments_driver_matrix_cabinet;

-- Ver estructura
\d ops.v_payments_driver_matrix_cabinet
```





