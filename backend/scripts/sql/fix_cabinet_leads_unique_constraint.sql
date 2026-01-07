-- ============================================================================
-- Script para crear constraint único en external_id para module_ct_cabinet_leads
-- Ejecutar este script si el upload de CSV falla con error de "no unique constraint"
-- ============================================================================

-- Paso 1: Verificar si hay duplicados (debe estar vacío para crear el constraint)
SELECT 
    external_id,
    COUNT(*) as count
FROM public.module_ct_cabinet_leads
WHERE external_id IS NOT NULL
GROUP BY external_id
HAVING COUNT(*) > 1;

-- Si hay duplicados, eliminar los duplicados primero (mantener el más reciente)
-- DESCOMENTAR SOLO SI HAY DUPLICADOS:
/*
DELETE FROM public.module_ct_cabinet_leads
WHERE id IN (
    SELECT id
    FROM (
        SELECT id,
               ROW_NUMBER() OVER (PARTITION BY external_id ORDER BY lead_created_at DESC, id DESC) as rn
        FROM public.module_ct_cabinet_leads
        WHERE external_id IS NOT NULL
    ) t
    WHERE t.rn > 1
);
*/

-- Paso 2: Eliminar constraint existente si existe (opcional, solo si necesitas recrearlo)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        WHERE n.nspname = 'public'
          AND t.relname = 'module_ct_cabinet_leads'
          AND c.conname = 'uq_module_ct_cabinet_leads_external_id'
    ) THEN
        ALTER TABLE public.module_ct_cabinet_leads
        DROP CONSTRAINT uq_module_ct_cabinet_leads_external_id;
        RAISE NOTICE 'Constraint eliminado';
    END IF;
END $$;

-- Paso 3: Crear constraint único
ALTER TABLE public.module_ct_cabinet_leads
ADD CONSTRAINT uq_module_ct_cabinet_leads_external_id
UNIQUE (external_id);

-- Paso 4: Verificar que se creó correctamente
SELECT 
    c.conname as constraint_name,
    t.relname as table_name,
    n.nspname as schema_name
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname = 'public'
  AND t.relname = 'module_ct_cabinet_leads'
  AND c.conname = 'uq_module_ct_cabinet_leads_external_id'
  AND c.contype = 'u';

-- Si el constraint no se puede crear (por duplicados), usar índice único parcial:
-- CREATE UNIQUE INDEX IF NOT EXISTS idx_cabinet_leads_external_id_unique 
--     ON public.module_ct_cabinet_leads(external_id) 
--     WHERE external_id IS NOT NULL;

