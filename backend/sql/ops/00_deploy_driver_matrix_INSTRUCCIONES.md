# Instrucciones: Deployment Driver Matrix Views

## Cómo ejecutar en DBeaver

### Paso 1: Abrir el script de deployment

1. En DBeaver, navega a: `backend/sql/ops/00_deploy_driver_matrix.sql`
2. Abre el archivo (doble clic o `File` → `Open SQL Script`)
3. Asegúrate de estar conectado a la base de datos correcta:
   - **Host**: `168.119.226.236`
   - **Port**: `5432`
   - **Database**: `yego_integral`
   - **User**: `yego_user`

### Paso 2: Ejecutar el script

1. **Selecciona todo el contenido** del archivo (Ctrl+A)
2. **Ejecuta el script** (Ctrl+Enter o botón ▶️ "Execute SQL Script")
3. **Espera a que termine** (puede tardar varios minutos dependiendo del tamaño de los datos)

### Paso 3: Verificar resultados

1. Revisa la pestaña **"Messages"** o **"Data Output"**:
   - ✅ Si ves `✅ Deployment exitoso: Todas las vistas creadas correctamente.` → **Éxito**
   - ❌ Si ves `ERROR: ...` → Lee el mensaje de error y corrige el problema

### Paso 4: Ejecutar verificación

1. Abre el archivo: `backend/sql/ops/00_deploy_driver_matrix_verify.sql`
2. **Selecciona todo** (Ctrl+A)
3. **Ejecuta** (Ctrl+Enter)
4. Revisa los resultados de cada sección:
   - **Verificación 1**: Todas las vistas deben mostrar `✅ EXISTE`
   - **Verificación 2**: Debe mostrar 20 filas de muestra
   - **Verificación 3**: Debe retornar **0 filas** (sin duplicados)
   - **Verificaciones 4-8**: Revisa que los conteos y distribuciones sean razonables

## Solución de problemas

### Error: "relation does not exist"

Si ves errores como `relation "ops.xxx" does not exist`:

1. **Verifica que existan las vistas/tablas base**:
   ```sql
   SELECT table_name 
   FROM information_schema.tables 
   WHERE table_schema = 'ops' 
   AND table_name IN (
       'scout_payment_rules',
       'partner_payment_rules',
       'v_yango_receivable_payable_detail',
       'v_yango_payments_ledger_latest_enriched'
   );
   ```

2. Si faltan, crea primero esas vistas/tablas antes de ejecutar el deployment.

### Error: "statement timeout"

Si el script tarda mucho y se cancela:

1. **Aumenta el timeout en DBeaver**:
   - `Window` → `Preferences` → `DBeaver` → `SQL Editor` → `Query Manager`
   - Aumenta `Query timeout` a 300 segundos (5 minutos) o más

2. **Ejecuta sección por sección**:
   - Ejecuta solo la Sección 1 (validación)
   - Luego Sección 2 (v_payment_calculation)
   - Y así sucesivamente

### Error: "permission denied"

Si ves errores de permisos:

1. Verifica que el usuario `yego_user` tenga permisos para:
   - `CREATE VIEW` en el schema `ops`
   - `SELECT` en las tablas/vistas base

## Orden de ejecución (si ejecutas manualmente)

Si necesitas ejecutar las vistas una por una:

1. `ops.v_payment_calculation`
2. `ops.v_claims_payment_status_cabinet`
3. `ops.v_yango_cabinet_claims_for_collection`
4. `ops.v_yango_payments_claims_cabinet_14d`
5. `ops.v_payments_driver_matrix_cabinet`

## Verificación rápida

Después del deployment, ejecuta esta query para verificar rápidamente:

```sql
SELECT COUNT(*) FROM ops.v_payments_driver_matrix_cabinet;
```

Si retorna un número (incluso 0), la vista existe y es accesible. ✅

