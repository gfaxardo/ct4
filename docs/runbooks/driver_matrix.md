# Driver Matrix - Runbook

## Propósito

Este runbook describe cómo aplicar y validar la vista `ops.v_payments_driver_matrix_cabinet`, que muestra 1 fila por driver con información de milestones M1/M5/M25 y estados de pago Yango/Scout.

---

## Aplicar la Vista en Base de Datos

### Paso 1: Verificar Dependencias

Antes de crear la vista, asegúrate de que existan las siguientes vistas/tablas:

```sql
-- Verificar dependencias
SELECT 
    table_schema,
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'ops'
    AND table_name IN (
        'v_claims_payment_status_cabinet',
        'v_yango_cabinet_claims_for_collection',
        'v_yango_payments_claims_cabinet_14d',
        'v_payment_calculation'
    )
UNION ALL
SELECT 
    table_schema,
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'public'
    AND table_name = 'drivers';
```

**Todas deben existir.** Si falta alguna, crearla primero.

### Paso 2: Aplicar la Vista

```bash
# Desde el directorio del proyecto
psql -h <host> -U <user> -d <database> -f backend/sql/ops/v_payments_driver_matrix_cabinet.sql
```

O ejecutar el contenido del archivo directamente en tu cliente SQL.

**Archivo canónico:** `backend/sql/ops/v_payments_driver_matrix_cabinet.sql`

### Paso 3: Verificar que se Creó Correctamente

```sql
-- Verificar que la vista existe
SELECT 
    table_schema,
    table_name,
    view_definition
FROM information_schema.views
WHERE table_schema = 'ops'
    AND table_name = 'v_payments_driver_matrix_cabinet';

-- Verificar columnas
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_schema = 'ops'
    AND table_name = 'v_payments_driver_matrix_cabinet'
ORDER BY ordinal_position;
```

**Debe tener 34 columnas** (incluyendo los flags de inconsistencia).

---

## Validar con verification.sql

### Ejecutar Queries de Verificación

```bash
psql -h <host> -U <user> -d <database> -f backend/sql/ops/v_payments_driver_matrix_cabinet_verification.sql
```

O ejecutar las queries manualmente desde el archivo.

### Qué Validar

1. **Verificación básica:**
   - Total de drivers
   - Drivers con M1/M5/M25
   - Drivers con origin_tag

2. **Sanity checks:**
   - No duplicados por driver_id (debe retornar 0 filas)
   - Distribución de milestones
   - Distribución de yango_payment_status
   - Distribución de window_status
   - Expected amounts correctos (M1=25, M5=35, M25=100)
   - Overdue days >= 0
   - week_start siempre es lunes

3. **Verificación de columnas:**
   - Todas las columnas esperadas están presentes
   - Tipos de datos correctos

---

## Qué Significa "M5 sin M1"

### Contexto

La vista puede mostrar casos donde un driver tiene datos para M5 (milestone 5) pero M1 (milestone 1) aparece vacío (NULL). **Esto NO es un bug**, es un comportamiento esperado.

### Causas Probables

1. **Missing claim M1:**
   - El driver alcanzó M5 pero nunca tuvo un claim M1 registrado en `ops.v_claims_payment_status_cabinet`.
   - Puede ocurrir si el driver se registró después de alcanzar M5 directamente.

2. **Mismatch identidad/join:**
   - El claim M1 existe pero no hace match con las tablas de enriquecimiento (Yango, window_status) debido a diferencias en `driver_id` o `lead_date`.

3. **Split de semanas:**
   - M1 y M5 tienen `week_start` diferentes, causando que aparezcan en filas separadas (aunque el GROUP BY debería agruparlos).

4. **Múltiples ciclos por driver:**
   - El `GROUP BY bc.driver_id` está agrupando múltiples claims, y el `MAX()` puede estar seleccionando un claim M1 que no tiene match en las tablas de enriquecimiento.

### Flags de Inconsistencia

La vista incluye flags para identificar estos casos:

- `m5_without_m1_flag`: `true` si M5 tiene `achieved_flag=true` pero M1 no
- `m25_without_m5_flag`: `true` si M25 tiene `achieved_flag=true` pero M5 no
- `milestone_inconsistency_notes`: Texto descriptivo ("M5 sin M1", "M25 sin M5", etc.)

### Interpretación

- **No se inventan datos:** Si M1 no existe en claims, `m1_*` será NULL aunque M5 exista.
- **Es información válida:** Muestra que existe evidencia de un milestone superior sin evidencia del anterior.
- **Requiere revisión:** Si necesitas investigar, usa el script de diagnóstico:
  - `backend/sql/ops/_debug_driver_matrix_m5_without_m1.sql`

---

## Endpoint Backend

**Endpoint:** `GET /api/v1/ops/payments/driver-matrix`

**Parámetros:**
- `week_start_from` (opcional): Fecha inicio semana
- `week_start_to` (opcional): Fecha fin semana
- `origin_tag` (opcional): 'cabinet' o 'fleet_migration'
- `only_pending` (opcional): Solo pendientes
- `limit` (default: 200): Límite de resultados
- `offset` (default: 0): Offset para paginación
- `order` (default: 'week_start_desc'): Ordenamiento

**Respuesta:**
- `meta`: Metadatos (total, returned, limit, offset)
- `data`: Array de `DriverMatrixRow` con todas las columnas de la vista

---

## Troubleshooting

### Error: "relation ops.v_payments_driver_matrix_cabinet does not exist"

**Solución:** Ejecutar el script SQL para crear la vista.

### Error: "column m5_without_m1_flag does not exist"

**Solución:** Asegúrate de usar la versión canónica del SQL que incluye los flags de inconsistencia.

### La vista retorna 0 filas

**Verificar:**
1. Que las vistas dependientes existan y tengan datos
2. Que haya claims con `milestone_value IN (1, 5, 25)`
3. Que los filtros aplicados no estén excluyendo todos los registros

### Performance lenta

**Optimizaciones:**
1. Verificar índices en `driver_id` en las tablas base
2. Considerar crear índices en las vistas dependientes si es necesario
3. Usar `limit` y `offset` para paginación

---

## Referencias

- **Vista canónica:** `backend/sql/ops/v_payments_driver_matrix_cabinet.sql`
- **Queries de verificación:** `backend/sql/ops/v_payments_driver_matrix_cabinet_verification.sql`
- **Script de diagnóstico:** `backend/sql/ops/_debug_driver_matrix_m5_without_m1.sql`
- **Documentación de inconsistencias:** `docs/runbooks/driver_matrix_inconsistencies.md`
- **Análisis de versiones:** `docs/analysis/driver_matrix_sql_audit.md`
- **Endpoint backend:** `backend/app/api/v1/ops_payments.py` (función `get_driver_matrix`)





