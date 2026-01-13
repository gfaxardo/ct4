# Solución: Error "Failed to fetch" en /pagos/yango-cabinet

## Problema

El error "Failed to fetch" indica que el frontend no puede conectarse al endpoint del backend. Esto puede deberse a:

1. **Las vistas SQL no se han ejecutado en la base de datos** (más probable)
2. El backend no está corriendo
3. Error de conexión entre frontend y backend

## Solución

### Paso 1: Verificar que el backend esté corriendo

Abre una terminal y verifica que el backend esté activo en `http://localhost:8000`

### Paso 2: Ejecutar las vistas SQL (CRÍTICO)

Las vistas SQL **DEBEN** ejecutarse en la base de datos antes de que los endpoints funcionen:

**Conexión**:
```bash
psql -h 168.119.226.236 -U yego_user -d yego_integral
# Password: 37>MNA&-35+
```

**Archivos a ejecutar** (en orden):
1. `backend/sql/ops/v_yango_cabinet_claims_for_collection.sql`
2. `backend/sql/ops/v_claims_cabinet_driver_rollup.sql`

Sin estas vistas, el endpoint intentará consultar vistas que no existen y fallará con un error de base de datos.

### Paso 3: Reiniciar el backend

Después de ejecutar las vistas, reinicia el servidor backend para asegurar que los cambios se apliquen.

### Paso 4: Verificar el endpoint directamente

Puedes probar el endpoint directamente en el navegador o con curl:

```
http://localhost:8000/api/v1/yango/payments/yango/cabinet/claims?payment_status=UNPAID,PAID_MISAPPLIED
```

Si el endpoint retorna un error de base de datos (como "relation does not exist"), significa que las vistas no se han ejecutado.

## Alternativa: Usar la página integrada

Recuerda que ahora la funcionalidad está integrada en `/pagos/claims` con un toggle entre "Modo Driver" y "Modo Cobranza Yango". Puedes usar esa página en lugar de `/pagos/yango-cabinet`.







