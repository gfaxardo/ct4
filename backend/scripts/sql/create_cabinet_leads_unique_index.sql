-- ============================================================================
-- Crear índice único en external_id para module_ct_cabinet_leads
-- Necesario para usar ON CONFLICT (external_id) DO NOTHING
-- ============================================================================

-- Opción 1: Índice único parcial (permite múltiples NULLs pero valores únicos)
-- Esta es la opción recomendada porque external_id puede ser NULL
CREATE UNIQUE INDEX IF NOT EXISTS idx_cabinet_leads_external_id_unique 
    ON public.module_ct_cabinet_leads(external_id) 
    WHERE external_id IS NOT NULL;

-- Verificar que el índice se creó correctamente
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname = 'public'
  AND tablename = 'module_ct_cabinet_leads'
  AND indexname = 'idx_cabinet_leads_external_id_unique';

-- Si el índice parcial no funciona con ON CONFLICT, usar esta alternativa:
-- Constraint único (pero esto NO permite NULLs duplicados)
-- NOTA: Descomentar solo si el índice parcial no funciona
/*
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'uq_module_ct_cabinet_leads_external_id'
    ) THEN
        ALTER TABLE public.module_ct_cabinet_leads
        ADD CONSTRAINT uq_module_ct_cabinet_leads_external_id
        UNIQUE (external_id);
    END IF;
END $$;
*/

