-- ============================================================================
-- Script de Verificación: Tablas Requeridas para Data Health
-- ============================================================================
-- Ejecutar ANTES de crear las vistas para verificar qué tablas existen.
-- Si una tabla no existe, comentar la CTE correspondiente en v_data_health.sql
-- ============================================================================

SELECT 
    table_schema,
    table_name,
    CASE 
        WHEN table_schema || '.' || table_name IN (
            'public.summary_daily',
            'ops.yango_payment_ledger',
            'raw.module_ct_cabinet_payments',
            'public.module_ct_cabinet_leads',
            'public.module_ct_scouting_daily',
            'public.module_ct_cabinet_migrations',
            'public.module_ct_scout_drivers',
            'public.module_ct_cabinet_payments',
            'public.drivers',
            'public.module_ct_scouts_list'
        ) THEN 'REQUERIDA'
        ELSE 'OPCIONAL'
    END AS status
FROM information_schema.tables
WHERE (table_schema, table_name) IN (
    ('public', 'summary_daily'),
    ('ops', 'yango_payment_ledger'),
    ('raw', 'module_ct_cabinet_payments'),
    ('public', 'module_ct_cabinet_leads'),
    ('public', 'module_ct_scouting_daily'),
    ('public', 'module_ct_cabinet_migrations'),
    ('public', 'module_ct_scout_drivers'),
    ('public', 'module_ct_cabinet_payments'),
    ('public', 'drivers'),
    ('public', 'module_ct_scouts_list')
)
ORDER BY table_schema, table_name;

-- Si alguna tabla aparece como "OPCIONAL" o no aparece, comentar su CTE en v_data_health.sql



