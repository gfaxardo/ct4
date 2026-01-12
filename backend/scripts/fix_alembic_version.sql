-- Script para corregir la versión de Alembic en la base de datos
-- Ejecutar: psql -d tu_database -f fix_alembic_version.sql

UPDATE alembic_version 
SET version_num = '013_identity_origin' 
WHERE version_num = '014_driver_orphan_quarantine';

-- Verificar
SELECT version_num FROM alembic_version;
