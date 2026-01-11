# Instrucciones para Ejecutar el Fix de la Vista

## Problema Identificado
Los logs muestran que la vista `ops.v_claims_payment_status_cabinet` tiene duplicados para milestone_value=5, causando `expected_total=195` en vez de `160`.

## Solución
Necesitas ejecutar el SQL actualizado de la vista en la base de datos.

---

## Opción 1: Usando psql (Recomendado)

1. **Abre una terminal/PowerShell**

2. **Conéctate a la base de datos:**
   ```powershell
   psql -h 168.119.226.236 -U yego_user -d yego_integral
   ```
   
   Cuando te pida la contraseña, ingresa: `37>MNA&-35+`

3. **Ejecuta el contenido del archivo:**
   
   Opción A - Desde psql:
   ```sql
   \i C:/Users/Pc/Documents/Cursor\ Proyectos/ct4/backend/sql/ops/v_claims_payment_status_cabinet.sql
   ```
   
   Opción B - Copiar y pegar:
   - Abre el archivo: `backend/sql/ops/v_claims_payment_status_cabinet.sql`
   - Copia TODO el contenido (desde CREATE OR REPLACE VIEW hasta el final)
   - Pégalo en psql y presiona Enter

4. **Verificar que funcionó:**
   ```sql
   -- Verificar que ahora no hay duplicados para un driver problemático
   SELECT 
       driver_id,
       milestone_value,
       COUNT(*) AS n_rows
   FROM ops.v_claims_payment_status_cabinet
   WHERE driver_id = 'b264635aea6c41c7b14b481b02d8cb09'
   GROUP BY driver_id, milestone_value
   ORDER BY milestone_value;
   ```
   
   Deberías ver `n_rows = 1` para cada milestone (no 2).

---

## Opción 2: Usando un cliente gráfico (DBeaver, pgAdmin, etc.)

1. Conéctate a la base de datos:
   - Host: `168.119.226.236`
   - Puerto: `5432`
   - Database: `yego_integral`
   - Usuario: `yego_user`
   - Contraseña: `37>MNA&-35+`

2. Abre el archivo: `backend/sql/ops/v_claims_payment_status_cabinet.sql`

3. Copia TODO el contenido y ejecútalo

---

## Verificación Final

Después de ejecutar el fix, verifica que funcionó:

1. **Haz una nueva petición al endpoint:**
   ```
   http://localhost:8000/api/v1/yango/payments/cabinet/drivers?limit=100
   ```

2. **Busca los drivers problemáticos en la respuesta:**
   - `b264635aea6c41c7b14b481b02d8cb09` (Oscar Sanabria)
   - `88881990913f4b8181ff342c99635452` (Alexander Anaya)
   - `3d809fc2cca64071a46dabe3223e314c` (Prado Wilfredo)

3. **Verifica que `expected_total` sea <= 160** (no 195)

---

## Si no tienes psql instalado

Instala PostgreSQL client tools o usa un cliente gráfico como DBeaver (gratis).





