-- ============================================================================
-- Crear tabla: public.module_ct_cabinet_leads
-- Ajustada para CSV sin columna id (id será autoincremental)
-- ============================================================================

CREATE TABLE IF NOT EXISTS public.module_ct_cabinet_leads (
    id SERIAL PRIMARY KEY,  -- Auto-incremental
    external_id VARCHAR,
    activation_city VARCHAR,
    active_1 BOOLEAN,
    active_5 BOOLEAN,
    active_10 BOOLEAN,
    active_15 BOOLEAN,
    active_25 BOOLEAN,
    active_50 BOOLEAN,
    active_100 BOOLEAN,
    asset_color VARCHAR,
    asset_model VARCHAR,
    asset_plate_number VARCHAR,
    last_name VARCHAR,
    first_name VARCHAR,
    middle_name VARCHAR,
    last_active_date DATE,
    lead_created_at TIMESTAMP WITHOUT TIME ZONE,
    park_name VARCHAR,
    park_phone VARCHAR,
    status VARCHAR,
    tariff VARCHAR,
    target_city VARCHAR,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- Índice único en external_id para evitar duplicados (ON CONFLICT DO NOTHING)
CREATE UNIQUE INDEX IF NOT EXISTS idx_cabinet_leads_external_id_unique 
    ON public.module_ct_cabinet_leads(external_id) 
    WHERE external_id IS NOT NULL;

-- Índices para mejorar rendimiento
CREATE INDEX IF NOT EXISTS idx_cabinet_leads_lead_created_at 
    ON public.module_ct_cabinet_leads(lead_created_at);

CREATE INDEX IF NOT EXISTS idx_cabinet_leads_park_phone 
    ON public.module_ct_cabinet_leads(park_phone) 
    WHERE park_phone IS NOT NULL;

COMMENT ON TABLE public.module_ct_cabinet_leads IS 
'Tabla de leads de registro en Yango Cabinet. Fuente principal para matching de identidad y generación de claims.';

COMMENT ON COLUMN public.module_ct_cabinet_leads.id IS 
'ID autoincremental. Si el CSV no tiene columna id, se genera automáticamente.';

COMMENT ON COLUMN public.module_ct_cabinet_leads.external_id IS 
'ID externo del lead. Usado como source_pk en el sistema de identidad. Debe ser único.';

COMMENT ON COLUMN public.module_ct_cabinet_leads.lead_created_at IS 
'Fecha y hora de creación del lead. Usado como snapshot_date en el sistema de identidad.';


