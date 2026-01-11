# Scripts para Crear Vistas Faltantes

Este directorio contiene scripts para crear automáticamente las vistas faltantes en la base de datos PostgreSQL.

## Vistas que se crean

1. **`ops.v_yango_collection_with_scout`**
   - Vista de cobranza Yango extendida con información de scout
   - Archivo SQL: `backend/scripts/sql/04_yango_collection_with_scout.sql`

2. **`ops.v_claims_payment_status_cabinet`**
   - Vista de estado de pagos de claims cabinet
   - Archivo SQL: `backend/sql/ops/v_claims_payment_status_cabinet.sql`

## Opción 1: Script PowerShell (Windows)

```powershell
cd backend\scripts
.\create_missing_views.ps1
```

**Requisitos:**
- PostgreSQL Client Tools instalado (`psql` en PATH)
- Credenciales de base de datos configuradas (por defecto usa las de `app/config.py`)

**Parámetros opcionales:**
```powershell
.\create_missing_views.ps1 `
    -DatabaseHost "168.119.226.236" `
    -DatabasePort "5432" `
    -DatabaseName "yego_integral" `
    -DatabaseUser "yego_user" `
    -DatabasePassword "tu_password"
```

## Opción 2: Script Python (Multiplataforma)

```bash
cd backend
# Activar entorno virtual
venv\Scripts\activate  # Windows
# o
source venv/bin/activate  # Linux/Mac

# Ejecutar script
python scripts/create_missing_views.py
```

**Requisitos:**
- Entorno virtual activado con dependencias instaladas
- Credenciales de base de datos en `app/config.py` o variables de entorno

## Verificación

Después de ejecutar el script, puedes verificar que las vistas existen:

```sql
SELECT 
    schemaname || '.' || viewname AS view_name
FROM pg_views
WHERE schemaname = 'ops'
    AND viewname IN ('v_yango_collection_with_scout', 'v_claims_payment_status_cabinet')
ORDER BY viewname;
```

## Solución de Problemas

### Error: "psql no está disponible"
- Instala PostgreSQL Client Tools
- O usa el script Python en su lugar

### Error: "relation already exists"
- No es crítico, significa que la vista ya existe
- El script continuará con las demás vistas

### Error: "dependencias faltantes"
- Algunas vistas pueden depender de otras vistas o tablas
- Ejecuta primero las vistas base o revisa el orden de ejecución en los archivos SQL

## Notas

- Los scripts son idempotentes: pueden ejecutarse múltiples veces sin problemas
- Las vistas se recrean si ya existen (usando `CREATE OR REPLACE VIEW`)
- Los scripts verifican automáticamente que las vistas se crearon correctamente
