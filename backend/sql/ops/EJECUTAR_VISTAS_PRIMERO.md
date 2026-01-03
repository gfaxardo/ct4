# ⚠️ IMPORTANTE: Ejecutar Vistas SQL Primero

Antes de probar los cambios en el código, **DEBES ejecutar las siguientes vistas SQL en la base de datos**:

## 1. Vista Claim-Level (Fuente Única)

**Archivo**: `backend/sql/ops/v_yango_cabinet_claims_for_collection.sql`

Ejecutar en `psql`:
```bash
psql -h 168.119.226.236 -U yego_user -d yego_integral
# Password: 37>MNA&-35+
```

Luego copiar y pegar el contenido completo del archivo.

## 2. Vista Rollup (Driver-Level)

**Archivo**: `backend/sql/ops/v_claims_cabinet_driver_rollup.sql`

Ejecutar en `psql` (misma conexión):
```bash
# Copiar y pegar el contenido completo del archivo
```

## 3. Validar Reconciliación (Opcional pero Recomendado)

**Archivo**: `backend/sql/ops/validation_rollup_reconciliation.sql`

Ejecutar para verificar que SUM(rollup) == SUM(claim-level).

---

**SIN estas vistas ejecutadas, los endpoints fallarán con "relation does not exist".**



