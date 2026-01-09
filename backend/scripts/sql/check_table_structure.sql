-- Verificar estructura de module_ct_cabinet_payments
SELECT 
    column_name, 
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_schema = 'public' 
    AND table_name = 'module_ct_cabinet_payments' 
ORDER BY ordinal_position;



